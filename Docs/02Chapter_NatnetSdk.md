# 第2章 NatNet数据采集系统（独立技术章节）

**版本**: V3.3.1  
**章节**: 2/6  
**重要性**: ⭐⭐⭐⭐⭐

> 本章节详细讲解NatNet数据采集的技术原理，独立于实验任务，适合技术人员深入学习。

---

## 2.1 NatNet协议概述

### 什么是NatNet？

**NatNet**是OptiTrack公司开发的网络协议，用于实时传输动作捕捉数据。

**核心特性**：
- 低延迟：<10ms网络传输
- 高帧率：支持最高360 Hz
- 多播支持：多个客户端同时接收
- 跨平台：Windows/Linux/Mac

### 数据传输模型

```
Motive软件（服务器）
    ↓ UDP广播
NatNet网络协议
    ↓ 解包
Python客户端（NatNetClient）
    ↓ 回调
用户程序（lsl_manager.py）
```

### 本项目使用的NatNet SDK

**路径**：`Config/NatNetSDK/Samples/PythonClient/`

**核心文件**：
- `NatNetClient.py` - 客户端主类
- `MoCapData.py` - 数据结构定义
- `DataDescriptions.py` - 描述信息

---

## 2.2 NatNet数据类型详解

### Motive中的三种对象类型

| 类型 | Motive图标 | 适用场景 | 数据更新条件 |
|------|-----------|---------|-------------|
| **Markerset** | 📦 | 物体位置跟踪 | 任意标记可见 ✅ |
| **Skeleton** | 🦴 | 真人骨骼跟踪 | 标记符合骨骼结构 ⚠️ |
| **RigidBody** | 🔲 | 刚体6DOF跟踪 | 刚体被识别 ✅ |

#### Markerset（推荐用于本项目）

**用途**：跟踪一组标记点的质心位置

**数据结构**：
```python
MarkerSetData:
    marker_data_list[] (MarkerData):
        - model_name: str (如"Sub001")
        - marker_pos_list: [[x,y,z], [x,y,z], ...]
```

**质心计算**：
```python
# lsl_manager.py中的实现
centroid_x = sum(pos[0] for pos in marker_pos_list) / len(marker_pos_list)
centroid_y = sum(pos[1] for pos in marker_pos_list) / len(marker_pos_list)
centroid_z = sum(pos[2] for pos in marker_pos_list) / len(marker_pos_list)
```

**优势**：
- ✅ 简单可靠
- ✅ 标记排列无要求
- ✅ 实时更新

**本项目使用场景**：
- Sub001 Markerset：参与者A的头戴设备
- Sub002 Markerset：参与者B的头戴设备

#### Skeleton（不推荐用于物体）

**用途**：真人全身/手部骨骼跟踪

**数据结构**：
```python
SkeletonData:
    skeleton_list[] (Skeleton):
        - id_num: int
        - name: str (如"Sub001")
        - rigid_body_list[] (关节):
            - id_num: int (关节ID)
            - name: str (如"Pelvis", "LeftHand")
            - pos: [x, y, z]
            - rot: [qx, qy, qz, qw]
            - tracking_valid: bool
```

**关键问题**：
```
Skeleton要求标记符合骨骼结构！

例如LeftHand模板要求：
- Wrist（手腕）: 1个关节
- 5个手指: 每个3个关节
- 共16个标记点，特定排列

如果标记点贴在物体上 → 无法匹配 → 数据冻结！
```

**实际案例**（本项目遇到的bug）：
```
Sub001使用Skeleton（LeftHand） + 标记贴在物体上
    ↓
Motive无法匹配骨骼结构
    ↓
数据冻结在初始值：(+0.932, +0.861, -0.001)
    ↓
PsychoPy光点静止不动 ❌
```

**解决方案**：改用Markerset类型 ✅

#### RigidBody

**用途**：刚体6自由度跟踪（位置+旋转）

**数据结构**：
```python
RigidBodyData:
    rigid_body_list[] (RigidBody):
        - id_num: int
        - pos: [x, y, z]
        - rot: [qx, qy, qz, qw]  # 四元数
        - error: float (重建误差)
        - tracking_valid: bool
```

