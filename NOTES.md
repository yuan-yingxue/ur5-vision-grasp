# 开发笔记

> 搭这套视觉抓取链路时的参数记录、结论和踩过的坑。
> 按主题组织，方便以后查；按时间的调试过程留在 commit 里。

---

## 1. 环境

| 组件 | 版本 / 配置 |
|---|---|
| 系统 | Windows 11 + WSL2 Ubuntu 22.04 |
| ROS2 | Humble |
| Python | 3.10.12 |
| PyTorch | 2.14.1+cu130 |
| OpenCV | 5.0.0（headless） |
| ultralytics | 8.4.194 |
| setuptools | 79.0.1（必须 <80，colcon-core 要求） |
| RMW | rmw_cyclonedds_cpp |

```bash
# ~/.bashrc
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

```ini
# ~/.wslconfig（Windows 侧）
[wsl2]
networkingMode=mirrored
autoProxy=true
memory=9GB
swap=8GB
```

---

## 2. 关键参数与实测数字

| 项目 | 数值 | 怎么来的 |
|---|---|---|
| 棋盘格方格边长 | 24.7 mm（标称 25） | 打印后用尺子量 |
| 相机内参（4096×3072） | fx 2920.29 / fy 2920.76 / cx 2029.76 / cy 1542.84 | cv2.calibrateCamera |
| **K640（实际用）** | fx 456.29 / fy 456.37 / cx 317.15 / cy 241.07 | 按 0.15625 缩放 |
| 标定重投影误差 | 1.37 px（旧图）/ **0.51 px**（固定机位新图） | calibrateCamera 返回 |
| 相机高度 | **81.4 cm** | 棋盘格 solvePnP 解出 |
| 相机倾斜 | 2.5° | 同上 |
| 空间分辨率 | 1 px ≈ 1.1 mm @ 0.5 m | 0.5 / fx |
| 检测 mAP50 | 0.972 / mAP50-95 0.900 | 60 张训练 80 epochs |
| 分割 mask mAP50 | **0.95** | 同一批数据，yolov8n-seg |
| 推理速度 | 3.3 ms（detect）/ 4.7 ms（seg） | val 输出 |
| 检测节点频率 | 9.95 Hz | ros2 topic hz |
| 抓取到位误差 | **4–10 mm** | MoveIt 执行后查 TF |

---

## 3. 链路与各节点

```
image_cycler → /camera/image_raw → detector_seg → /seg_polygons
    → grasp_pose_v3 → /grasp_poses_v3（全部）+ /grasp_target（目标类）
    → grasp_executor → /move_action → move_group → /execute_trajectory
    → fake hardware → /joint_states → RViz

