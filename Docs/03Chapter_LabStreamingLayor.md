# 第3章 LSL数据流系统（独立技术章节）

**版本**: V3.3.1  
**章节**: 3/6  
**重要性**: ⭐⭐⭐⭐⭐

> 本章节详细讲解LSL（Lab Streaming Layer）的技术原理和使用方法，独立于具体实验任务。

---

## 3.1 LSL核心概念

### 什么是LSL？

**Lab Streaming Layer (LSL)** 是一个开源的实时数据流框架，专为实验室多模态数据同步设计。

**官方网站**：https://labstreaminglayer.org/

**核心特性**：
- ⏱️ **统一时钟**：自动时间同步，微秒级精度
- 🌐 **网络透明**：自动发现，跨设备通信
- 🔌 **即插即用**：设备自动注册到LSL网络
- 📊 **多模态支持**：EEG/fNIRS/眼动/动捕等

### LSL vs 其他协议

| 协议 | 延迟 | 时间同步 | 自动发现 | 多模态 |
|------|------|---------|---------|--------|
| **LSL** | <10ms | ✅ 自动 | ✅ 是 | ✅ 是 |
| NatNet | <10ms | ❌ 无 | ❌ 手动 | ❌ 限OptiTrack |
| TCP/IP | >50ms | ❌ 无 | ❌ 手动 | ⚠️ 复杂 |
| 串口 | >100ms | ❌ 无 | ❌ 手动 | ❌ 单设备 |

**结论**：LSL是实验室多设备同步的最佳选择！

---

## 3.2 LSL三大核心概念

### 概念1：Stream（流）

**流**是LSL中的基本数据单元，类似"数据频道"。

**流的属性**：
- **名称**（name）：流的唯一标识，如"Sub001_Position"
- **类型**（type）：数据类型，如"MoCap"、"EEG"、"Markers"
- **通道数**（channel_count）：每个样本的维度，如3（X,Y,Z）
- **采样率**（nominal_srate）：样本频率，如120 Hz或0（不规则）
- **数据格式**（channel_format）：float32、int32等
- **Source ID**：设备唯一标识

**本项目的LSL流**：

| 流名称 | 类型 | 通道 | 采样率 | 格式 |
|--------|------|------|-------|------|
| Navigation_Markers | Markers | 1 | 0 | int32 |
| Sub001_Position | MoCap | 3 | 0 | float32 |
| Sub002_Position | MoCap | 3 | 0 | float32 |

### 概念2：Outlet（输出）

**Outlet**用于**发送数据**到LSL网络。

**创建Outlet**：
```python
from pylsl import StreamInfo, StreamOutlet

# 1. 创建StreamInfo（描述流）
info = StreamInfo(
    name='Sub001_Position',      # 流名称
    type='MoCap',                # 流类型
    channel_count=3,             # 通道数（X,Y,Z）
    nominal_srate=0,             # 采样率（0=不规则）
    channel_format='float32',    # 数据格式
    source_id='optitrack_sub001' # 唯一ID
)

# 2. 添加元数据（可选但推荐）
channels = info.desc().append_child("channels")
for axis in ['X', 'Y', 'Z']:
    ch = channels.append_child("channel")
    ch.append_child_value("label", f"Position_{axis}")
    ch.append_child_value("unit", "meters")
    ch.append_child_value("type", "Position")

# 3. 创建Outlet
outlet = StreamOutlet(info)

# 4. 发送数据
while True:
    sample = [x, y, z]  # 3个float值
    outlet.push_sample(sample)  # LSL自动添加时间戳
    time.sleep(1/120)  # 120 Hz
```

**本项目实现**（lsl_manager.py）：
```python
def initialize_position_outlets(self, sub_ids=['001', '002']):
    """创建OptiTrack位置LSL流"""
    for sub_id in sub_ids:
        stream_name = f"Sub{sub_id}_Position"
        
        # 创建StreamInfo
        position_info = StreamInfo(
            name=stream_name,
            type='MoCap',
            channel_count=3,
            nominal_srate=0,
            channel_format='float32',
            source_id=f'optitrack_sub{sub_id}'
        )
        
        # 添加通道元数据
        channels = position_info.desc().append_child("channels")
        for axis in ['X', 'Y', 'Z']:
            ch = channels.append_child("channel")
            ch.append_child_value("label", f"Position_{axis}")
            ch.append_child_value("unit", "meters")
            ch.append_child_value("type", "Position")
        
        # 创建Outlet
        outlet = StreamOutlet(position_info)
        self.position_outlets[f"Sub{sub_id}"] = outlet
```

