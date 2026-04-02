import math
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

# 窗口尺寸常量
WINDOW_W, WINDOW_H = 1100, 760

# 行星参数
PLANET_RADIUS = 2.6      # 行星半径（超大行星）
LAT_STEPS = 16           # 纬线分段数（绘制经纬网格用）
LON_STEPS = 24           # 经线分段数

# 卫星参数（长方体）
SAT_W, SAT_H, SAT_D = 0.3, 0.15, 0.12  # 卫星的长、高、宽（缩小）
ORBIT_RADIUS = 3.0       # 卫星轨道半径（近距离贴近行星表面）

# 视角控制变量
rot_x, rot_y = 18.0, -30.0  # 绕 X 轴和 Y 轴的旋转角度
zoom = 1.0                  # 缩放系数
orbit_angle = 0.0           # 卫星轨道角度（度数）


def draw_axes(length=3.5):
    """
    绘制坐标轴（X红色，Y绿色，Z蓝色）
    临时关闭光照以保证线条颜色正常显示
    """
    glDisable(GL_LIGHTING)      # 关闭光照，避免光照影响线条颜色
    glLineWidth(2.0)            # 设置线宽
    glBegin(GL_LINES)           # 开始绘制线段
    
    # X轴 - 红色
    glColor3f(1, 0.2, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(length, 0, 0)
    
    # Y轴 - 绿色
    glColor3f(0.2, 1, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(0, length, 0)
    
    # Z轴 - 蓝色
    glColor3f(0.2, 0.5, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, length)
    
    glEnd()                     # 结束绘制
    glEnable(GL_LIGHTING)       # 重新开启光照


def draw_lat_lon_lines(radius, lat_steps=LAT_STEPS, lon_steps=LON_STEPS):
    """
    绘制球体的经纬线网格（辅助视觉参考）
    radius: 球体半径
    lat_steps: 纬线层数（不包括极点）
    lon_steps: 经线条数
    """
    glDisable(GL_LIGHTING)      # 关闭光照保证线条颜色
    glColor3f(0.05, 0.08, 0.15) # 深蓝色线条
    glLineWidth(1.2)            # 线宽

    # 绘制纬线（水平圆环，除南北极点外）
    for i in range(1, lat_steps):
        # 计算纬度角 phi（从 -π/2 到 π/2）
        phi = -math.pi / 2 + i * math.pi / lat_steps
        z = radius * math.sin(phi)      # Z轴高度
        r = radius * math.cos(phi)      # 当前纬度圈的半径
        glBegin(GL_LINE_LOOP)           # 绘制闭合圆环
        for j in range(lon_steps):
            t = 2 * math.pi * j / lon_steps  # 经度角 theta
            glVertex3f(r * math.cos(t), r * math.sin(t), z)
        glEnd()

    # 绘制经线（从北极到南极的半圆弧）
    for j in range(lon_steps):
        t = 2 * math.pi * j / lon_steps      # 当前经线的经度角
        glBegin(GL_LINE_STRIP)              # 绘制线带（不闭合）
        for i in range(lat_steps + 1):
            phi = -math.pi / 2 + i * math.pi / lat_steps  # 纬度角
            r = radius * math.cos(phi)       # 当前纬度的半径
            z = radius * math.sin(phi)       # Z轴高度
            glVertex3f(r * math.cos(t), r * math.sin(t), z)
        glEnd()

    glEnable(GL_LIGHTING)       # 重新开启光照


def draw_planet(radius=PLANET_RADIUS):
    """
    绘制行星（蓝色球体 + 经纬线网格）
    """
    # 设置行星材质颜色（蓝色）
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.22, 0.52, 0.95, 1.0))
    
    # 创建 OpenGL 二次曲面对象用于绘制球体
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)  # 设置平滑法线，保证光照效果
    gluSphere(quad, radius, 64, 64)      # 绘制球体（半径，经度分段，纬度分段）
    gluDeleteQuadric(quad)               # 删除二次曲面对象释放资源

    # 在球体表面叠加经纬线网格（略微放大避免深度冲突）
    draw_lat_lon_lines(radius * 1.002)


