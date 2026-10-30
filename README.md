# UR5 Vision Grasp · 21 天冲刺

> 从 ROS2 零基础，到 UR5 机械臂视觉抓取闭环。
> 21 天，每天 2–3 小时，全部过程记录在这个仓库里。

---

## 这是什么

一个从零开始搭建的 **ROS2 机器人视觉抓取系统**，最终目标是：

```
摄像头图像 → YOLO 检测 → 像素反投影 → 手眼标定 → MoveIt2 规划 → UR5 执行抓取
```

背景：电气工程本科，保研至浙江大学工程师学院机械（具身操作方向）。毕业设计课题为**电力场景下的机械臂操作**，硬件平台是实验室的 UR5。这个仓库是入学前把技术栈跑通的过程记录，也是毕设的前期工作。

**当前状态**：ROS2 基础已打通，正在进入视觉与坐标变换阶段。

---

## 进度

| 周 | 天 | 内容 | 状态 |
|---|---|---|---|
| — | Day 1 | 节点与话题（publisher / subscriber） | ✅ |
| — | Day 2 | 服务、参数、launch、rosbag | ✅ |
| 第一周 | Day 3 | tf2 坐标变换 | 🔄 |
| 第一周 | Day 4–5 | YOLO 训练 + 包成 ROS2 节点 | ⬜ |
| 第一周 | Day 6–7 | 相机标定 + 像素到 3D | ⬜ |
| 第二周 | Day 8–10 | MoveIt2 + 抓取闭环 + 成功率统计 | ⬜ |
| 第二周 | Day 11–14 | 失败分析 + 示教数据管线 + 论文阅读 | ⬜ |
| 第三周 | Day 15–21 | 面试准备 + 作品集整理 | ⬜ |

详细日程见 `docs/` 与每日提交记录。

---

## 目前完成的内容

| 文件 | 说明 |
|---|---|
| `src/turtle_ctrl/turtle_ctrl/circle.py` | 发布者：以固定线速度/角速度驱动 turtlesim 画圆 |
| `src/turtle_ctrl/turtle_ctrl/pose_listener.py` | 订阅者：实时打印乌龟位姿 |
| `src/turtle_ctrl/turtle_ctrl/param_circle.py` | 用 ROS2 参数控制圆半径，支持运行时热修改 |
| `src/turtle_ctrl/launch/demo.launch.py` | 一条命令启动三个节点，带 `use_circle` 开关 |

**已验证**：

- `ros2 param set /param_circle radius 2.0` 可实时改变圆的半径
- `ros2 bag record` / `play` 可录制并复现话题数据
- launch 文件用 `use_circle:=false` 可切换"录制模式"与"回放模式"

---

## 快速开始

环境：Windows 11 + WSL2 (Ubuntu 22.04) + ROS2 Humble + Python 3.10

```bash
# 1. 编译
cd ~/ros2_ws
colcon build --symlink-install --packages-select turtle_ctrl
source install/setup.bash

# 2. 启动（三个节点）
ros2 launch turtle_ctrl demo.launch.py

# 3. 另开终端，运行中改参数
ros2 param set /param_circle radius 2.0
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
├── docs/                      # 每日证据（截图、录屏、命令输出）
│   └── day02/
└── README.md
```

---

## 路线图

- **第一周**：ROS2 基础 + YOLO 训练 + 相机标定，做到"一张图 → 一个基座坐标系下的 3D 点"
- **第二周**：MoveIt2 规划 + 抓取闭环 + 成功率统计 + 示教数据管线
- **第三周**：失败分析、简历与作品集、面试准备

---

## 关于

- 武汉大学 电气工程及其自动化（2027 届）
- 浙江大学 工程师学院 机械（2027 级，具身操作方向）
- 欢迎交流：通过 GitHub Issue 或 Profile 页联系