**本项目中**：
- 主要使用Markerset获取位置
- RigidBody数据保存到OptiTrack CSV
- 可作为Markerset的备选数据源

---

## 2.3 NatNet回调机制⭐

### 两种回调函数

NatNet SDK提供两种回调：

| 回调函数 | 数据内容 | 用途 | 本项目使用 |
|---------|---------|------|-----------|
| `new_frame_listener` | 简单dict（只有统计） | 获取帧号、对象数量 | ❌ 错误 |
| **`new_frame_with_data_listener`** | 完整dict（含MoCapData对象） | 获取实际位置数据 | ✅ 正确 |

### 关键Bug修复（V3.1）

**问题**：
```python
# 错误用法（V3.0）
self.natnet_client.new_frame_listener = self._on_new_frame

# _on_new_frame收到的data_dict：
data_dict = {
    'frame_number': 12345,
    'marker_set_count': 2,
    # ... 只有统计信息，没有位置数据！
}

# 无法访问：
data_dict.marker_set_data  # ❌ 属性不存在
```

**修复**：
```python
# 正确用法（V3.1+）
self.natnet_client.new_frame_with_data_listener = self._on_new_frame

# _on_new_frame收到的data_dict：
data_dict = {
    'frame_number': 12345,
    'marker_set_count': 2,
    'mocap_data': <MoCapData对象>,  # ✅ 包含完整数据！
    ...
}

# 提取MoCapData对象
mocap_data = data_dict['mocap_data']
marker_set_data = mocap_data.marker_set_data  # ✅ 成功
```

### 回调函数实现（lsl_manager.py）

```python
def _on_new_frame(self, data_dict):
    """NatNet新帧回调"""
    # 1. 提取MoCapData对象
    if "mocap_data" not in data_dict:
        return
    
    mocap_data = data_dict["mocap_data"]
    
    # 2. 处理Markerset数据
    if hasattr(mocap_data, 'marker_set_data') and mocap_data.marker_set_data:
        marker_set_list = mocap_data.marker_set_data.marker_data_list
        
        for marker_set in marker_set_list:
            # 获取名称
            model_name = marker_set.model_name  # "Sub001"
            
            # 获取标记位置
            marker_positions = marker_set.marker_pos_list  # [[x,y,z], ...]
            
            # 计算质心
            centroid = calculate_centroid(marker_positions)
            
            # 缓存数据
            self.latest_skeleton_data[model_name] = {
                'pelvis_position': centroid,
                'timestamp': time.time(),
                'valid': True
            }
            
            # 推送到LSL位置流
            if model_name in self.position_outlets:
                self.position_outlets[model_name].push_sample([
                    float(centroid[0]),
                    float(centroid[1]),
                    float(centroid[2])
                ])
```

---

## 2.4 NatNet连接配置

### IP配置（关键！）

**文件**：`Config/experiment_config.json`

```json
"natnet_config": {
  "server_ip": "192.168.3.58",  // Motive所在电脑的IP
  "client_ip": "192.168.3.55",  // Python程序所在电脑的IP
  "use_multicast": true          // 是否使用组播
}
```

**或在代码中**（`lsl_manager.py` 第77-79行）：

```python
self.server_ip = "192.168.3.58"  # Motive IP
self.client_ip = "192.168.3.55"  # 本机IP
self.use_multicast = True
```

### 网络模式

#### 单播模式（use_multicast=false）

```
Motive (192.168.3.58)
    ↓ 单播UDP
Python (192.168.3.55)
```

**适用**：
- Motive和Python在同一电脑
- 网络不支持组播
- 点对点通信

#### 组播模式（use_multicast=true，推荐）

```
Motive (192.168.3.58)
    ↓ 组播UDP (239.255.42.99)
    ├─→ Python客户端1
    ├─→ Python客户端2
    └─→ ...
```

**适用**：
- 多个客户端同时接收
- 不同电脑上的程序
- 标准网络环境

### 连接初始化

