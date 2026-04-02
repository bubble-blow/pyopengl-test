import math
import random
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

WINDOW_W, WINDOW_H = 1280, 800

# 轨道与运动参数
POINT_COUNT = 700
STEP_LEN = 0.35
MIN_CURVATURE_RADIUS = 6.0   # 曲率半径下限：越大弯越缓
TRACK_WIDTH = 0.8
TRACK_HEIGHT = 0.18

GRAVITY = 9.81
INITIAL_SPEED = 13.5         # 初始速度（m/s）
MIN_SPEED = 3.5              # 防止数值抖动导致静止

# 相机相对轨道局部坐标系偏移（固定距离与固定相对角度）
CAM_BACK = 4.2
CAM_UP = 1.4
CAM_SIDE = 1.1
CAM_LOOK_AHEAD = 2.0

# 全局状态
path_points = []
frames = []
arc_lengths = []
speeds = []
car_s = 0.0
last_time = None


def v_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def v_norm(a):
    return math.sqrt(max(1e-12, v_dot(a, a)))


def v_unit(a):
    n = v_norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


def tangent_from_angles(yaw, pitch):
    cp = math.cos(pitch)
    return v_unit((cp * math.cos(yaw), cp * math.sin(yaw), math.sin(pitch)))


def build_random_path(n=POINT_COUNT, step=STEP_LEN, r_min=MIN_CURVATURE_RADIUS):
    """构建随机但曲率受限的3D轨道中心线。"""
    pts = [(0.0, 0.0, 4.0)]
    yaw = 0.0
    pitch = 0.0

    # 每步允许的方向变化角上限，确保近似曲率半径不小于 r_min
    max_turn = min(0.24, step / r_min)

    for i in range(1, n):
        # 缓慢随机改变偏航和俯仰，避免急弯
        yaw += random.uniform(-max_turn, max_turn)
        pitch += random.uniform(-0.55 * max_turn, 0.55 * max_turn)
        pitch = max(-0.55, min(0.55, pitch))

        t = tangent_from_angles(yaw, pitch)
        p = v_add(pts[-1], v_mul(t, step))

        # 长程起伏，避免无限下坠或上升
        wave = 2.2 * math.sin(i * 0.025) + 1.0 * math.sin(i * 0.063 + 1.5)
        z_target = 4.5 + wave
        p = (p[0], p[1], 0.92 * p[2] + 0.08 * z_target)

        pts.append(p)

    return pts


def smooth_polyline(pts, rounds=2):
    data = pts[:]
    for _ in range(rounds):
        nxt = [data[0]]
        for i in range(1, len(data) - 1):
            a, b, c = data[i - 1], data[i], data[i + 1]
            nxt.append((
                0.2 * a[0] + 0.6 * b[0] + 0.2 * c[0],
                0.2 * a[1] + 0.6 * b[1] + 0.2 * c[1],
                0.2 * a[2] + 0.6 * b[2] + 0.2 * c[2],
            ))
        nxt.append(data[-1])
        data = nxt
    return data


def compute_arclengths(pts):
    s = [0.0]
    for i in range(1, len(pts)):
        s.append(s[-1] + v_norm(v_sub(pts[i], pts[i - 1])))
    return s


def compute_speeds(pts, v0=INITIAL_SPEED, g=GRAVITY):
    """用机械能近似：v^2 = v0^2 + 2g(h0-h)。"""
    h0 = pts[0][2]
    out = []
    for p in pts:
        v2 = v0 * v0 + 2.0 * g * (h0 - p[2])
        out.append(max(MIN_SPEED, math.sqrt(max(0.0, v2))))
    return out


