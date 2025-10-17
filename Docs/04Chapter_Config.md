# 第4章 配置参数完全手册

**版本**: V3.3.1  
**章节**: 4/6

> 本章节详细列出所有可调参数，说明其作用和推荐值。

---

## 4.1 坐标转换参数⭐

**文件**：`Config/experiment_config.json`

### transform_params

```json
"transform_params": {
  "scale_factor": 180.0,    // ⭐ 缩放因子（像素/米）
  "z_flip": -1,             // Z轴翻转因子
  "world_range": 6.0,       // 世界坐标范围（米）
  "screen_range": 1080      // 屏幕坐标范围（像素）
}
```

#### scale_factor（缩放因子）

**作用**：控制Motive坐标到PsychoPy坐标的缩放比例

**公式**：
```
X_screen = scale_factor × X_real
Y_screen = scale_factor × Z_real × z_flip
```

**推荐值**：

| 房间实际大小 | 推荐缩放因子 | 计算方式 | 显示效果 |
|-------------|------------|---------|---------|
| 4m × 4m | 270 | 1080/4 | 放大显示 |
| 5m × 5m | 216 | 1080/5 | 中等放大 |
| **6m × 6m** | **180** | 1080/6 | ✅ 默认，正好填满 |
| 7m × 7m | 154 | 1080/7 | 缩小显示 |
| 8m × 8m | 135 | 1080/8 | 更小显示 |

**调整建议**：
```
推荐值 = 理论值 × 0.9

例如：5m房间
理论值 = 1080 / 5 = 216
推荐值 = 216 × 0.9 = 194

原因：留出10%缓冲，避免边界光点消失
```

**效果示例**：

```
scale_factor = 180（默认）：
Motive移动1米 → PsychoPy光点移动180像素

scale_factor = 200（放大）：
Motive移动1米 → PsychoPy光点移动200像素（视觉更明显）

scale_factor = 150（缩小）：
Motive移动1米 → PsychoPy光点移动150像素（显示范围更广）
```

**修改后立即生效**：
- ✅ PsychoPy光点位置
- ✅ 所有坐标转换
- ✅ 碰撞检测阈值
- ✅ 隐藏目标半径显示

**无需修改代码，重启程序即可！**

---

## 4.2 场景配置参数

**文件**：`Config/experiment_config.json`

### scene_config

```json
"scene_config": {
  "room_size": [6.0, 6.0],          // 房间物理大小（米）
  "window_size": [1920, 1080],      // PsychoPy窗口大小（像素）
  "scene_size": [1080, 1080],       // 显示区域大小（像素）
  "num_hidden_targets": 3,          // 隐藏目标数量
  "target_radius": 0.4,             // 目标半径（米）
  "wallmarker_threshold": 1.0,      // 墙标到达阈值（米）
  "min_target_distance": 2.0        // 目标最小间距（米）
}
```

#### target_radius（目标半径）

**作用**：隐藏目标的检测半径

**默认**：0.4米（40cm）

**效果**：
```
参与者进入距离目标<0.4米的圆形区域 → 触发"找到目标"
```

**调整建议**：
- 0.3米：更难找到（需要精确到达）
- **0.4米**：推荐（适中）
- 0.5米：更容易找到（范围更大）

**PsychoPy显示**：
```
屏幕半径 = target_radius × scale_factor
         = 0.4 × 180
         = 72像素
```

#### wallmarker_threshold（墙标阈值）

**作用**：到达墙标的判定距离

**默认**：1.0米

**效果**：
```
参与者进入距离墙标<1.0米 → 触发"到达墙标"
```

**调整建议**：
- 0.5米：严格模式
- **1.0米**：推荐（宽松合理）
- 1.5米：非常宽松

---

## 4.3 实验流程参数

### phase_0 / phase_1

```json
"experiment_flow": {
  "phase_0": {
    "name": "认知地图建立",
    "default_trials": 20,       // 默认trial数量
    "timeout_wall": 30.0,       // 导航到墙标超时（秒）
    "timeout_target": 45.0      // 搜索目标超时（秒）
  }
}
```

#### timeout参数

**作用**：防止参与者长时间卡在某个任务

**效果**：
```
参与者超过30秒未到达墙标 → 自动跳过，进入下一阶段
参与者超过45秒未找到目标 → Trial失败，进入下一Trial
```

**调整建议**：
- timeout_wall: 20-40秒
- timeout_target: 30-60秒（搜索更难，给更多时间）

