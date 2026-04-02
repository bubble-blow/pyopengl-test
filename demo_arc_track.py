import math
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# --------- 参数（可按需修改）---------
INNER_RADIUS = 1.4          # 圆弧轨道内半径
CROSS_SECTION_WIDTH = 0.4   # 矩形横截面宽（径向）
CROSS_SECTION_HEIGHT = 0.25 # 矩形横截面高（Z 方向）
ARC_DEGREES = 220           # 圆弧角度
SEGMENTS = 96               # 圆弧离散段数（越大越圆滑）

WINDOW_W, WINDOW_H = 1000, 700

# 交互状态
rot_x = 20.0
rot_y = -35.0
zoom = 1.0


def radial_point(radius: float, theta: float, z: float):
    """极坐标转笛卡尔坐标。theta 单位：弧度。"""
    return (radius * math.cos(theta), radius * math.sin(theta), z)


def normal_xy(theta: float):
    """返回 XY 平面里沿半径方向的法线（单位向量）。"""
    return (math.cos(theta), math.sin(theta), 0.0)


def tangent_xy(theta: float):
    """返回 XY 平面里沿切向的向量（单位向量）。"""
    return (-math.sin(theta), math.cos(theta), 0.0)


def draw_quad(v1, v2, v3, v4, n):
    glNormal3f(*n)
    glVertex3f(*v1)
    glVertex3f(*v2)
    glVertex3f(*v3)
    glVertex3f(*v4)


def draw_arc_track(inner_r, width, height, arc_deg, segments):
    outer_r = inner_r + width
    z0, z1 = -height / 2.0, height / 2.0

    start = -math.radians(arc_deg) / 2.0
    end = math.radians(arc_deg) / 2.0

    dtheta = (end - start) / segments

    # 逐段绘制 4 个侧面 + 顶面 + 底面
    glBegin(GL_QUADS)
    for i in range(segments):
        t0 = start + i * dtheta
        t1 = start + (i + 1) * dtheta

        # 每段 8 个角点（内/外 * 前后角 * 上下）
        i0b = radial_point(inner_r, t0, z0)
        i0t = radial_point(inner_r, t0, z1)
        o0b = radial_point(outer_r, t0, z0)
        o0t = radial_point(outer_r, t0, z1)

        i1b = radial_point(inner_r, t1, z0)
        i1t = radial_point(inner_r, t1, z1)
        o1b = radial_point(outer_r, t1, z0)
        o1t = radial_point(outer_r, t1, z1)

        # 内侧面（朝向圆心）
        n_in = tuple(-x for x in normal_xy((t0 + t1) * 0.5))
        draw_quad(i0b, i1b, i1t, i0t, n_in)

        # 外侧面（远离圆心）
        n_out = normal_xy((t0 + t1) * 0.5)
        draw_quad(o0b, o0t, o1t, o1b, n_out)

        # 顶面
        draw_quad(i0t, i1t, o1t, o0t, (0.0, 0.0, 1.0))

        # 底面
        draw_quad(i0b, o0b, o1b, i1b, (0.0, 0.0, -1.0))

    # 两端封口（截面矩形）
    t_start, t_end = start, end
    n_start = tuple(-x for x in tangent_xy(t_start))
    n_end = tangent_xy(t_end)

    si_b = radial_point(inner_r, t_start, z0)
    si_t = radial_point(inner_r, t_start, z1)
    so_b = radial_point(outer_r, t_start, z0)
    so_t = radial_point(outer_r, t_start, z1)

    ei_b = radial_point(inner_r, t_end, z0)
    ei_t = radial_point(inner_r, t_end, z1)
    eo_b = radial_point(outer_r, t_end, z0)
    eo_t = radial_point(outer_r, t_end, z1)

    draw_quad(si_b, si_t, so_t, so_b, n_start)
    draw_quad(ei_b, eo_b, eo_t, ei_t, n_end)
    glEnd()


def draw_axes(length=3.0):
    glDisable(GL_LIGHTING)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    # X - 红
    glColor3f(1.0, 0.2, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(length, 0, 0)
    # Y - 绿
    glColor3f(0.2, 1.0, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(0, length, 0)
    # Z - 蓝
    glColor3f(0.2, 0.5, 1.0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, length)
    glEnd()
    glEnable(GL_LIGHTING)


def init_gl():
    glClearColor(0.06, 0.07, 0.1, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_NORMALIZE)

    glLightfv(GL_LIGHT0, GL_POSITION, (4.0, 5.0, 8.0, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.95, 0.95, 0.95, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.6, 0.6, 0.6, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 40.0)


def reshape(w, h):
    h = max(h, 1)
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, w / h, 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)


def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # 相机
    gluLookAt(0.0, -5.0 / zoom, 3.0 / zoom,
              0.0, 0.0, 0.0,
              0.0, 0.0, 1.0)

    glRotatef(rot_x, 1.0, 0.0, 0.0)
    glRotatef(rot_y, 0.0, 0.0, 1.0)

    draw_axes()

    # 轨道本体
    glColor3f(0.85, 0.72, 0.2)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.85, 0.72, 0.2, 1.0))
    draw_arc_track(INNER_RADIUS, CROSS_SECTION_WIDTH, CROSS_SECTION_HEIGHT, ARC_DEGREES, SEGMENTS)

    glutSwapBuffers()


def keyboard(key, _x, _y):
    global zoom
    k = key.decode("utf-8", errors="ignore").lower()
    if k == 'q' or ord(key) == 27:  # ESC
        sys.exit(0)
    elif k == '+':
        zoom *= 1.08
    elif k == '-':
        zoom /= 1.08
    glutPostRedisplay()


def special(key, _x, _y):
    global rot_x, rot_y
    if key == GLUT_KEY_UP:
        rot_x -= 4
    elif key == GLUT_KEY_DOWN:
        rot_x += 4
    elif key == GLUT_KEY_LEFT:
        rot_y -= 4
    elif key == GLUT_KEY_RIGHT:
        rot_y += 4
    glutPostRedisplay()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"3D Arc Track Demo (Rectangular Cross-section)")

    init_gl()

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)

    print("\n=== 控制说明 ===")
    print("方向键: 旋转模型")
    print("+ / - : 缩放")
    print("Q 或 ESC: 退出\n")

    glutMainLoop()


if __name__ == '__main__':
    main()