def compute_frames(pts, s_vals, v_vals):
    """为每个点计算局部标架 (t, n_top, b_right) 与视重方向。"""
    g_vec = (0.0, 0.0, -GRAVITY)
    N = len(pts)
    t_list = []

    for i in range(N):
        if i == 0:
            t = v_unit(v_sub(pts[1], pts[0]))
        elif i == N - 1:
            t = v_unit(v_sub(pts[-1], pts[-2]))
        else:
            t = v_unit(v_sub(pts[i + 1], pts[i - 1]))
        t_list.append(t)

    # 先给一个初始“上向”
    n_prev = (0.0, 0.0, 1.0)
    frames_local = []

    for i in range(N):
        t = t_list[i]

        # 速度向量 v(t)
        vel = v_mul(t, v_vals[i])

        # 用差分估计加速度 a = dv/dt
        if i == 0:
            ds = max(1e-6, s_vals[1] - s_vals[0])
            dt = ds / max(1e-6, v_vals[0])
            vel_next = v_mul(t_list[1], v_vals[1])
            a_vec = v_mul(v_sub(vel_next, vel), 1.0 / max(1e-6, dt))
        elif i == N - 1:
            ds = max(1e-6, s_vals[-1] - s_vals[-2])
            dt = ds / max(1e-6, v_vals[-1])
            vel_prev = v_mul(t_list[-2], v_vals[-2])
            a_vec = v_mul(v_sub(vel, vel_prev), 1.0 / max(1e-6, dt))
        else:
            ds_f = max(1e-6, s_vals[i + 1] - s_vals[i])
            ds_b = max(1e-6, s_vals[i] - s_vals[i - 1])
            dt_f = ds_f / max(1e-6, v_vals[i])
            dt_b = ds_b / max(1e-6, v_vals[i - 1])
            vel_f = v_mul(t_list[i + 1], v_vals[i + 1])
            vel_b = v_mul(t_list[i - 1], v_vals[i - 1])
            a_vec = v_mul(v_sub(vel_f, vel_b), 1.0 / max(1e-6, dt_f + dt_b))

        # 视重方向（“感觉到的重力”）：g_eff = g - a
        g_eff = v_sub(g_vec, a_vec)

        # 轨道顶面法线：取视重在法平面中的分量（保证与切线正交）
        g_perp = v_sub(g_eff, v_mul(t, v_dot(g_eff, t)))
        if v_norm(g_perp) < 1e-5:
            g_perp = n_prev
        n_top = v_unit(g_perp)

        # 消除法线翻转抖动
        if v_dot(n_top, n_prev) < 0:
            n_top = v_mul(n_top, -1.0)

        b_right = v_unit(v_cross(t, n_top))
        n_top = v_unit(v_cross(b_right, t))

        n_prev = n_top
        frames_local.append((t, n_top, b_right))

    return frames_local


def sample_by_arclength(s_query):
    total = arc_lengths[-1]
    s = s_query % total

    lo, hi = 0, len(arc_lengths) - 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if arc_lengths[mid] <= s:
            lo = mid
        else:
            hi = mid

    i0, i1 = lo, min(lo + 1, len(path_points) - 1)
    s0, s1 = arc_lengths[i0], arc_lengths[i1]
    u = 0.0 if s1 <= s0 else (s - s0) / (s1 - s0)

    p0, p1 = path_points[i0], path_points[i1]
    p = (
        p0[0] * (1 - u) + p1[0] * u,
        p0[1] * (1 - u) + p1[1] * u,
        p0[2] * (1 - u) + p1[2] * u,
    )

    t0, n0, b0 = frames[i0]
    t1, n1, b1 = frames[i1]
    t = v_unit((t0[0] * (1 - u) + t1[0] * u,
                t0[1] * (1 - u) + t1[1] * u,
                t0[2] * (1 - u) + t1[2] * u))
    n = v_unit((n0[0] * (1 - u) + n1[0] * u,
                n0[1] * (1 - u) + n1[1] * u,
                n0[2] * (1 - u) + n1[2] * u))
    b = v_unit(v_cross(t, n))
    n = v_unit(v_cross(b, t))

    v = speeds[i0] * (1 - u) + speeds[i1] * u
    return p, t, n, b, v


def draw_axes(length=6.0):
    glDisable(GL_LIGHTING)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3f(1, 0.2, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(length, 0, 0)
    glColor3f(0.2, 1, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(0, length, 0)
    glColor3f(0.3, 0.6, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, length)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_track():
    half_w = TRACK_WIDTH * 0.5
    h = TRACK_HEIGHT

    # 轨道顶面（法线 = n_top，故顶面与视重方向垂直）
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.78, 0.80, 0.84, 1.0))
    glBegin(GL_QUADS)
    for i in range(len(path_points) - 1):
        p0, p1 = path_points[i], path_points[i + 1]
        _, n0, b0 = frames[i]
        _, n1, b1 = frames[i + 1]

        lt0 = v_sub(p0, v_mul(b0, half_w))
        rt0 = v_add(p0, v_mul(b0, half_w))
        lt1 = v_sub(p1, v_mul(b1, half_w))
        rt1 = v_add(p1, v_mul(b1, half_w))

        n_avg = v_unit(v_add(n0, n1))
        glNormal3f(*n_avg)
        glVertex3f(*lt0)
        glVertex3f(*rt0)
        glVertex3f(*rt1)
        glVertex3f(*lt1)
    glEnd()

    # 两侧与底面
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.34, 0.36, 0.42, 1.0))
    glBegin(GL_QUADS)
    for i in range(len(path_points) - 1):
        p0, p1 = path_points[i], path_points[i + 1]
        _, n0, b0 = frames[i]
        _, n1, b1 = frames[i + 1]

        lt0 = v_sub(p0, v_mul(b0, half_w))
        rt0 = v_add(p0, v_mul(b0, half_w))
        lb0 = v_sub(lt0, v_mul(n0, h))
        rb0 = v_sub(rt0, v_mul(n0, h))

        lt1 = v_sub(p1, v_mul(b1, half_w))
        rt1 = v_add(p1, v_mul(b1, half_w))
        lb1 = v_sub(lt1, v_mul(n1, h))
        rb1 = v_sub(rt1, v_mul(n1, h))

        # 左侧
        nl = v_unit(v_mul(v_add(b0, b1), -1.0))
        glNormal3f(*nl)
        glVertex3f(*lt0)
        glVertex3f(*lt1)
        glVertex3f(*lb1)
        glVertex3f(*lb0)

        # 右侧
        nr = v_unit(v_add(b0, b1))
        glNormal3f(*nr)
        glVertex3f(*rt0)
        glVertex3f(*rb0)
        glVertex3f(*rb1)
        glVertex3f(*rt1)

        # 底面
        nb = v_unit(v_mul(v_add(n0, n1), -1.0))
        glNormal3f(*nb)
        glVertex3f(*lb0)
        glVertex3f(*rb0)
        glVertex3f(*rb1)
        glVertex3f(*lb1)
    glEnd()