### 概念3：Inlet（输入）

**Inlet**用于**接收数据**从LSL网络。

**使用Inlet**：
```python
from pylsl import resolve_streams, StreamInlet

# 1. 发现流
streams = resolve_streams(wait_time=5.0)  # 扫描5秒

# 2. 选择要接收的流
for stream in streams:
    if stream.name() == 'Sub001_Position':
        # 3. 创建Inlet
        inlet = StreamInlet(stream)
        
        # 4. 接收数据
        while True:
            sample, timestamp = inlet.pull_sample()
            x, y, z = sample[0], sample[1], sample[2]
            print(f"位置: ({x:.3f}, {y:.3f}, {z:.3f}) @ {timestamp:.3f}秒")
```

**本项目实现**（lsl_recorder.py）：
```python
def _record_worker(self):
    """录制线程"""
    # 创建Inlet
    self.inlets = []
    for stream in self.selected_streams:
        inlet = StreamInlet(stream)
        self.inlets.append(inlet)
    
    # 接收循环
    while self.is_recording:
        for inlet in self.inlets:
            sample, timestamp = inlet.pull_sample(timeout=0.001)
            if sample:
                # 缓存数据
                self.data_buffers[stream_name].append({
                    'timestamp': timestamp,
                    'sample': sample
                })
```

---

## 3.3 本项目的LSL流详解

### 流1：Navigation_Markers

**用途**：TTL事件标记（Trial开始、到达墙标等）

**规格**：
```python
StreamInfo(
    name='Navigation_Markers',
    type='Markers',
    channel_count=1,         # 1个通道（TTL码）
    nominal_srate=0,         # 不规则采样
    channel_format='int32',  # 整数
    source_id='navigation_ttl_markers'
)
```

**通道定义**：
```
Ch_1 = TTL标记码（整数1-5）
```

**数据样本**：
```
t=100.0秒: [1]  # Trial开始
t=130.5秒: [2]  # 到达墙标
t=165.8秒: [4]  # 找到目标
```

**发送时机**（data_logger.py）：
```python
def log_marker(self, marker_code, meaning):
    # 1. 记录到Markers.csv
    self.markers_writer.writerow([timestamp, marker_code, meaning, ...])
    
    # 2. 同时发送到LSL流
    self.lsl_manager.send_marker(marker_code, meaning)
```

**异步发送机制**（lsl_manager.py）：
```python
# 主线程：放入队列（不阻塞）
def send_marker(self, code, meaning):
    self.marker_queue.put(code)

# 独立线程：异步发送
def _marker_send_loop(self):
    while self.marker_running:
        code = self.marker_queue.get()
        self.marker_outlet.push_sample([code])
```

---

### 流2-3：Sub001/Sub002_Position

**用途**：OptiTrack位置数据广播（供外部LSL设备接收）

**规格**：
```python
StreamInfo(
    name='Sub001_Position',      # Sub002_Position
    type='MoCap',                # 动作捕捉类型
    channel_count=3,             # 3个通道（X,Y,Z）
    nominal_srate=0,             # 不规则（实际~120Hz）
    channel_format='float32',    # 浮点数
    source_id='optitrack_sub001' # 'optitrack_sub002'
)
```

**通道定义**：
```
Ch_1 = Position_X (米, Motive世界坐标)
Ch_2 = Position_Y (米, Motive Up-axis高度)
Ch_3 = Position_Z (米, Motive世界坐标)
```

**元数据**：
```xml
<channels>
  <channel>
    <label>Position_X</label>
    <unit>meters</unit>
    <type>Position</type>
    <coordinate_system>Motive_World</coordinate_system>
  </channel>
  ...
</channels>

<acquisition>
  <manufacturer>OptiTrack</manufacturer>
  <system>Motive</system>
  <protocol>NatNet</protocol>
  <subject_id>Sub001</subject_id>
</acquisition>
```

**数据样本**：
```
t=100.000秒: [0.932, 0.861, -0.001]  # X=0.932m, Y=0.861m, Z=-0.001m
t=100.008秒: [0.935, 0.862, -0.005]
t=100.017秒: [0.940, 0.863, -0.010]
```

**推送时机**（lsl_manager.py）：
```python
def _on_new_frame(self, data_dict):
    # 计算Markerset质心
    centroid_position = (x, y, z)
    
    # 立即推送到LSL流
    if model_name in self.position_outlets:
        position_sample = [float(x), float(y), float(z)]
        self.position_outlets[model_name].push_sample(position_sample)
```

