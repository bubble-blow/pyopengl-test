import math
import sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

WINDOW_W, WINDOW_H = 1100, 760

# Planet
PLANET_RADIUS = 1.2
LAT_STEPS = 16
LON_STEPS = 24

# Satellite (cuboid)
SAT_W, SAT_H, SAT_D = 0.5, 0.25, 0.2
ORBIT_RADIUS = 2.4

rot_x, rot_y = 18.0, -30.0
zoom = 1.0
orbit_angle = 0.0


def draw_axes(length=3.5):
    glDisable(GL_LIGHTING)
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3f(1, 0.2, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(length, 0, 0)
    glColor3f(0.2, 1, 0.2)
    glVertex3f(0, 0, 0)
    glVertex3f(0, length, 0)
    glColor3f(0.2, 0.5, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, length)
    glEnd()
    glEnable(GL_LIGHTING)


def draw_lat_lon_lines(radius, lat_steps=LAT_STEPS, lon_steps=LON_STEPS):
    glDisable(GL_LIGHTING)
    glColor3f(0.05, 0.08, 0.15)
    glLineWidth(1.2)

    # 纬线（除极点）
    for i in range(1, lat_steps):
        phi = -math.pi / 2 + i * math.pi / lat_steps
        z = radius * math.sin(phi)
        r = radius * math.cos(phi)
        glBegin(GL_LINE_LOOP)
        for j in range(lon_steps):
            t = 2 * math.pi * j / lon_steps
            glVertex3f(r * math.cos(t), r * math.sin(t), z)
        glEnd()

    # 经线
    for j in range(lon_steps):
        t = 2 * math.pi * j / lon_steps
        glBegin(GL_LINE_STRIP)
        for i in range(lat_steps + 1):
            phi = -math.pi / 2 + i * math.pi / lat_steps
            r = radius * math.cos(phi)
            z = radius * math.sin(phi)
            glVertex3f(r * math.cos(t), r * math.sin(t), z)
        glEnd()

    glEnable(GL_LIGHTING)


def draw_planet(radius=PLANET_RADIUS):
    # 球体底色
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (0.22, 0.52, 0.95, 1.0))
    quad = gluNewQuadric()
    gluQuadricNormals(quad, GLU_SMOOTH)
    gluSphere(quad, radius, 64, 64)
    gluDeleteQuadric(quad)

    # 叠加经纬线
    draw_lat_lon_lines(radius * 1.002)


def draw_colored_cuboid(w, h, d):
    x, y, z = w / 2.0, h / 2.0, d / 2.0

    faces = [
        # front
        ((0, 0, 1), (1.0, 0.25, 0.25), [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]),
        # back
        ((0, 0, -1), (0.25, 1.0, 0.25), [(-x, -y, -z), (-x, y, -z), (x, y, -z), (x, -y, -z)]),
        # left
        ((-1, 0, 0), (0.25, 0.55, 1.0), [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)]),
        # right
        ((1, 0, 0), (1.0, 0.9, 0.25), [(x, -y, -z), (x, y, -z), (x, y, z), (x, -y, z)]),
        # top
        ((0, 1, 0), (1.0, 0.4, 0.95), [(-x, y, -z), (-x, y, z), (x, y, z), (x, y, -z)]),
        # bottom
        ((0, -1, 0), (0.25, 1.0, 0.95), [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)]),
    ]

    glBegin(GL_QUADS)
    for normal, color, verts in faces:
        glNormal3f(*normal)
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (*color, 1.0))
        for vx, vy, vz in verts:
            glVertex3f(vx, vy, vz)
    glEnd()


def draw_satellite():
    global orbit_angle
    t = math.radians(orbit_angle)
    x = ORBIT_RADIUS * math.cos(t)
    y = ORBIT_RADIUS * math.sin(t)
    z = 0.35 * math.sin(2.0 * t)

    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(orbit_angle * 2.0, 0, 0, 1)
    glRotatef(35.0, 1, 0, 0)
    draw_colored_cuboid(SAT_W, SAT_H, SAT_D)
    glPopMatrix()


def init_gl():
    glClearColor(0.02, 0.02, 0.05, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_NORMALIZE)

    glLightfv(GL_LIGHT0, GL_POSITION, (4.0, 5.0, 7.0, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.95, 0.95, 0.95, 1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0, 1.0, 1.0, 1.0))

    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (0.7, 0.7, 0.7, 1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50)


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

    gluLookAt(0.0, -6.0 / zoom, 3.5 / zoom,
              0.0, 0.0, 0.0,
              0.0, 0.0, 1.0)

    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 0, 1)

    draw_axes()
    draw_planet(PLANET_RADIUS)
    draw_satellite()

    glutSwapBuffers()


def idle():
    global orbit_angle
    orbit_angle = (orbit_angle + 0.15) % 360.0
    glutPostRedisplay()


def keyboard(key, _x, _y):
    global zoom
    k = key.decode("utf-8", errors="ignore").lower()
    if k == 'q' or ord(key) == 27:
        sys.exit(0)
    if k == '+':
        zoom *= 1.08
    if k == '-':
        zoom /= 1.08
    glutPostRedisplay()


def special(key, _x, _y):
    global rot_x, rot_y
    if key == GLUT_KEY_UP:
        rot_x -= 3
    elif key == GLUT_KEY_DOWN:
        rot_x += 3
    elif key == GLUT_KEY_LEFT:
        rot_y -= 3
    elif key == GLUT_KEY_RIGHT:
        rot_y += 3
    glutPostRedisplay()


def main():
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutCreateWindow(b"Planet + Cuboid Satellite Demo")

    init_gl()

    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)

    print("\n=== 控制说明 ===")
    print("方向键: 旋转视角")
    print("+ / - : 缩放")
    print("Q 或 ESC: 退出\n")

    glutMainLoop()


if __name__ == '__main__':
    main()