```python
# lsl_manager.py
client = NatNetClient()
client.set_client_address("192.168.3.55")    # 本机IP
client.set_server_address("192.168.3.58")   # Motive IP
client.set_use_multicast(True)
client.set_print_level(0)                    # 关闭verbose输出

# 设置回调
client.new_frame_with_data_listener = self._on_new_frame

# 启动（'d'=数据流模式）
client.run('d')
```

---

## 2.5 Motive配置要求

### 流设置（关键！）

**路径**：Motive > 编辑 > 设置 > 流设置（Streaming）

**必须启用**：
- ✅ **Broadcast Frame Data** - 启用帧数据广播
- ✅ **Marker Set** - 启用Markerset数据（如果使用Markerset）
- ✅ **Labeled Markers** - 启用标记点标签
- ✅ **Rigid Body** - 启用刚体数据（如果使用RigidBody）
- ⚠️ **Skeleton** - 只在真人骨骼跟踪时启用

**本地接口**：
- ✅ 启用
- 传输类型：组播（Multicast）
- 命令端口：1510（默认）
- 数据端口：1511（默认）

### Markerset创建步骤

#### 方法1：从选中的标记创建

```
步骤1: 在Motive 3D视图中，选择要组成一个Markerset的标记点
步骤2: 右键 → "Rigid Body" → "Create From Selected Markers"
步骤3: 在Assets面板中，右键新创建的对象 → "Rename"
步骤4: 命名为"Sub001"
```

#### 方法2：手动创建

```
步骤1: Assets面板 → 点击"+"按钮
步骤2: 选择"Marker Set"
步骤3: 将标记点拖拽到Markerset中
步骤4: 重命名为"Sub001"
```

### 验证配置

**检查清单**：
```
Assets面板中：
├─ Sub001 📦 (Markerset)
│   └─ 包含4-7个标记点
│   └─ 状态：绿色（正在跟踪）✅
│
└─ Sub002 📦 (Markerset)
    └─ 包含4-7个标记点
    └─ 状态：绿色（正在跟踪）✅

底部状态栏：
└─ 录制按钮：红色（Recording）✅
```

---

## 2.6 数据接收实现

### lsl_manager.py中的实现

#### 初始化NatNet客户端

```python
def initialize_natnet_client(self, server_ip, client_ip, use_multicast):
    # 创建客户端
    self.natnet_client = NatNetClient()
    self.natnet_client.set_client_address(client_ip)
    self.natnet_client.set_server_address(server_ip)
    self.natnet_client.set_use_multicast(use_multicast)
    
    # 关闭verbose输出
    self.natnet_client.set_print_level(0)
    
    # 设置回调（重要！）
    self.natnet_client.new_frame_with_data_listener = self._on_new_frame
    
    # 启动客户端
    self.natnet_client.run('d')  # 'd' = 数据流模式
    
    # 等待连接
    time.sleep(2)
    
    # 验证连接
    if self.natnet_client.connected():
        return True
    else:
        return False
```

#### 帧回调处理

```python
def _on_new_frame(self, data_dict):
    """每帧调用一次（~120 Hz）"""
    # 提取MoCapData对象
    mocap_data = data_dict["mocap_data"]
    
    # 处理Markerset数据
    if hasattr(mocap_data, 'marker_set_data'):
        marker_set_list = mocap_data.marker_set_data.marker_data_list
        
        for marker_set in marker_set_list:
            model_name = marker_set.model_name
            
            # 跳过"all"总集合
            if model_name.lower() == 'all':
                continue
            
            # 计算质心
            positions = marker_set.marker_pos_list
            if positions:
                centroid = self._calculate_centroid(positions)
                
                # 存储（支持多种命名格式）
                storage_names = [model_name]  # Sub001
                if model_name.startswith('Sub'):
                    sub_id = int(model_name[3:])
                    storage_names.append(f"Skeleton_{sub_id}")  # Skeleton_1
                
                for name in storage_names:
                    self.latest_skeleton_data[name] = {
                        'pelvis_position': centroid,
                        'timestamp': time.time(),
                        'valid': True
                    }
                
                # 推送到LSL流
                if model_name in self.position_outlets:
                    self.position_outlets[model_name].push_sample([
                        float(centroid[0]),
                        float(centroid[1]),
                        float(centroid[2])
                    ])
```