det_view ← 图像 + /seg_polygons + /grasp_poses_v3 → /detection_view → rqt_image_view
```

| 节点 | 作用 |
|---|---|
| `detector_seg.py` | YOLOv8-seg 推理，每个 mask 取轮廓 → approxPolyDP → 最多 32 点 |
| `grasp_pose_v3.py` | 多边形全部反投影到 z=0 → 世界坐标 minAreaRect → 位姿 |
| `grasp_executor.py` | 组 MoveGroup 目标（位置 + 朝向约束）→ 发 action → 查 TF 算误差 |
| `image_cycler.py` | 循环发一组图，替代只能发一张的 image_publisher |
| `add_table.py` | 往规划场景加桌面碰撞体 |
| `det_view.py` | 检测结果可视化（自动裁剪到目标活动区域） |

**消息格式**：`/seg_polygons` 每物体一段 `[ n, x1,y1, ..., xn,yn, cls, conf ]`。

---

## 4. 参数与阈值的依据

| 参数 | 取值 | 依据 |
|---|---|---|
| `conf` / `iou`（检测） | 0.5 / 0.45 | 单张图上 7 个框 → 3 个，其余为重复框或低置信误检 |
| `conf_target`（抓取） | **0.9** | 8 张图里真目标 0.95–0.99，一个误检 0.81，中间有 0.14 的空隙 |
| `vel_scale`（执行） | 0.35 | 0.1 时单次动作 42 秒，太慢；0.35 约 12 秒 |
| 位置约束 | 10 mm 直径球 | 比这更严会让规划失败率上升 |
| 朝向约束 | 0.2 rad | 夹爪朝下已经由四元数保证，容差可放宽 |
| 桌面碰撞体 `top_z` | −5 mm | 设在 0 会和 UR5 的 base_link 碰撞几何重叠，导致自身碰撞 |
| `exclude_bottom`（可视化） | 0.25 | 画面底部是无关内容，裁掉 |

---

## 5. 踩坑记录

### A. 名字写错但静默失效
| 现象 | 真因 |
|---|---|
| 话题名没变 | `-r image:=...` 应该是 `image_raw` |
| 参数没生效 | `-p rate:=2.0` 应该是 `publish_rate` |
| `Node not found` | 节点名 `ImagePublisher` 区分大小写 |

### B. 依赖版本冲突
| 报错 | 冲突 |
|---|---|
| `canonicalize_version() got an unexpected keyword` | setuptools 84 vs packaging 21.3 |
| `numpy.core.multiarray failed to import` | numpy 2 vs apt 装的 matplotlib/pandas |
| `_ARRAY_API not found`（cv_bridge） | numpy 2 vs apt 版 cv_bridge |
| `TypeError: can only extend array with array` | `msg.data` 是 array.array，不能 `+=` list |

### C. 文件位置 / 构建
| 现象 | 真因 |
|---|---|
| `ModuleNotFoundError` | `.py` 放到了外层包目录 |
| 编译了却找不到 | 在 `src/` 里跑 colcon build，生成了错位的 install |
| launch 找不到文件 | `launch/` 目录不存在，或没写进 data_files |

### D. WSL 网络
| 现象 | 解决 |
|---|---|
| git push 卡死无输出 | `.wslconfig` 加 `networkingMode=mirrored` + `autoProxy=true` |
| 节点互相看不见 | 换 CycloneDDS |
| pip 报 `Network is unreachable` | 加 `-i 清华源` |

### E. 数据格式
| 现象 | 真因 |
|---|---|
| 标签每行几十个字段 | Roboflow 项目类型选成了 Segmentation，导出的是多边形 |
| `data.yaml` 找不到图 | `../train/images` 相对路径解析错 |

### F. 几何 / 坐标
| 现象 | 真因 |
|---|---|
| `/grasp_points` 一直空数组 | tf 里相机光轴朝前，射线平行桌面，`s<0` 全被丢弃 |
| 3D 坐标差 6.4 倍 | 用了全分辨率 K 而不是 K640 |
| 尺寸偏大 2~4 倍 | 相机高度是假设值；且高物体的上半部分不在 z=0 上 |

### G. 规划 / 执行
| 现象 | 真因 | 处理 |
|---|---|---|
| `99999` 失败率 50% | 目标离基座 23 cm，接近基座正下方奇异区 | 平移相机 tf 的 x +30 cm，目标到 55 cm |
| `-2 INVALID_MOTION_PLAN` 偶发 | 时间参数化产生不合法轨迹 | 0.5 秒延迟重试（最多 2 次） |
| 反复回同一位姿 | 同一张图 10 Hz 重复发同一目标 | 位姿去重（1 cm / 5°） |
| 能规划到 z<0 | 规划场景里没有桌面 | `add_table` 加 CollisionObject |
| 开度恒等于上限 | 物体短边 8.2 cm + 余量 1 cm 超夹爪最大开度 | 减 margin；本质是物体超限 |

---

## 6. 三个排查过程

### 6.1 空数组：指标正常 ≠ 结果正确
`/grasp_points` 一直输出空数组，但所有话题频率正常，也不报错。
手算 `s = (0 - 0.8) / 1.0 = -0.8` 才反应过来：tf 里相机是平视的，
光轴朝前，射线永远打不到脚下的桌面。加 180° 俯视旋转后正常。

**教训**：进程不崩、频率正常、没有报错，唯一表现是数据为空。

### 6.2 规划失败不是规划器的问题
失败率 50%，错误码 99999。先算目标的几何位置：离基座只有 23 cm，
正好在奇异区。平移 30 cm 后失败率降到 12%，剩下的偶发 `-2` 加重试后基本消失。

**教训**：规划失败先看目标几何合理性，再调规划器参数。

### 6.3 两张棋盘格照片解出的位姿差 12 cm
同一个固定机位拍两张，解出的相机位置差 `Δx=4cm, Δy=11cm`。
相机没动，是**棋盘格被重新摆过**。之后拍演示图时让棋盘格全程留在画面里不动。

**教训**：用平面靶标定外参时，靶标的位置就是坐标系原点，动了靶标等于换了坐标系。

---

## 7. 待解决

- [ ] **`tool0` 落在 z=0 没有夹爪高度补偿** —— 真实夹爪约 10 cm，会插进桌面
- [ ] **`INVALID_MOTION_PLAN` 只是重试兜底**，没解决时间参数化的问题
- [ ] **演示物体尺寸接近夹爪极限**（8.5 cm vs 2F-85 的 8.5 cm）
- [ ] **背景误检**：场景里没有的杯子和耳机也会被检出（0.3–0.8）
- [ ] **反投影假设物体贴桌面**：有高度的物体会把上半部分投到桌面外
- [ ] **`/seg_polygons` 缺 header**（时间戳 / frame_id）
- [ ] **还没上真机**：目前只有 fake hardware + 手机拍的照片
