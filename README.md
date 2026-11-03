# UR5 Vision Grasp · 21 天冲刺

> 从 ROS2 零基础，到 UR5 机械臂视觉抓取闭环。
> 21 天，每天 2–3 小时，全部过程记录在这个仓库里。

---

## 这是什么

一个从零搭建的 **ROS2 视觉抓取系统**：把一张相机图像，变成机械臂能执行的抓取位姿。

```
图像 → YOLO 检测 → 像素反投影 → MoveIt2 规划 → UR5 执行
```

![pipeline](docs/pipeline_diagram.png)

*反投影依赖三个前提：相机内参、相机到基座的坐标变换、桌面平面假设。*

**背景**：电气工程本科，保研至浙江大学工程师学院机械（具身操作方向）。毕业设计课题为**电力场景下的机械臂操作**，硬件平台是实验室的 UR5。这个仓库是入学前把技术栈跑通的过程记录，也是毕设的前期工作。

**当前状态**：检测 → 相机标定 → 像素到 3D 已打通，正在做抓取位姿（位置 + 姿态）。

---

## 进度

| 周 | 天 | 内容 | 状态 |
|---|---|---|---|
| — | Day 1 | 节点与话题（publisher / subscriber） | ✅ |
| — | Day 2 | 服务、参数、launch、rosbag | ✅ |
| 第一周 | Day 3 | tf2 坐标变换 + 四元数 | ✅ |
| 第一周 | Day 4 | YOLO 训练（mAP50 0.972） | ✅ |
| 第一周 | Day 5 | 包成 ROS2 检测节点 | ✅ |
| 第一周 | Day 6 | 相机标定 + 像素到 3D（RMS 1.37 px） | ✅ |
| 第一周 | Day 7 | 抓取位姿（位置 + 姿态） | 🔄 |
| 第二周 | Day 8–10 | MoveIt2 + 抓取闭环 + 成功率统计 | ⬜ |
| 第二周 | Day 11–14 | 失败分析 + 示教数据管线 + 论文阅读 | ⬜ |
| 第三周 | Day 15–21 | 面试准备 + 作品集整理 | ⬜ |

详细日程与每日证据见 `docs/` 与提交记录。

---

## 目前完成的内容

| 文件 / 目录 | 说明 |
|---|---|
| `src/turtle_ctrl/turtle_ctrl/circle.py` | 发布者：驱动 turtlesim 画圆 |
| `src/turtle_ctrl/turtle_ctrl/pose_listener.py` | 订阅者：实时打印位姿 |
| `src/turtle_ctrl/turtle_ctrl/param_circle.py` | 用 ROS2 参数控制半径，支持运行时热改 |
| `src/turtle_ctrl/turtle_ctrl/detector.py` | YOLOv8 检测节点：订阅图像，发布像素框 |
| `src/turtle_ctrl/turtle_ctrl/grasp_pose.py` | 反投影节点：像素框 → 基座 3D 位姿 |
| `src/turtle_ctrl/launch/demo.launch.py` | 一条命令起多节点，带条件开关 |
| `calib/` | 15 张棋盘格标定图 + `camera_params.npz` |

**已验证**：

- 检测：60 张图训练，mAP50 **0.972**，单帧推理 **3.3 ms**
- 标定：15 张图，重投影误差 **1.37 px**，输出 `K640`
- 反投影：三个物体输出 `(X, Y, Z)`，Z 恒为 0（平面假设的结果）
- 检测节点能跟上 **9.95 Hz** 的输入频率
- `ros2 param set` / `ros2 bag` / launch 条件启动均已跑通

---

## 关键数字

| 指标 | 值 | 含义 |
|---|---|---|
| mAP50 | 0.972 | 60 张训练 / 12 张验证，样本偏小 |
| 推理延迟 | 3.3 ms | 640×480 输入 |
| 标定 RMS | 1.37 px | 换算到 0.5 m 约 0.23 mm |
| 空间分辨率 | 1 px ≈ 1.1 mm | 相机高 0.8 m 时 |
| 检测频率 | 9.95 Hz | 够实时抓取 |

---

## 快速开始

**环境**：Windows 11 + WSL2 (Ubuntu 22.04) + ROS2 Humble + Python 3.10 + RTX 4060

```bash
# 0. 编译
cd ~/ros2_ws
colcon build --symlink-install --packages-select turtle_ctrl
source install/setup.bash
```

```bash
# 1. 发布相机到基座的坐标变换（终端 1）
ros2 run tf2_ros static_transform_publisher --x 0.5 --y 0.0 --z 0.8 \
  --qx 1 --qy 0 --qz 0 --qw 0 \
  --frame-id base_link --child-frame-id camera_link
```

```bash
# 2. 假相机（终端 2）—— 真机时换成真实相机驱动
ros2 run image_publisher image_publisher_node "$(ls ~/ros2_ws/datasets/grasp/valid/images/*.jpg | head -1)" \
  --ros-args -r image_raw:=/camera/image_raw -r camera_info:=/camera/camera_info -p frame_id:=camera_link
```

```bash
# 3. 检测（终端 3）
ros2 run turtle_ctrl detector

# 4. 反投影（终端 4）
ros2 run turtle_ctrl grasp_pose
```

预期在终端 4 看到：

```
[INFO] cls=1 conf=0.99 pos=(0.691, 0.206, 0.000)
[INFO] cls=0 conf=0.97 pos=(0.448, 0.033, 0.000)
[INFO] cls=2 conf=0.99 pos=(0.594, -0.248, 0.000)
```

---

## 仓库结构

```
ros2_ws/
├── src/turtle_ctrl/           # ROS2 包
│   ├── turtle_ctrl/           # Python 节点
│   ├── launch/                # launch 文件
│   ├── setup.py
│   └── package.xml
├── calib/                     # 标定图 + camera_params.npz
├── docs/                      # 每日证据（图 / 命令输出 / 链路图）
└── README.md
```

---

## 路线图

- **第一周**：ROS2 基础 → YOLO 训练 → 相机标定 → 像素到 3D
- **第二周**：MoveIt2 规划 + 抓取闭环 + 成功率统计 + 示教数据管线
- **第三周**：失败分析、简历与作品集、面试准备

---

## 关于

- 武汉大学 电气工程及其自动化（2027 届）
- 浙江大学 工程师学院 机械（2027 级，具身操作方向）
- 欢迎交流：通过 GitHub Issue 或 Profile 页联系