def draw_colored_cuboid(w, h, d):
    """
    绘制彩色长方体（六个面使用不同颜色）
    w: X轴方向宽度
    h: Y轴方向高度
    d: Z轴方向深度
    """
    x, y, z = w / 2.0, h / 2.0, d / 2.0  # 半长、半高、半深

    # 定义六个面的数据：(法向量, 颜色RGB, 四个顶点坐标)
    faces = [
        # 前面（+Z方向）- 红色
        ((0, 0, 1), (1.0, 0.25, 0.25), [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]),
        # 后面（-Z方向）- 绿色
        ((0, 0, -1), (0.25, 1.0, 0.25), [(-x, -y, -z), (-x, y, -z), (x, y, -z), (x, -y, -z)]),
        # 左面（-X方向）- 蓝色
        ((-1, 0, 0), (0.25, 0.55, 1.0), [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)]),
        # 右面（+X方向）- 黄色
        ((1, 0, 0), (1.0, 0.9, 0.25), [(x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z)]),
        # 顶面（+Y方向）- 紫色
        ((0, 1, 0), (1.0, 0.4, 0.95), [(-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z)]),
        # 底面（-Y方向）- 青色
        ((0, -1, 0), (0.25, 1.0, 0.95), [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)]),
    ]

    glBegin(GL_QUADS)  # 开始绘制四边形
    for normal, color, verts in faces:
        glNormal3f(*normal)                                      # 设置面法向量
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (*color, 1.0))  # 设置材质颜色
        for vx, vy, vz in verts:
            glVertex3f(vx, vy, vz)  # 绘制顶点
    glEnd()


def draw_satellite():
    """
    绘制卫星（绕行星公转的长方体）
    轨道固定在 X-Y 平面，Z 轴位置锁定为 0
    """
    global orbit_angle
    t = math.radians(orbit_angle)        # 角度转弧度
    
    # 计算卫星位置（X-Y 平面圆形轨道，Z 轴锁定）
    x = ORBIT_RADIUS * math.cos(t)
    y = ORBIT_RADIUS * math.sin(t)
    z = 0.0                                    # 锁定在轨道平面
    
    glPushMatrix()                       # 保存当前变换矩阵
    glTranslatef(x, y, z)                # 平移到卫星位置
    glRotatef(orbit_angle * 2.0, 0, 0, 1) # 自转（绕Z轴）
    glRotatef(35.0, 1, 0, 0)            # 倾斜卫星姿态
    draw_colored_cuboid(SAT_W, SAT_H, SAT_D)  # 绘制彩色长方体
    glPopMatrix()                        # 恢复变换矩阵


def init_gl():
    """
    初始化 OpenGL 状态（光照、材质、清屏色等）
    """
    glClearColor(0.02, 0.02, 0.05, 1)    # 设置深蓝色背景
    glEnable(GL_DEPTH_TEST)              # 启用深度测试（隐藏面消除）
    glEnable(GL_LIGHTING)                # 启用光照
    glEnable(GL_LIGHT0)                  # 启用光源0
    glEnable(GL_NORMALIZE)               # 自动归一化法向量

    # 设置光源0的位置（世界坐标）
    glLightfv(GL_LIGHT0, GL_POSITION, (4.0, 5.0, 7.0, 1.0))
    # 设置漫反射光颜色（亮白色）
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.95, 0.95, 0.95, 1.0))
    # 设置镜面反射光颜色
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    # 设置材质的高光属性（白色高光）
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.7, 0.7, 0.7, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)  # 高光指数（0-128）