**帧率**：跟随NatNet，约120 Hz

---

## 3.4 LSL时间同步机制⭐

### LSL统一时钟

**LSL提供全局时钟**：
```python
from pylsl import local_clock

# 所有程序调用local_clock()得到统一时间
t1 = local_clock()  # 程序A
t2 = local_clock()  # 程序B
# t1和t2使用相同的时间基准！
```

**时钟特性**：
- **单调递增**：保证不回退
- **高精度**：微秒级（0.000001秒）
- **跨进程**：不同程序自动同步
- **跨设备**：网络自动校准

### 时间戳自动添加

```python
# 发送端（Outlet）
outlet.push_sample([1, 2, 3])  # 无需提供时间戳

# LSL自动添加：
# 内部调用local_clock()获取当前时间
# 样本带有时间戳：(sample=[1,2,3], timestamp=12345.678)

# 接收端（Inlet）
sample, timestamp = inlet.pull_sample()
# timestamp就是LSL时钟的发送时刻
```

### 多设备时间同步示例

```python
# 设备A：OptiTrack（Python）
t_optitrack = local_clock()  # 100.000秒
outlet.push_sample([x, y, z])

# 设备B：fNIRS（另一台电脑）
t_fnirs = local_clock()  # 100.000秒（自动同步！）
fnirs_outlet.push_sample([oxy, deoxy])

# 设备C：LSL录制器（又一台电脑）
sample_ot, timestamp_ot = inlet_ot.pull_sample()
sample_fn, timestamp_fn = inlet_fn.pull_sample()

# 时间戳对齐
if abs(timestamp_ot - timestamp_fn) < 0.001:  # <1ms
    print("数据同步！")
```

**本项目应用**：
```python
# data_logger.py中使用LSL时钟
from pylsl import local_clock

def _get_lsl_timestamp(self):
    return local_clock()  # 与LSL流完全同步

# 所有数据使用相同时钟
Behavior.csv → local_clock()
Position.csv → local_clock()
Markers.csv → local_clock()
LSL流 → local_clock()（自动）
```

---

## 3.5 流发现机制

### 流注册与发现

```
┌────────────────┐
│  程序A         │
│  创建Outlet    │  → 注册到LSL网络（UDP组播）
└────────────────┘
        ↓
  【LSL网络】
  (239.255.42.99)
        ↓
┌────────────────┐
│  程序B         │
│  resolve_streams() → 扫描LSL网络 → 发现流
└────────────────┘
```

### 流发现API

#### 方法1：发现所有流

```python
from pylsl import resolve_streams

# 扫描5秒，发现所有LSL流
streams = resolve_streams(wait_time=5.0)

print(f"发现{len(streams)}个流:")
for stream in streams:
    print(f"  - {stream.name()} ({stream.type()})")
```

#### 方法2：按类型发现

```python
from pylsl import resolve_byprop

# 只发现MoCap类型的流
mocap_streams = resolve_byprop('type', 'MoCap', timeout=5.0)

# 只发现Marker类型的流
marker_streams = resolve_byprop('type', 'Markers', timeout=5.0)
```

#### 方法3：按名称发现

```python
from pylsl import resolve_byprop

# 发现特定名称的流
sub001_streams = resolve_byprop('name', 'Sub001_Position', timeout=5.0)
```

**本项目使用**（lsl_recorder.py）：
```python
def discover_streams(self, timeout=3.0):
    streams = resolve_streams(wait_time=timeout)
    
    for stream in streams:
        print(f"  [{i+1}] {stream.name()} | Type: {stream.type()} | "
              f"Channels: {stream.channel_count()} | Rate: {stream.nominal_srate()}Hz")
    
    return streams
```

---

## 3.6 本项目的LSL实现

### LSL Marker流（发送端）

**位置**：`lsl_manager.py`

#### 创建Marker流

```python
def initialize_marker_outlet(self):
    # 创建StreamInfo
    marker_info = StreamInfo(
        name='Navigation_Markers',
        type='Markers',
        channel_count=1,
        nominal_srate=0,  # 事件驱动
        channel_format='int32',
        source_id='navigation_ttl_markers'
    )
    
    # 添加通道描述
    channels = marker_info.desc().append_child("channels")
    ch = channels.append_child("channel")
    ch.append_child_value("label", "TTL_Code")
    ch.append_child_value("unit", "")
    ch.append_child_value("type", "marker")
    
    # 创建Outlet
    self.marker_outlet = StreamOutlet(marker_info)
```

