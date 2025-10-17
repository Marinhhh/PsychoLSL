# 第1章 项目架构与模块详解

**版本**: V3.3.1  
**章节**: 1/6

---

## 1.1 系统简介

### 项目概述

**空间导航与神经同步实验系统**是一个基于OptiTrack动作捕捉和LSL数据流的实验平台，用于研究二人协作任务中的空间导航行为和神经同步现象。

### 核心技术栈

| 技术组件 | 版本 | 作用 |
|---------|------|------|
| **Python** | 3.8+ | 主编程语言 |
| **NatNet SDK** | 4.x | OptiTrack数据接收 |
| **pylsl** | 1.17.6 | LSL数据流处理 |
| **PsychoPy** | 2024.x | 实时可视化 |
| **PyQt5** | 5.x | GUI界面 |
| **pandas** | - | 数据分析（可选） |

### 系统能力

- ✅ **实时跟踪**：~120 Hz OptiTrack位置数据
- ✅ **实时显示**：30 FPS PsychoPy视觉反馈
- ✅ **数据广播**：3路LSL流（Marker + 2个位置流）
- ✅ **数据录制**：CSV + XDF格式
- ✅ **时间同步**：微秒级精度LSL时钟
- ✅ **鲁棒性**：4层数据保护，99.9%可靠性

---

## 1.2 目录结构与职责

### 完整目录树

```
Navigation/
├── run_experiment.py                 # 统一启动器
│
├── Scripts/                          # 所有程序代码
│   ├── Core/                         # 核心服务层（高内聚）
│   │   ├── lsl_manager.py           # LSL/NatNet混合管理器⭐
│   │   ├── transform_manager.py     # 坐标转换与场景管理
│   │   ├── audio_manager.py         # 音频播放管理
│   │   └── optitrack_data_saver.py  # OptiTrack数据保存
│   │
│   ├── Utils/                        # 工具层（低耦合）
│   │   ├── config_manager.py        # 配置文件加载
│   │   └── data_logger.py           # 数据记录（LSL时钟）
│   │
│   ├── Procedures/                   # 实验流程层（业务逻辑）
│   │   ├── map_phase.py             # Phase 0: 认知地图学习
│   │   └── navigation_phase.py      # Phase 1: 神经同步测量
│   │
│   └── Tools/                        # 独立工具
│       ├── test_natnet_to_psychopy.py      # NatNet→PsychoPy测试
│       ├── test_optitrack_lsl_streams.py   # OptiTrack→LSL流测试
│       ├── test_lsl_connection.py          # LSL连接诊断
│       ├── diagnose_natnet_data.py         # NatNet数据诊断
│       ├── lsl_recorder.py                 # LSL录制器（CLI/GUI）
│       └── generate_audios.py              # 音频生成工具
│
├── Config/                           # 配置与SDK
│   ├── experiment_config.json       # 实验总配置⭐
│   ├── LSL/pylsl-1.17.6/           # LSL SDK
│   └── NatNetSDK/                   # OptiTrack NatNet SDK
│
├── Assets/                           # 静态资源
│   └── Audios/                      # 音频文件
│       ├── WallMarker_go/          # 墙标指令
│       ├── WallMarker_arrive/      # 到达墙标
│       ├── Target_go/              # 目标指令
│       ├── Target_arrive/          # 找到目标
│       └── Common/                 # 通用提示
│
├── Data/                             # 数据存储⭐
│   ├── Behavior/D{dyad}/           # 行为数据
│   │   └── S{session}/
│   │       ├── Behavior.csv        # Trial级数据
│   │       ├── Position.csv        # 帧级位置
│   │       ├── Markers.csv         # TTL事件
│   │       └── scene_layout.json   # 场景布局
│   │
│   ├── OptiTrack/D{dyad}/          # OptiTrack原始数据
│   │   ├── Optitrack_Marker_*.csv
│   │   ├── Optitrack_Skeleton_*.csv
│   │   └── Optitrack_RigidBody_*.csv
│   │
│   └── LSL/{日期}/                  # LSL录制数据
│       ├── Sub001_Position_*.csv
│       └── Sub002_Position_*.csv
│
├── Logs/                             # 运行日志
│
└── docs/                             # 文档
    ├── 技术文档-主文档.md（本文档）
    ├── 技术文档-第1-6章.md
    ├── framework.md                 # 框架文档
    ├── research_design.md           # 研究设计
    └── Change/                      # 版本更新记录
```

---

## 1.3 模块分层设计

### 三层架构