def draw_car(s):
    p, t, n, b, _ = sample_by_arclength(s)
    # 小车置于轨道上方一点
    car_pos = v_add(p, v_mul(n, 0.16))

    # 构造 4x4 矩阵：列向量为局部坐标轴 (t, b, n)
    M = [
        t[0], t[1], t[2], 0.0,
        b[0], b[1], b[2], 0.0,
        n[0], n[1], n[2], 0.0,
        car_pos[0], car_pos[1], car_pos[2], 1.0,
    ]

    glPushMatrix()
    glMultMatrixf(M)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.95, 0.25, 0.18, 1.0))
    glScalef(0.45, 0.28, 0.22)
    glutSolidCube(1.0)
    glPopMatrix()


def init_gl():
    glClearColor(0.05, 0.06, 0.09, 1.0)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_CULL_FACE)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_NORMALIZE)

    glLightfv(GL_LIGHT0, GL_POSITION, (12.0, -8.0, 18.0, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.96, 0.96, 0.96, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.4, 0.4, 0.4, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)


def reshape(w, h):
    h = max(1, h)
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(55.0, w / h, 0.1, 1500.0)
    glMatrixMode(GL_MODELVIEW)


def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    p, t, n, b, _ = sample_by_arclength(car_s)

    # 相机与轨道顶面保持固定距离/角度（固定局部偏移）
    eye = v_add(v_add(v_add(p, v_mul(t, -CAM_BACK)), v_mul(n, CAM_UP)), v_mul(b, CAM_SIDE))
    look = v_add(v_add(p, v_mul(t, CAM_LOOK_AHEAD)), v_mul(n, 0.08))

    gluLookAt(eye[0], eye[1], eye[2],
              look[0], look[1], look[2],
              n[0], n[1], n[2])

    draw_axes(4.5)
    draw_track()
    draw_car(car_s)

    glutSwapBuffers()


def idle():
    global car_s, last_time
    t_now = glutGet(GLUT_ELAPSED_TIME) * 0.001
    if last_time is None:
        last_time = t_now
        return

    dt = max(0.0, min(0.035, t_now - last_time))
    last_time = t_now

    # 用当前位置速度推进弧长参数
    _, _, _, _, v = sample_by_arclength(car_s)
    car_s += v * dt

    glutPostRedisplay()


def keyboard(key, _x, _y):
    k = key.decode("utf-8", errors="ignore").lower()
    if k == 'q' or ord(key) == 27:
        sys.exit(0)


def build_scene():
    global path_points, arc_lengths, speeds, frames

    random.seed(42)
    raw = build_random_path()
    path_points = smooth_polyline(raw, rounds=3)
    arc_lengths = compute_arclengths(path_points)
    speeds = compute_speeds(path_points)
    frames = compute_frames(path_points, arc_lengths, speeds)


def main():
    build_scene()

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Random Curvature-Limited Roller Coaster")

    init_gl()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutIdleFunc(idle)

    print("\n=== 控制说明 ===")
    print("Q / ESC: 退出")
    print(f"最小曲率半径约束: {MIN_CURVATURE_RADIUS:.2f}")
    print("轨道顶面法线来自视重方向投影（顶面与视重方向垂直）\n")

    glutMainLoop()


if __name__ == '__main__':
    main()