#### 异步发送Marker

```python
# 主线程（不阻塞）
def send_marker(self, code, meaning):
    self.marker_queue.put(code)  # 放入队列
    print(f"⏰ Marker已排队: {code} ({meaning})")

# 独立线程（异步发送）
def _marker_send_loop(self):
    while self.marker_running:
        code = self.marker_queue.get(timeout=0.1)
        
        # 发送到LSL
        self.marker_outlet.push_sample([code])
```

**优势**：
- ✅ 主循环不被阻塞
- ✅ 发送速度快（<1ms）
- ✅ 支持高频事件

---

### LSL位置流（发送端）

**位置**：`lsl_manager.py`

#### 创建位置流

```python
def initialize_position_outlets(self, sub_ids=['001', '002']):
    for sub_id in sub_ids:
        # 创建StreamInfo（3通道：X,Y,Z）
        position_info = StreamInfo(
            name=f"Sub{sub_id}_Position",
            type='MoCap',
            channel_count=3,
            nominal_srate=0,  # 不规则采样
            channel_format='float32',
            source_id=f'optitrack_sub{sub_id}'
        )
        
        # 添加详细元数据
        channels = position_info.desc().append_child("channels")
        for axis in ['X', 'Y', 'Z']:
            ch = channels.append_child("channel")
            ch.append_child_value("label", f"Position_{axis}")
            ch.append_child_value("unit", "meters")
            ch.append_child_value("type", "Position")
            ch.append_child_value("coordinate_system", "Motive_World")
        
        # 设备信息
        acquisition = position_info.desc().append_child("acquisition")
        acquisition.append_child_value("manufacturer", "OptiTrack")
        acquisition.append_child_value("system", "Motive")
        acquisition.append_child_value("protocol", "NatNet")
        acquisition.append_child_value("subject_id", f"Sub{sub_id}")
        
        # 创建Outlet
        outlet = StreamOutlet(position_info)
        self.position_outlets[f"Sub{sub_id}"] = outlet
```

#### 推送位置数据

```python
def _on_new_frame(self, data_dict):
    # 计算Markerset质心
    centroid = (x, y, z)
    
    # 推送到LSL流
    if model_name in self.position_outlets:
        position_sample = [
            float(centroid[0]),  # X
            float(centroid[1]),  # Y
            float(centroid[2])   # Z
        ]
        self.position_outlets[model_name].push_sample(position_sample)
```

---

### LSL流（接收端）

**位置**：`lsl_recorder.py`

#### 发现流

```python
def discover_streams(self, timeout=3.0):
    streams = resolve_streams(wait_time=timeout)
    
    for stream in streams:
        print(f"发现: {stream.name()} | Type: {stream.type()}")
    
    return streams
```

#### 录制流

```python
def _record_worker(self):
    # 连接到所有选中的流
    self.inlets = []
    for stream in self.selected_streams:
        inlet = StreamInlet(stream)
        self.inlets.append(inlet)
    
    # 录制循环
    while self.is_recording:
        for inlet in self.inlets:
            sample, timestamp = inlet.pull_sample(timeout=0.001)
            
            if sample:
                # 缓存数据
                stream_name = inlet.info().name()
                self.data_buffers[stream_name].append({
                    'timestamp': timestamp,
                    'sample': sample
                })
                
                self.total_samples += 1
        
        # 定期自动保存（每30秒）
        if time.time() - self.last_save_time >= 30.0:
            self._save_data_incremental()
```

---

## 3.7 LSL故障排查

### 问题1：resolve_streams()找不到流

**症状**：
```python
streams = resolve_streams(wait_time=5.0)
print(len(streams))  # 0，未发现任何流
```

**诊断步骤**：

#### 步骤1：确认Outlet已创建

```python
# 检查lsl_manager是否已启动
lsl_manager = LSLManager()
result = lsl_manager.start_services(enable_position_broadcast=True)

# 应该看到：
# ✅ LSL Marker流已创建
# ✅ OptiTrack位置LSL流已创建（共2个）
```

#### 步骤2：检查网络

```python
# LSL使用UDP组播：239.255.42.99
# 检查防火墙是否阻止UDP

# Windows防火墙 → 高级设置 → 入站规则
# 确保允许Python.exe的UDP通信
```

#### 步骤3：增加扫描时间

```python
# 从5秒增加到15秒
streams = resolve_streams(wait_time=15.0)
```

#### 步骤4：检查pylsl版本

