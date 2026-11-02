# 学习笔记（Day 0 – 5）

> 用途：面试素材 + 复盘。每天收工前更新。
> 原则：只记「能复述的事实」和「踩过的坑」，不写流水账。

---

## 0. 数字账本（面试用，最重要）

| 指标 | 数值 | 怎么来的 |
|---|---|---|
| 训练集规模 | **60 张 / 182 个框 / 3 类** | Roboflow 标注后统计 |
| 数据划分 | train 42 / valid 12 / test 6 | Roboflow 默认 70/20/10 |
| **mAP50** | **0.972** | 80 epochs 训练后验证 |
| mAP50-95 | 0.900 | 同上（说明框贴合度高） |
| Precision / Recall | 0.949 / 0.976 | 同上 |
| 单类 mAP50 | counter 0.995 / cup 0.995 / **earphone 0.925** | earphone 最差 |
| 推理速度 | **3.3 ms/张**（640×480） | YOLO val 输出 |
| 训练耗时 | **约 1 分钟**（80 epochs，RTX 4060） | 日志 `0.016 hours` |
| 检测节点频率 | **9.95 Hz** | `ros2 topic hz /detections` |
| 误报情况 | 原始 7 个框 → 过滤后 3 个（**误报率 57%**） | 单张验证图对比 |
| 输入图像尺寸 | 640×480（原图 4:3，Fit within 640） | Roboflow 预处理 |

---

## 1. 环境清单（重装时照着抄）

| 组件 | 版本 / 配置 |
|---|---|
| 系统 | Windows 11 24H2 + WSL2 Ubuntu 22.04 |
| ROS2 | Humble |
| Python | 3.10.12（系统 python3） |
| PyTorch | 2.14.1+cu130 |
| numpy | 2.2.6 |
| scipy | 1.15.3 |
| matplotlib | 3.10.9 |
| pandas | 2.3.3 |
| Pillow | 12.3.0 |
| opencv | 5.0.0（opencv-python-headless） |
| ultralytics | 8.4.194 |
| setuptools | **79.0.1**（必须 <80） |
| packaging | 26.3 |
| **RMW** | **rmw_cyclonedds_cpp**（写进 ~/.bashrc） |

**关键配置**：

```bash
# ~/.bashrc
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# ~/.wslconfig（Windows 侧）
[wsl2]
networkingMode=mirrored
autoProxy=true
```

---

## 2. 每日记录

### Day 0（10/27）环境
- **做了什么**：装 pip → torch → numpy/scipy/opencv，验证 GPU
- **卡在哪**：`pip: command not found`；`ros2 --version` 不存在
- **怎么解决**：`apt install python3-pip`；ROS 版本看 `printenv ROS_DISTRO`
- **记住**：`pip --user` 装的东西优先级高于系统包，埋下了后面一连串 ABI 坑

### Day 1（10/28）节点与话题
- **做了什么**：turtlesim + 手写 `circle.py`（发布）/ `pose_listener.py`（订阅），首次 git 提交
- **卡在哪**：
  1. `colcon build` 报 `canonicalize_version() got an unexpected keyword` → setuptools 84 vs packaging 21.3
  2. `setup.py` 的 `circle` 写了两次 → 报 `'setup.py' is not a Distutils setup script`（**真因在报错上一行**）
  3. `Package not found` → 忘了 `source install/setup.bash`
- **怎么解决**：装 `setuptools<80` + `packaging>=23`；删重复行
- **一句话总结**：**发布者是"我主动发"，订阅者是"别人发给我"——后者必须给回调**

### Day 2（10/29）服务 / 参数 / launch / bag
- **做了什么**：`ros2 service call /spawn`、`param_circle` 热改半径、写 `demo.launch.py`、录放 bag
- **卡在哪**：
  1. `param_circle.py` 放到了外层包目录 → `ModuleNotFoundError`
  2. 在 `~/ros2_ws/src` 里跑 `colcon build` → 生成错位的 `src/install`
  3. launch 报 `file 'demo.launch.py' was not found in share` → **压根没建 launch 目录**
- **怎么解决**：
  - 文件必须在内层 `turtle_ctrl/turtle_ctrl/`
  - `colcon build` 只能在 `~/ros2_ws`（有 `src/` 的那层）
  - launch 目录 + `data_files` 里加 `glob('launch/*.launch.py')`
- **一句话总结**：**动了"注册信息"就要 build，只改代码内容不用（`--symlink-install`）**