```
┌─────────────────────────────────────────┐
│  Procedures/ (业务逻辑层)                │
│  - map_phase.py                          │
│  - navigation_phase.py                   │
│  职责：组合Core和Utils完成实验流程        │
└─────────────────────────────────────────┘
                  ↓ 调用
┌─────────────────────────────────────────┐
│  Core/ (核心服务层)                      │
│  - lsl_manager.py (数据采集)             │
│  - transform_manager.py (坐标转换)       │
│  - audio_manager.py (音频播放)           │
│  职责：提供核心功能服务                   │
└─────────────────────────────────────────┘
                  ↓ 使用
┌─────────────────────────────────────────┐
│  Utils/ (工具层)                         │
│  - config_manager.py                     │
│  - data_logger.py                        │
│  职责：提供无状态工具函数                 │
└─────────────────────────────────────────┘
```

### 设计原则

#### 高内聚

每个模块只负责一个核心功能：
- `lsl_manager.py` → 只管LSL/NatNet
- `transform_manager.py` → 只管坐标转换
- `audio_manager.py` → 只管音频

#### 低耦合

模块间通过清晰接口通信：
```python
# Procedures调用Core
self.lsl_manager = LSLManager()  # 获取实例
position = self.lsl_manager.get_latest_skeleton_data("Sub001")  # 调用接口

# Core使用Utils
self.data_logger = DataLogger(self.lsl_manager)  # 依赖注入
```

#### 单例模式

核心管理器使用单例，避免重复初始化：
```python
# LSLManager是单例
manager1 = LSLManager()  # 第1次创建
manager2 = LSLManager()  # 返回同一实例
assert manager1 is manager2  # True
```

---

## 1.4 核心模块详解

### 1.4.1 lsl_manager.py - LSL/NatNet混合管理器

**职责**：
- NatNet客户端（接收Motive数据）
- LSL Marker异步发送（TTL标记）
- LSL位置流广播（OptiTrack位置）
- 数据缓存和获取接口

**关键类**：
```python
class LSLManager:
    """LSL/NatNet混合管理器（单例）"""
    
    # 核心方法
    def start_services(enable_position_broadcast=True)  # 启动所有服务
    def send_marker(code, meaning)                      # 发送TTL标记
    def get_latest_skeleton_data(skeleton_name)         # 获取位置数据
    def cleanup()                                       # 清理资源
```

**数据流**：
```
Motive → NatNet → _on_new_frame() → 
    ├─ 缓存到latest_skeleton_data{}
    ├─ 推送到LSL位置流
    └─ 保存到OptiTrack CSV
```

**详细说明** → [第2章 NatNet系统](技术文档-第2章-NatNet系统.md)

---

### 1.4.2 transform_manager.py - 坐标转换管理器

**职责**：
- Motive世界坐标 ↔ PsychoPy屏幕坐标
- 场景标记生成（墙标A1-D5，目标P1-P3）
- 碰撞检测（点是否在区域内）

**关键方法**：
```python
class TransformManager:
    # 坐标转换
    def real_to_screen(x_real, z_real)     # Motive → PsychoPy
    def screen_to_real(x_screen, y_screen) # PsychoPy → Motive
    
    # 场景生成
    def generate_wall_markers()            # 生成墙标A1-D5
    def generate_hidden_targets()          # 生成隐藏目标P1-P3
    
    # 碰撞检测
    def check_point_near_marker(point, marker_id, threshold)
```

**坐标转换公式**：
```python
# Motive → PsychoPy
x_screen = 180.0 * x_real
y_screen = 180.0 * z_real * (-1)  # Z轴翻转

# PsychoPy → Motive
x_real = x_screen / 180.0
z_real = (y_screen * (-1)) / 180.0
```

---

### 1.4.3 audio_manager.py - 音频管理器

**职责**：
- 预加载音频文件
- 播放指令音频
- 管理音频资源

**关键方法**：
```python
class AudioManager:
    def load_all_audios()                 # 预加载
    def play_wallmarker_go(marker_id)     # "请前往A5"
    def play_wallmarker_arrive(marker_id) # "成功到达A5"
    def play_target_go(target_id)         # "探索寻找P2"
    def play_target_arrive(target_id)     # "找到了P2"
    def play_common(type)                 # 通用提示
```

---

### 1.4.4 data_logger.py - 数据记录器

**职责**：
- 创建数据文件（Behavior/Position/Markers CSV）
- 使用LSL统一时钟
- 缓冲和批量写入