```bash
python -c "import pylsl; print(pylsl.__version__)"
# 应该显示：1.17.6或类似版本
```

### 问题2：pull_sample()一直没有数据

**症状**：
```python
inlet = StreamInlet(stream)
sample, timestamp = inlet.pull_sample(timeout=1.0)
# sample = None（超时）
```

**可能原因**：

#### 原因A：Outlet未推送数据

**检查**：
```python
# 在Outlet端检查
# lsl_manager._on_new_frame()是否被调用？
# 添加调试输出：
print(f"推送位置: {position_sample}")
self.position_outlets[model_name].push_sample(position_sample)
```

#### 原因B：网络阻塞

**检查**：
```python
# 尝试本地回环测试
# 在同一台电脑上发送和接收
```

#### 原因C：流名称不匹配

**检查**：
```python
# Outlet创建的名称
outlet_name = "Sub001_Position"

# Inlet连接的流
inlet_stream_name = inlet.info().name()

# 应该完全一致！
assert outlet_name == inlet_stream_name
```

### 问题3：时间戳不一致

**症状**：
```
LSL流时间戳：98870.xxx
Behavior.csv时间戳：1729152034.xxx（相差很大）
```

**原因**：混用了不同时钟

**解决**：
```python
# 确保所有地方使用local_clock()
from pylsl import local_clock

# ✅ 正确
timestamp = local_clock()

# ❌ 错误
timestamp = time.time()  # Python本地时间
```

**验证**：
```python
import time
from pylsl import local_clock

t1 = time.time()
t2 = local_clock()

print(f"time.time(): {t1}")     # 1729152034.xxx（Unix时间）
print(f"local_clock(): {t2}")   # 98870.xxx（LSL时钟）
print(f"差值: {t1 - t2:.0f}秒")  # 可能相差数十年！
```

---

## 3.8 LSL流订阅示例（外部设备）

### 示例：fNIRS设备接收OptiTrack位置

```python
"""
假设fNIRS设备的Python程序
需要接收OptiTrack位置数据进行同步分析
"""

from pylsl import resolve_byprop, StreamInlet, local_clock

# 1. 发现OptiTrack位置流
print("查找OptiTrack位置流...")
mocap_streams = resolve_byprop('type', 'MoCap', timeout=10.0)

if not mocap_streams:
    print("未找到OptiTrack流，请确保实验程序已启动")
    exit()

# 2. 连接到Sub001位置流
sub001_stream = None
for stream in mocap_streams:
    if 'Sub001' in stream.name():
        sub001_stream = stream
        break

inlet = StreamInlet(sub001_stream)

# 3. 接收位置数据
print("开始接收Sub001位置...")
while True:
    # 获取OptiTrack位置
    sample, timestamp = inlet.pull_sample()
    x, y, z = sample[0], sample[1], sample[2]
    
    # 获取当前fNIRS数据（假设）
    fnirs_data = get_fnirs_data()  # 自己的采集函数
    fnirs_timestamp = local_clock()
    
    # 检查时间同步
    time_diff = abs(fnirs_timestamp - timestamp)
    
    if time_diff < 0.010:  # <10ms
        # 位置和fNIRS数据同步！
        print(f"同步数据: 位置=({x:.3f},{y:.3f},{z:.3f}), fNIRS={fnirs_data}")
    else:
        print(f"时间差过大: {time_diff*1000:.1f}ms")
```

---

## 3.9 LSL录制器技术细节

### 录制器架构

```
LSLRecorderCore
    ├── discover_streams()     # 发现流
    ├── select_streams()       # 选择要录制的流
    ├── start_recording()      # 开始录制
    │   └── _record_worker()   # 录制线程
    │       ├── pull_sample()  # 接收数据
    │       ├── 缓存到buffer
    │       └── 定期自动保存（每30秒）
    └── stop_recording()       # 停止录制
        └── _save_data()       # 最终保存
```

### 数据保存策略（V3.3.1）

#### 4层保护机制

```
层1: 定期自动保存（每30秒）
    ↓ 追加模式写入文件
    └─ 清空buffer

层2: 正常停止保存
    ↓ stop_recording()调用
    └─ 保存剩余buffer数据

层3: 信号处理器（Ctrl+C）
    ↓ signal_handler()捕获
    └─ 触发stop_recording()

层4: 紧急保存（atexit）
    ↓ 程序退出时自动调用
    └─ _emergency_save()
```

#### 文件写入模式

