# PyOpenGL 3D 圆弧轨道 Demo

这是一个使用 **PyOpenGL + GLUT** 编写的 3D 绘图示例：
- 模型是一个**圆弧轨道**；
- 轨道横截面是**矩形**（径向宽度 × Z 方向高度）。

## 运行方式

```bash
pip install PyOpenGL PyOpenGL_accelerate
python demo_arc_track.py
```

> Linux 下若缺少 GLUT，可能还需要安装 freeglut（如 Ubuntu: `sudo apt install freeglut3-dev`）。

## 交互

- 方向键：旋转模型
- `+` / `-`：缩放
- `Q` 或 `ESC`：退出

## 可调参数

在 `demo_arc_track.py` 顶部可修改：
- `INNER_RADIUS`：内半径
- `CROSS_SECTION_WIDTH`：矩形截面宽度（径向）
- `CROSS_SECTION_HEIGHT`：矩形截面高度（Z方向）
- `ARC_DEGREES`：圆弧角度
- `SEGMENTS`：离散段数