---

## 4.4 音频配置参数⭐

```json
"audio_config": {
  "wallmarker_go_dir": "Assets/Audios/WallMarker_go",
  "wallmarker_arrive_dir": "Assets/Audios/WallMarker_arrive",
  "target_go_dir": "Assets/Audios/Target_go",
  "target_arrive_dir": "Assets/Audios/Target_arrive",
  "common_dir": "Assets/Audios/Common",
  "interval_after_target_found": 2.0  // ⭐ 找到目标后等待时间
}
```

#### interval_after_target_found

**作用**：找到目标后，等待N秒再发出下一个指令

**默认**：2.0秒

**效果时间轴**：
```
t=0:    "找到了P2"（音频播放）
t=0-1:  音频播放中
t=1-2:  静默等待
t=2:    "前往墙标B3"（下一个指令）
```

**调整建议**：
| 值 | 效果 | 适用场景 |
|----|------|---------|
| 1.0秒 | 快节奏 | 熟练参与者 |
| **2.0秒** | **推荐** | 一般参与者 |
| 3.0秒 | 慢节奏 | 老年人、初学者 |
| 5.0秒 | 很慢 | 特殊需求 |

**修改位置**：
```json
"interval_after_target_found": 3.0  ← 改为3秒
```

**或代码中**（`map_phase.py` 第602行）：
```python
time.sleep(3.0)  # 改为3秒
```

---

## 4.5 NatNet配置参数

```json
"natnet_config": {
  "server_ip": "192.168.3.58",      // ⭐ Motive所在电脑IP
  "client_ip": "192.168.3.55",      // ⭐ Python程序所在电脑IP
  "use_multicast": true,             // 是否使用组播
  "connection_timeout": 5.0,         // 连接超时（秒）
  "skeleton_names": ["Skeleton_1", "Skeleton_2"],
  "rigid_body_names": ["RigidBody_1", "RigidBody_2"]
}
```

### IP配置指南

#### 情况1：同一台电脑运行Motive和Python

```json
"server_ip": "127.0.0.1",    // 本地回环
"client_ip": "127.0.0.1",
"use_multicast": false        // 单播模式
```

#### 情况2：Motive和Python在不同电脑

```json
"server_ip": "192.168.3.58",  // Motive电脑的实际IP
"client_ip": "192.168.3.55",  // Python电脑的实际IP  
"use_multicast": true         // 组播模式
```

**如何查找IP**：
```cmd
# Windows命令行
ipconfig

# 查找"以太网适配器"或"无线局域网适配器"
# IPv4地址：192.168.x.x
```

---

## 4.6 LSL配置参数

```json
"lsl_config": {
  "marker_stream_name": "Navigation_Markers",
  "marker_stream_type": "Markers",
  "degraded_mode_timeout": 10.0,    // Degraded模式超时
  "max_position_loss": 2.0          // 位置丢失最大时长
}
```

#### max_position_loss

**作用**：位置数据丢失超过N秒后的处理策略

**默认**：2.0秒

**效果**：
```
位置数据丢失（例如标记被遮挡）：
0-2秒：光点保持静止在最后有效位置
>2秒：显示警告，光点可能消失或特殊标记
```

**调整建议**：
- 1.0秒：严格模式（快速发现问题）
- **2.0秒**：推荐（容忍短暂遮挡）
- 5.0秒：宽松模式（适合复杂环境）

---

## 4.7 数据配置参数

```json
"data_config": {
  "behavior_dir": "Data/Behavior",
  "optitrack_dir": "Data/OptiTrack",
  "lsl_dir": "Data/LSL",
  "logs_dir": "Logs",
  "position_buffer_size": 100,       // 位置数据缓冲大小
  "auto_flush_interval": 10.0        // 自动刷新间隔（秒）
}
```

#### position_buffer_size

**作用**：Position.csv的批量写入缓冲区大小

**默认**：100行

**效果**：
```
接收100帧位置数据 → 一次性写入文件（减少I/O）
```

**调整建议**：
- 50：更频繁写入（数据更安全，I/O更多）
- **100**：推荐（平衡）
- 200：减少I/O（但丢失风险稍高）

#### auto_flush_interval

**作用**：强制刷新文件缓冲的时间间隔

**默认**：10.0秒

**效果**：
```
即使buffer未满，每10秒也会强制写入文件
```

---

## 4.8 可视化配置参数