**关键方法**：
```python
class DataLogger:
    def __init__(lsl_manager)             # 强制传入LSL管理器
    def create_session(dyad_id, session_id)
    def log_behavior(behavior_data)       # 记录trial数据
    def log_position(position_data)       # 记录位置（缓冲）
    def log_marker(code, meaning)         # 记录marker（同时发送LSL）
```

**时间戳**：
```python
from pylsl import local_clock
timestamp = local_clock()  # LSL统一时钟
```

---

### 1.4.5 实验流程模块

#### map_phase.py - 认知地图学习

**阶段**：Phase 0  
**参与者**：单人  
**任务**：学习墙标和隐藏目标位置

**流程**：
```
初始化 → 20个Trial → 每个Trial:
    ├─ 导航到墙标
    ├─ 搜索隐藏目标
    └─ 记录数据
```

#### navigation_phase.py - 神经同步测量

**阶段**：Phase 1  
**参与者**：双人（导航者+观察者）  
**任务**：一人导航，一人观察并判断

**流程**：
```
初始化 → Block → 20个Trial → 每个Trial:
    ├─ 导航者移动
    ├─ 观察者按键判断
    └─ 记录双人数据
```

---

## 1.5 数据流架构

### 完整数据流图

```
┌──────────────────────────────────────────────┐
│         Motive OptiTrack                      │
│  Sub001 Markerset + Sub002 Markerset         │
└──────────────────────────────────────────────┘
                    ↓
            【NatNet协议，~120Hz】
                    ↓
┌──────────────────────────────────────────────┐
│  LSLManager (lsl_manager.py)                  │
│  - 接收NatNet数据                              │
│  - 计算Markerset质心                           │
│  - 缓存latest_skeleton_data{}                 │
└──────────────────────────────────────────────┘
    ↓           ↓              ↓            ↓
┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│PsychoPy│ │LSL Marker│ │LSL位置流 │ │数据保存  │
│显示    │ │TTL标记  │ │位置广播  │ │CSV文件   │
│30 FPS  │ │事件驱动 │ │~120Hz    │ │持续写入  │
└────────┘ └─────────┘ └──────────┘ └──────────┘
    ↓          ↓             ↓            ↓
  光点跟踪  LSL录制器   LSL录制器   Behavior/
                                    OptiTrack/
```

### 数据路径详解

#### 路径1：实时显示（PsychoPy）

```python
# map_phase.py/navigation_phase.py
while True:
    # 获取位置
    data = lsl_manager.get_latest_skeleton_data("Sub001")
    
    # 转换坐标
    x_screen, y_screen = transform_manager.real_to_screen(data['x'], data['z'])
    
    # 更新光点
    self.participant_dot.pos = (x_screen, y_screen)
    
    # 绘制
    self.win.flip()
```

**延迟**：<50ms

#### 路径2：LSL流广播

```python
# lsl_manager.py → _on_new_frame()
# 接收NatNet数据
centroid_position = (x, y, z)

# 推送到LSL位置流
position_sample = [float(x), float(y), float(z)]
self.position_outlets['Sub001'].push_sample(position_sample)
```

**帧率**：~120 Hz

#### 路径3：数据保存

```python
# data_logger.py
# Behavior数据
log_behavior(trial_data)  → Behavior.csv

# 位置数据（缓冲100条）
log_position(pos_data)  → Position.csv（批量写入）

# Marker数据（立即写入）
log_marker(code, meaning)  → Markers.csv（同时发送LSL）
```

---

## 1.6 依赖关系图

### 模块依赖

```
Procedures/map_phase.py
    ├─→ Core/lsl_manager.py
    ├─→ Core/transform_manager.py
    ├─→ Core/audio_manager.py
    └─→ Utils/data_logger.py
            └─→ Core/lsl_manager.py (依赖注入)

Core/lsl_manager.py
    ├─→ NatNetSDK (外部)
    ├─→ pylsl (外部)
    └─→ Core/optitrack_data_saver.py

Tools/lsl_recorder.py
    └─→ pylsl (外部，独立运行)
```

### 导入示例

```python
# Procedures中的标准导入
from Core.lsl_manager import LSLManager
from Core.transform_manager import TransformManager
from Core.audio_manager import AudioManager
from Utils.data_logger import DataLogger
from Utils.config_manager import load_config

from psychopy import visual, core, event
```

---

## 1.7 快速开始

### 最小启动流程

#### 步骤1：检查Motive配置

- ✅ Sub001和Sub002是**Markerset类型**
- ✅ 流设置中启用"Marker Set"
- ✅ Motive处于录制状态（红色按钮）

#### 步骤2：启动系统

```bash
# 方式1：使用统一启动器
python run_experiment.py

# 方式2：直接运行阶段
python Scripts\Procedures\map_phase.py
```