### Day 3（10/30）tf2 与四元数
- **做了什么**：`static_transform_publisher` 发布 `base_link→camera_link`、`tf2_echo` 查询、`view_frames` 生成树、手算带旋转的坐标变换
- **核心公式**：`P_base = R · P_cam + t`
- **手算结果**：相机俯 90°，点 `(0.2,0,1.0)` → **`(0.7, -1.0, 0.8)`**（已用 scipy 验证）
- **卡在哪**：`tf2_echo` 刷 `Waiting ... frame does not exist` 十几分钟
- **怎么解决**：**换 CycloneDDS**（Fast DDS 在 WSL 下端点能匹配但数据到不了）
- **一句话总结**：**四元数 = 轴 × sin(θ/2) + cos(θ/2)；复合旋转是四元数乘法，不是点乘**

### Day 4（10/31）YOLO 训练
- **做了什么**：装 ultralytics → coco8 验证 GPU → 拍 60 张 → Roboflow 标注 → 训练 80 轮 → 读指标
- **卡在哪**：
  1. `pip install` 报 `Network is unreachable` → 没加镜像（IPv6 无路由）
  2. `numpy.core.multiarray failed to import` → 系统 matplotlib/pandas/Pillow 是 numpy 1.x 编译的
  3. **Roboflow 项目类型选成了 Segmentation** → 标签是多边形（每行 49/97/109 个字段）
  4. `data.yaml` 里 `../train/images` → 解析到不存在的目录
  5. `git commit` 显示 nothing to commit → `runs/` `datasets/` 被 gitignore
- **怎么解决**：
  - 加 `-i 清华源`；`pip --user --upgrade matplotlib pandas pillow scipy`
  - **写脚本把多边形转外接矩形**（182 个框），不用重标
  - `data.yaml` 改成 `path:` + 相对路径
  - 证据 `cp` 到 `docs/day04/` 再提交
- **一句话总结**：**训练只要 1 分钟，标注和数据处理才是主要工作量**

### Day 5（11/01）包成 ROS2 节点
- **做了什么**：`image_publisher` 造假相机 → 离线推理验证 → 写 `detector.py` → 联调
- **节点接口**：订阅 `/camera/image_raw`（`sensor_msgs/Image`）→ 发布 `/detections`（`Float32MultiArray`，每 6 个数一组）
- **过滤策略**：`conf=0.5` + `iou=0.45` + **每类只保留最高分**（场景先验：每类一个物体）
- **卡在哪**：
  1. remap 写成 `-r image:=...`（实际话题叫 `image_raw`）→ **静默失效**
  2. param 写成 `-p rate:=2.0`（实际叫 `publish_rate`）→ **静默失效**
  3. 节点名是 `/ImagePublisher`（大写），`/image_publisher` 查不到
  4. **`cv_bridge` 报 `_ARRAY_API not found` + segfault**（同样是 numpy 2 vs apt 包的 ABI 问题）
  5. heredoc 粘贴串行 → `EOFnt(...)` 乱码 + SyntaxError
- **怎么解决**：
  - 改完 remap/param 立刻用 `topic list` / `param list` / `echo --field` 验证
  - **不用 cv_bridge，6 行手动解码** `sensor_msgs/Image`（`data` → `reshape(height, step)` → 截断 → RGB→BGR）
  - 长脚本写文件再跑，别用 heredoc 粘
- **一句话总结**：**节点和脚本的区别是"谁控制循环"——脚本我调用别人，节点别人调用我**

---

## 3. 踩过的坑（按类型）

### 类型 A：名字写错但**静默失效**
| 现象 | 真因 |
|---|---|
| 话题名没变 | `-r image:=...` 应该是 `image_raw` |
| 频率没变 | `-p rate:=2.0` 应该是 `publish_rate` |
| `Node not found` | 节点名 `ImagePublisher` 区分大小写 |

**规律**：ROS 的 remap / param 匹配不上就不管，**不报错**。改完必须验证。

### 类型 B：pip 覆盖系统包导致 ABI 崩
| 报错 | 冲突 |
|---|---|
| `canonicalize_version() got an unexpected keyword` | setuptools 84 vs packaging 21.3 |
| `ValueError: numpy.dtype size changed` | numpy 2 vs 系统 scipy 1.8 |
| `numpy.core.multiarray failed to import` | numpy 2 vs 系统 matplotlib/pandas/Pillow |
| `AttributeError: _ARRAY_API not found`（cv_bridge） | numpy 2 vs apt 版 cv_bridge |

**规律**：`~/.local` 优先级 > `/usr/lib/python3/dist-packages`。**pip 装了 numpy，就要把依赖 numpy ABI 的包都用 pip 装一遍。**