```python
# 第1次：创建文件+表头
with open(file, 'w') as f:
    writer.writerow(['Timestamp', 'Ch_1', 'Ch_2', 'Ch_3'])  # 表头
    writer.writerows(buffer_data)  # 首批数据

# 第2次（30秒后）：追加模式
with open(file, 'a') as f:
    writer.writerows(buffer_data)  # 追加，无表头

# 第3次（60秒后）：追加模式
with open(file, 'a') as f:
    writer.writerows(buffer_data)  # 追加
```

**优势**：
- ✅ 数据实时写入磁盘
- ✅ 内存占用低（buffer<3600样本）
- ✅ 程序崩溃最多丢失30秒

---

## 3.10 LSL最佳实践

### 1. Outlet生命周期管理

```python
# ✅ 推荐：单例模式
class LSLManager:
    def __init__(self):
        self.position_outlets = {}
    
    def initialize_position_outlets(self):
        # 只创建一次
        outlet = StreamOutlet(info)
        self.position_outlets['Sub001'] = outlet
    
    def cleanup(self):
        # 清理时自动注销
        self.position_outlets.clear()

# ❌ 不推荐：每次创建新Outlet
def send_data():
    info = StreamInfo(...)
    outlet = StreamOutlet(info)  # 每次都创建
    outlet.push_sample([x, y, z])
```

### 2. 推送频率控制

```python
# ✅ 推荐：跟随数据源帧率
def _on_new_frame(self, data_dict):
    # NatNet每帧调用一次（~120Hz）
    # 直接推送
    outlet.push_sample(sample)

# ❌ 不推荐：固定延迟
while True:
    outlet.push_sample(sample)
    time.sleep(1/120)  # 可能与数据源不同步
```

### 3. 元数据的重要性

```python
# ✅ 推荐：添加详细元数据
channels = info.desc().append_child("channels")
ch.append_child_value("label", "Position_X")
ch.append_child_value("unit", "meters")
ch.append_child_value("type", "Position")

# ⚠️ 可用但不推荐：无元数据
info = StreamInfo("MyStream", "Data", 3, 0, "float32")
# 接收端不知道通道含义
```

### 4. 错误处理

```python
# ✅ 推荐：容错处理
try:
    outlet.push_sample(sample)
except Exception as e:
    self.logger.warning(f"LSL推送失败: {e}")
    # 继续运行，不影响主流程

# ❌ 不推荐：让异常中断程序
outlet.push_sample(sample)  # 如果失败，程序崩溃
```

---

## 3.11 性能优化

### Outlet性能

**单个Outlet**：
- 推送延迟：<1ms
- CPU占用：<0.1%
- 内存占用：<1MB

**多个Outlet（本项目：3个）**：
- 推送延迟：<2ms
- CPU占用：<0.5%
- 内存占用：<3MB

**结论**：LSL开销极小，可以放心使用！

### Inlet性能

**pull_sample()延迟**：
- 有数据：<1ms
- 无数据（timeout）：timeout时间

**优化建议**：
```python
# ✅ 推荐：短timeout，非阻塞
sample, ts = inlet.pull_sample(timeout=0.001)

# ❌ 不推荐：长timeout，阻塞主循环
sample, ts = inlet.pull_sample(timeout=1.0)
```

---

## 3.12 LSL工具生态

### pyxdf - XDF文件读取

```python
import pyxdf

# 读取XDF文件
data, header = pyxdf.load_xdf('recording.xdf')

# data是列表，每个元素是一个流
for stream in data:
    print(f"流: {stream['info']['name'][0]}")
    print(f"样本数: {len(stream['time_series'])}")
    print(f"时间戳: {stream['time_stamps']}")
```

### LabRecorder - 官方录制工具

**本项目不使用LabRecorder的原因**：
- ❌ 文件命名不灵活
- ❌ 只支持XDF格式（本项目需要CSV）
- ❌ 无法程序化控制

**本项目自己实现lsl_recorder.py**：
- ✅ 灵活的文件命名
- ✅ 同时保存XDF和CSV
- ✅ CLI/GUI双模式
- ✅ 定期自动保存

---

## 下一章

**→ [第4章 配置参数完全手册](技术文档-第4章-配置参数.md)**

学习所有可调参数及其效果，掌握系统调优方法。

---

**本章节关键点**：
- ✅ 使用`resolve_streams()`发现流
- ✅ `StreamInfo`描述流，`StreamOutlet`发送，`StreamInlet`接收
- ✅ 使用`local_clock()`确保时间同步
- ✅ Outlet只创建一次，重复使用