def reshape(w, h):
    """
    窗口大小改变时的回调函数
    重新设置视口和投影矩阵
    """
    h = max(h, 1)                        # 避免除零
    glViewport(0, 0, w, h)              # 设置视口大小
    glMatrixMode(GL_PROJECTION)          # 切换到投影矩阵
    glLoadIdentity()                     # 重置投影矩阵
    gluPerspective(45.0, w / h, 0.1, 100.0)  # 透视投影（视角，宽高比，近平面，远平面）
    glMatrixMode(GL_MODELVIEW)           # 切换回模型视图矩阵


def display():
    """
    显示回调函数：每帧绘制场景
    """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # 清空颜色和深度缓冲
    glLoadIdentity()                                    # 重置模型视图矩阵

    # 设置摄像机位置和朝向
    # 眼睛位置保持略大于轨道半径，缩放影响距离
    cam_dist = ORBIT_RADIUS + 0.2
    # 观察中心点：(0, 0, 0)
    # 向上方向：(0, 0, 1) 即 Z 轴向上
    gluLookAt(0.0, -cam_dist / zoom, 0.8 / zoom,
              0.0, 0.0, 0.0,
              0.0, 0.0, 1.0)

    # 应用用户控制的旋转（绕 X 和 Z 轴）
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 0, 1)

    # 绘制场景物体
    draw_axes()                      # 坐标轴
    draw_planet(PLANET_RADIUS)       # 行星
    draw_satellite()                 # 卫星

    glutSwapBuffers()                # 双缓冲交换


def idle():
    """
    空闲回调函数：更新动画状态并请求重绘
    """
    global orbit_angle
    orbit_angle = (orbit_angle + 0.15) % 360.0  # 卫星角度递增（速度 0.15 度/帧）
    glutPostRedisplay()                         # 触发重绘


def keyboard(key, _x, _y):
    """
    普通按键回调函数
    """
    global zoom
    k = key.decode("utf-8", errors="ignore").lower()  # 解码并转为小写
    if k == 'q' or ord(key) == 27:   # Q 键或 ESC 键退出
        sys.exit(0)
    if k == '+':                     # 放大
        zoom *= 1.08
    if k == '-':                     # 缩小
        zoom /= 1.08
    glutPostRedisplay()              # 重绘


def special(key, _x, _y):
    """
    特殊按键回调函数（方向键）
    """
    global rot_x, rot_y
    if key == GLUT_KEY_UP:           # 上方向键：绕 X 轴向上旋转
        rot_x -= 3
    elif key == GLUT_KEY_DOWN:       # 下方向键：绕 X 轴向下旋转
        rot_x += 3
    elif key == GLUT_KEY_LEFT:       # 左方向键：绕 Z 轴向左旋转
        rot_y -= 3
    elif key == GLUT_KEY_RIGHT:      # 右方向键：绕 Z 轴向右旋转
        rot_y += 3
    glutPostRedisplay()              # 重绘


def main():
    """
    主函数：初始化 GLUT，注册回调函数，进入主循环
    """
    glutInit(sys.argv)                                              # 初始化 GLUT
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)       # 双缓冲、RGB、深度缓冲
    glutInitWindowSize(WINDOW_W, WINDOW_H)                          # 设置窗口大小
    glutCreateWindow(b"Planet + Cuboid Satellite Demo")             # 创建窗口

    init_gl()                                                       # OpenGL 初始化

    # 注册各种回调函数
    glutDisplayFunc(display)      # 显示回调
    glutIdleFunc(idle)            # 空闲回调（动画）
    glutReshapeFunc(reshape)      # 窗口大小改变回调
    glutKeyboardFunc(keyboard)    # 键盘回调
    glutSpecialFunc(special)      # 特殊按键回调

    # 打印控制说明
    print("\n=== 控制说明 ===")
    print("方向键: 旋转视角")
    print("+ / - : 缩放")
    print("Q 或 ESC: 退出\n")

    glutMainLoop()                # 进入 GLUT 主循环


if __name__ == '__main__':
    main()