```json
"visual_config": {
  "participant_colors": {
    "navigator": [1, -1, -1],    // 红色
    "observer": [-1, -1, 1],     // 蓝色
    "single": [1, 1, 1]          // 白色
  },
  "wall_colors": {
    "A": [-1, -1, 1],            // 蓝色
    "B": [-1, 1, -1],            // 绿色
    "C": [1, -1, -1],            // 红色
    "D": [1, 1, -1]              // 黄色
  },
  "marker_radius": 12,           // 墙标半径（像素）
  "participant_radius": 15,      // 参与者光点半径（像素）
  "text_height": 20              // 文本高度（像素）
}
```

#### 颜色格式

**PsychoPy颜色范围**：-1到+1

```
[-1, -1, -1] = 黑色
[1, 1, 1] = 白色
[1, -1, -1] = 红色
[-1, 1, -1] = 绿色
[-1, -1, 1] = 蓝色
[1, 1, -1] = 黄色
```

**修改示例**：
```json
// 将导航者改为绿色
"navigator": [-1, 1, -1]
```

---

## 4.9 鲁棒性配置参数

```json
"robustness_config": {
  "max_position_loss_time": 2.0,    // 位置丢失容忍时间
  "skeleton_timeout": 3.0,          // 骨骼数据超时
  "retry_attempts": 3,              // 重试次数
  "graceful_degradation": true      // 优雅降级
}
```

---

## 4.10 参数修改流程

### 标准流程

```
1. 编辑 Config/experiment_config.json
2. 保存文件
3. 重启程序
4. 验证效果
```

### 验证方法

#### 验证缩放因子

```bash
python Scripts\Tools\test_natnet_to_psychopy.py

# 移动Sub001 1米
# 观察PsychoPy窗口右上角显示的X或Y坐标
# 应该变化scale_factor像素
```

#### 验证音频间隔

```bash
# 运行实验，找到目标后计时
# "找到了P2" → [等待] → "前往B3"
# 等待时间应该 ≈ interval_after_target_found
```

---

## 4.11 高级参数

### LSL录制器参数（lsl_recorder.py）

**文件**：`Scripts/Tools/lsl_recorder.py`

```python
# 第68行：自动保存间隔
self.auto_save_interval = 30.0  # 秒

# 第445行：GUI窗口大小
self.setGeometry(100, 100, 1200, 800)  # (x, y, width, height)
```

### NatNet verbose输出

**文件**：`Scripts/Core/lsl_manager.py`

```python
# 第216行：print_level控制
self.natnet_client.set_print_level(0)  # 0=关闭, 1=开启, 20=每20帧
```

### PsychoPy帧率

**文件**：`Scripts/Tools/test_natnet_to_psychopy.py`

```python
# 第289行：控制帧率
time.sleep(1/30)  # 30 FPS

# 可改为：
time.sleep(1/60)  # 60 FPS（更流畅，CPU占用更高）
time.sleep(1/20)  # 20 FPS（省资源）
```

---

## 4.12 参数优化建议

### 场景A：小房间（4m×4m）

```json
{
  "transform_params": {
    "scale_factor": 240,     // 放大显示
    "world_range": 4.0
  },
  "scene_config": {
    "room_size": [4.0, 4.0],
    "target_radius": 0.3,    // 半径按比例缩小
    "wallmarker_threshold": 0.8
  }
}
```

### 场景B：大房间（8m×8m）

```json
{
  "transform_params": {
    "scale_factor": 120,     // 缩小显示
    "world_range": 8.0
  },
  "scene_config": {
    "room_size": [8.0, 8.0],
    "target_radius": 0.6,    // 半径可以稍大
    "wallmarker_threshold": 1.5
  }
}
```

### 场景C：高性能电脑

```python
# test_natnet_to_psychopy.py
time.sleep(1/60)  # 提升到60 FPS
```

### 场景D：低性能电脑

```python
# test_natnet_to_psychopy.py  
time.sleep(1/20)  # 降低到20 FPS

# lsl_recorder.py
self.auto_save_interval = 60.0  # 减少I/O频率
```

---

## 下一章

**→ [第5章 数据格式规范](技术文档-第5章-数据格式.md)**

学习所有数据文件的格式、字段含义和分析方法。

---

**本章节要点**：
- ⭐ `scale_factor`是最常调整的参数
- ⭐ 修改配置文件后需重启程序
- ⭐ 参数自动应用到所有模块