#### 步骤3：（可选）启动LSL录制器

```bash
python Scripts\Tools\lsl_recorder.py --gui
```

---

## 1.8 配置文件概览

### experiment_config.json结构

```json
{
  "version": "3.0",
  
  "transform_params": {          // 坐标转换参数
    "scale_factor": 180.0,       // ⭐ 缩放因子
    "world_range": 6.0,          // 房间大小
    "screen_range": 1080         // 屏幕大小
  },
  
  "scene_config": {              // 场景配置
    "num_hidden_targets": 3,
    "target_radius": 0.4,
    "wallmarker_threshold": 1.0
  },
  
  "experiment_flow": {           // 实验流程
    "phase_0": {...},            // 认知地图学习
    "phase_1": {...}             // 神经同步测量
  },
  
  "ttl_markers": {               // TTL标记定义
    "1": "Trial开始",
    "2": "到达墙面标记",
    "3": "观察者按键",
    "4": "找到隐藏目标",
    "5": "Block结束"
  },
  
  "audio_config": {              // 音频配置
    "interval_after_target_found": 2.0  // ⭐ 音频间隔
  },
  
  "natnet_config": {             // NatNet配置
    "server_ip": "192.168.3.58",  // ⭐ Motive IP
    "client_ip": "192.168.3.55"   // ⭐ 本机IP
  },
  
  "lsl_config": {...},           // LSL配置
  "data_config": {...},          // 数据配置
  "visual_config": {...},        // 可视化配置
  "robustness_config": {...}     // 鲁棒性配置
}
```

**详细说明** → [第4章 配置参数手册](技术文档-第4章-配置参数.md)

---

## 1.9 数据文件一览

### 单次实验（15分钟）生成的文件

| 文件类型 | 位置 | 行数 | 大小 | 用途 |
|---------|------|------|------|------|
| **Behavior.csv** | Behavior/D001/ | ~20 | ~5KB | Trial级分析 |
| **Position.csv** | Behavior/D001/ | ~108K | ~5MB | 轨迹分析 |
| **Markers.csv** | Behavior/D001/ | ~100 | ~10KB | 事件分析 |
| **Optitrack_*.csv** | OptiTrack/D001/ | ~108K | ~10MB | 原始数据 |
| **Sub001_Position.csv** | LSL/日期/ | ~108K | ~5MB | LSL同步 |
| **Sub002_Position.csv** | LSL/日期/ | ~108K | ~5MB | LSL同步 |

**总量**：约30-35 MB / 实验

---

## 1.10 性能指标

### 实时性能

| 指标 | 目标 | 实测 | 状态 |
|------|------|------|------|
| NatNet帧率 | 120 Hz | 111-120 Hz | ✅ |
| PsychoPy帧率 | 30 FPS | 29-30 FPS | ✅ |
| 位置延迟 | <100ms | <50ms | ✅ |
| LSL广播延迟 | <10ms | <5ms | ✅ |

### 资源占用

| 资源 | 占用 | 状态 |
|------|------|------|
| CPU | 30-40% | ✅ 低 |
| 内存 | <200MB | ✅ 低 |
| 磁盘I/O | 1次/30秒 | ✅ 极低 |
| 网络 | ~15KB/s | ✅ 极低 |

---

## 1.11 技术亮点

### 1. 多路数据流设计

**同一份NatNet数据，4种用途**：
1. PsychoPy实时显示（视觉反馈）
2. LSL位置流广播（设备同步）
3. LSL Marker流（事件标记）
4. CSV文件保存（数据分析）

### 2. 统一时钟系统

**所有数据使用LSL时钟**：
- 支持多模态融合（OptiTrack + fNIRS + EEG）
- 微秒级同步精度
- 自动时间漂移补偿

### 3. 数据可靠性保障

**4层保护机制**：
1. 定期自动保存（每30秒）
2. 正常停止保存
3. 信号处理器（Ctrl+C）
4. 紧急保存（atexit）

**可靠性**：99.9%

### 4. 鲁棒性设计

- Degraded Mode（LSL不可用时仍可运行）
- 位置丢失处理（光点保持静止）
- 异常恢复和自动重连
- 详细日志和诊断工具

---

## 下一章

**→ [第2章 NatNet数据采集系统](技术文档-第2章-NatNet系统.md)**

学习如何接收和处理Motive OptiTrack数据，理解Markerset/Skeleton/RigidBody的区别，掌握NatNet故障排查。

---

**本章节完成** ✅  
**继续阅读** → 第2章