---

## 2.7 数据获取接口

### get_latest_skeleton_data()

**功能**：提取指定对象的最新3D位置

**签名**：
```python
def get_latest_skeleton_data(self, skeleton_name: str) -> dict | None
```

**参数**：
- `skeleton_name`: 对象名称，支持多种格式
  - "Sub001" - Motive中的实际名称
  - "Skeleton_1" - 内部映射格式
  - "Skeleton_001" - 兼容格式

**返回值**：
```python
{
    'x': float,        # X坐标（米）
    'y': float,        # Y坐标（米，高度）
    'z': float,        # Z坐标（米）
    'timestamp': float,  # Unix时间戳
    'valid': bool      # 数据是否有效
}
```

**使用示例**：
```python
# 在实验程序中
data = self.lsl_manager.get_latest_skeleton_data("Sub001")

if data and data['valid']:
    x_real = data['x']  # Motive X坐标
    y_real = data['y']  # Motive Y坐标（高度）
    z_real = data['z']  # Motive Z坐标
    
    # 转换到PsychoPy坐标
    x_screen, y_screen = self.transform_manager.real_to_screen(x_real, z_real)
else:
    # 无数据或数据丢失
    # 光点保持静止在最后有效位置
```

### 名称映射机制

**自动映射**：
```python
# 用户调用
get_latest_skeleton_data("Sub001")

# 内部尝试
possible_names = [
    "Sub001",       # 原始名称
    "Skeleton_1",   # 映射格式（从"001"转换为1）
    "Skeleton_001"  # 兼容格式
]

# 依次查找缓存
for name in possible_names:
    if name in self.latest_skeleton_data:
        return self.latest_skeleton_data[name]  # 找到即返回
```

**优势**：
- ✅ 用户不需要知道内部存储格式
- ✅ 兼容多种命名习惯
- ✅ 代码更健壮

---

## 2.8 NatNet故障排查

### 问题1：无法连接到OptiTrack服务器

**症状**：
```
❌ 无法连接到OptiTrack服务器
```

**诊断步骤**：

#### 步骤1：检查Motive是否运行

```
Windows任务管理器 → 进程 → 查找"Motive"
```

如果没有运行 → 启动Motive

#### 步骤2：检查网络连接

```cmd
# 在命令行测试ping
ping 192.168.3.58

# 应该看到：
Reply from 192.168.3.58: bytes=32 time<1ms TTL=128
```

如果超时 → 检查网络连接或IP配置

#### 步骤3：检查IP配置

**Motive中**：
```
编辑 > 设置 > 流设置 > 本地接口
查看"本地接口IP"
```

**Python中**（`lsl_manager.py` 第77行）：
```python
self.server_ip = "192.168.3.58"  # 应该匹配Motive的IP
```

#### 步骤4：检查防火墙

```
Windows防火墙 > 允许应用通过防火墙
确保Motive和Python都允许
```

### 问题2：连接成功但无数据

**症状**：
```
✅ NatNet客户端连接成功
[NatNet] 帧数: 0, FPS: 0.0, 缓存骨骼: []
```

**诊断步骤**：

#### 步骤1：检查Motive录制状态

```
Motive底部 → 录制按钮应该是红色
```

如果是灰色 → 点击开始录制

#### 步骤2：检查流设置

```
编辑 > 设置 > 流设置
✅ Broadcast Frame Data: 启用
✅ Marker Set: 勾选（如果使用Markerset）
```

#### 步骤3：运行诊断工具

```bash
python Scripts\Tools\diagnose_natnet_data.py
```

查看输出的数据类型和对象名称。

### 问题3：光点位置不更新

**症状**：
```
[NatNet] Markerset数据: Sub001 -> 质心: (+0.932, +0.861, -0.001)
坐标一直不变，光点静止
```

**可能原因**：

#### 原因A：对象是Skeleton类型（最常见）

**检查**：
```
Motive Assets面板 → Sub001的图标是🦴还是📦？
```