### 类型 C：文件位置 / 构建目录
| 现象 | 真因 |
|---|---|
| `ModuleNotFoundError: turtle_ctrl.xxx` | `.py` 放到了外层包目录 |
| 编译了却找不到模块 | 在 `src/` 里跑 `colcon build`，生成错位 `install` |
| launch 找不到文件 | `launch/` 目录不存在，或没写进 `data_files` |

### 类型 D：WSL 网络
| 现象 | 真因 | 解决 |
|---|---|---|
| `git push` 卡死、无输出 | WSL NAT 看不到 Windows 的 `127.0.0.1:7897` 代理 | `.wslconfig` 加 `networkingMode=mirrored` + `autoProxy=true` |
| ROS 节点互相看不见 | Fast DDS 在 WSL 下发现不稳定 | 换 CycloneDDS |
| `Network is unreachable` | pip 走 IPv6，无出口 | 加 `-i 镜像` |

### 类型 E：数据格式
| 现象 | 真因 |
|---|---|
| 标签每行 49/97/109 个字段 | Roboflow 项目是 Segmentation，导出多边形 |
| `data.yaml` 找不到图片 | `../train/images` 相对路径解析错 |
| 误报 57% | 训练集缺"负样本"（背景干扰物），且每张图都是"三类各一个"的固定构图 |

---

## 4. 三个可复述的技术故事（面试用，各 90 秒）

### 故事 1：numpy 2 引发的连环 ABI 崩溃
> 装完 PyTorch 后，`colcon build` 报 setuptools 版本冲突，接着 scipy、matplotlib、pandas 依次崩，最后 `cv_bridge` 直接 segfault。现象各不相同，根因是同一个：pip 装的 numpy 2 覆盖了系统 numpy 1.x，而系统里用 apt 装的 C 扩展是按旧 ABI 编译的。
> 我的处理不是一个个修，而是先定位共同根因，然后分两类解决：能用 pip 升级的（scipy/matplotlib/pandas）全部升级到 numpy 2 版本；apt 装的 cv_bridge 无法升级，就自己写了 6 行代码解码 `sensor_msgs/Image`，绕过这个依赖。

**这句话的价值**：讲出了"同一个根因、不同表象"的诊断能力。

### 故事 2：从 Fast DDS 换到 CycloneDDS
> 调 tf2 时 `tf2_echo` 一直报"坐标系不存在"，但 `ros2 topic echo /tf_static` 明明有数据，`ros2 topic info` 也显示订阅端 QoS 完全匹配。我依次排除了：发布者是否存活、话题是否存在、QoS 是否兼容、是否是迟到订阅者补发失败——都不是。
> 最后对比测试两种 DDS 实现：Fast DDS 在该 WSL 环境下"端点能匹配、数据传不过去"，CycloneDDS 连测三次都是 2–3 秒出结果。于是把默认 RMW 换成 CycloneDDS，问题消失。这个改动对后面多节点通信都生效。

**这句话的价值**：讲出了对照实验和"用数据说话"的排查方法。

### 故事 3：把分割标注转成检测标注
> 用 Roboflow 标注时项目类型选成了 Instance Segmentation，导出的标签是多边形（每行几十个坐标）。我不想重标 60 张，于是写脚本把每个多边形的外接矩形算出来（min/max），转成标准 YOLO 检测标签，182 个框全部转换成功，格式校验通过。
> 判断依据是：抓取只需要物体位置和大小，像素级掩码没有额外价值；而分割模型推理慢 2–3 倍，对实时抓取是负收益。

**这句话的价值**：讲出了"用需求反推技术选型"的判断力。

---

## 5. 未解清单 / 待办

- [ ] **`/detections` 缺 header**（无时间戳、无 frame_id）→ Day 7 算位姿前必须升级成 `vision_msgs/Detection2DArray` 或自定义带 header 的消息
- [ ] **假相机会掉帧**（标称 10 Hz，实测偶发到 5 Hz）→ Day 10 抓取循环要能处理"没有新图"
- [ ] **误报率 57%**（7→3）→ 补"只含 1–2 个物体"和"空场景"的图重训，Day 11 做
- [ ] **每类 top-1 是场景先验**，多物体场景会失效 → 需要 NMS 调参或聚类去重
- [ ] Day 4 / Day 5 的证据（`docs/day04`、`docs/day05`）确认已 commit & push
- [ ] README 进度表更新到 Day 5
- [ ] `grasp_seg_backup/`（多边形原始标注）确认不需要后可删

---

## 6. 每天收工前自检

- [ ] 今天有 commit 吗？
- [ ] 有能截图/录屏的产出吗？
- [ ] 坑和解决办法记进这里了吗？
- [ ] 明天的第一件事写下来了吗？