**解决**：
```
如果是🦴（Skeleton）→ 删除 → 重新创建为📦（Markerset）
```

#### 原因B：标记未被跟踪

**检查**：
```
Motive 3D视图 → 标记点是绿色还是红色？
```

**解决**：
```
如果是红色 → 调整相机角度，确保标记可见
```

#### 原因C：数据缓存过时

**解决**：
```bash
# 重启Python程序
python run_experiment.py
```

### 问题4：帧率过低

**症状**：
```
[NatNet] 帧数: 1000, FPS: 30.5
```

**正常帧率**：100-120 FPS

**可能原因**：
- Motive相机帧率设置过低
- 网络带宽不足
- CPU负载过高

**解决**：
```
Motive > 相机设置 > 帧率 > 设置为120 FPS
关闭不必要的后台程序
```

---

## 2.9 NatNet数据结构参考

### MoCapFrame对象结构

```
MoCapData (根对象)
├── prefix_data
│   └── frame_number (帧号)
│
├── marker_set_data (MarkerSetData)
│   └── marker_data_list[] (MarkerData)
│       ├── model_name: "Sub001"
│       └── marker_pos_list: [[x,y,z], ...]
│
├── skeleton_data (SkeletonData)
│   └── skeleton_list[] (Skeleton)
│       ├── id_num
│       ├── name
│       └── rigid_body_list[] (关节)
│
├── rigid_body_data (RigidBodyData)
│   └── rigid_body_list[] (RigidBody)
│       ├── id_num
│       ├── pos: [x,y,z]
│       └── rot: [qx,qy,qz,qw]
│
├── labeled_marker_data (LabeledMarkerData)
└── suffix_data (时间戳等)
```

### 字段名速查

| 对象类型 | 常见错误 | 正确字段 |
|---------|---------|---------|
| Marker | `.id` | `.id_num` ✅ |
| Marker | `.name` | `.model_name` ✅ |
| Skeleton | `.id` | `.id_num` ✅ |
| Skeleton | `.joints` | `.rigid_body_list` ✅ |
| Joint | `.valid` | `.tracking_valid` ✅ |
| RigidBody | `.mean_error` | `.error` ✅ |

---

## 2.10 实战示例

### 示例1：最小NatNet接收程序

```python
import sys
from pathlib import Path

# 添加SDK路径
sdk_path = Path('Config/NatNetSDK/Samples/PythonClient')
sys.path.insert(0, str(sdk_path))

from NatNetClient import NatNetClient

def on_frame(data_dict):
    """帧回调"""
    mocap_data = data_dict["mocap_data"]
    
    if hasattr(mocap_data, 'marker_set_data'):
        marker_sets = mocap_data.marker_set_data.marker_data_list
        
        for ms in marker_sets:
            print(f"{ms.model_name}: {len(ms.marker_pos_list)}个标记")

# 创建客户端
client = NatNetClient()
client.set_server_address("192.168.3.58")
client.set_client_address("192.168.3.55")
client.new_frame_with_data_listener = on_frame
client.run('d')

# 运行
import time
time.sleep(10)
client.shutdown()
```

### 示例2：获取实时位置

```python
from Scripts.Core.lsl_manager import LSLManager

# 启动管理器
manager = LSLManager()
manager.start_services()

# 等待数据
import time
time.sleep(3)

# 获取位置
data = manager.get_latest_skeleton_data("Sub001")

if data:
    print(f"Sub001位置: X={data['x']:.3f}m, Y={data['y']:.3f}m, Z={data['z']:.3f}m")
else:
    print("无数据")

# 清理
manager.cleanup()
```

---

## 下一章

**→ [第3章 LSL数据流系统](技术文档-第3章-LSL系统.md)**

学习LSL的核心概念、流创建、数据广播和录制技术。

---

**本章节关键点**：
- ✅ 使用`new_frame_with_data_listener`回调
- ✅ Sub001/Sub002使用**Markerset类型**（不是Skeleton）
- ✅ Motive流设置启用"Marker Set"
- ✅ 正确配置IP地址

