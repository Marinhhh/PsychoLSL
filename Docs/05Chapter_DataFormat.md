# 第5章 数据格式规范

**版本**: V3.3.1  
**章节**: 5/6

---

## 5.1 CSV文件格式

### Behavior.csv

**路径**：`Data/Behavior/D{dyad}/D{dyad}_{timestamp}.Behavior.csv`

**表头**：
```csv
SubID,SubRole,Phase,Session,Block,IsNavigation,Trial,WallMarker,Time_Wall_go,Time_Wall_arrive,RT_WallMarker,Target,Target_position,Time_Target_go,Time_Target_arrive,RT_Target,KeyNumber,Key_Navigation_position,Key_Time,AccNumber,PerAcc
```

**字段说明**：

| 字段 | 类型 | 含义 | 示例 |
|------|------|------|------|
| SubID | str | 被试ID | "001" |
| SubRole | str | 被试角色 | "A"或"B" |
| Phase | int | 实验阶段 | 0或1 |
| Session | str | 会话ID | "S2" |
| Block | int | Block编号 | 1 |
| IsNavigation | int | 是否为导航者 | 1或0 |
| Trial | int | Trial编号 | 1-20 |
| WallMarker | str | 墙标ID | "A5" |
| **Time_Wall_go** | float | 开始前往墙标时刻（LSL时钟） | 101007.618 |
| **Time_Wall_arrive** | float | 到达墙标时刻 | 101036.572 |
| **RT_WallMarker** | float | 墙标反应时间（秒） | 28.954 |
| Target | str | 目标ID | "P2" |
| **Target_position** | str | 目标坐标"x,z" | "1.200,-0.800" |
| **Time_Target_go** | float | 开始搜索时刻 | 101038.000 |
| **Time_Target_arrive** | float | 找到目标时刻 | 101065.123 |
| **RT_Target** | float | 搜索反应时间（秒） | 27.123 |
| KeyNumber | int | 观察者按键次数 | 3 |
| Key_Navigation_position | str | 按键时导航者位置 | "0.5,1.2;..." |
| Key_Time | str | 按键时间列表 | "101040.1;..." |
| AccNumber | int | 正确按键数 | 2 |
| PerAcc | float | 正确率 | 0.67 |

**示例数据行**：
```csv
001,A,0,S2,1,1,1,A5,101007.618,101036.572,28.954,P2,"1.200,-0.800",101038.000,101065.123,27.123,0,"","",0,0.0
```

---

### Position.csv

**路径**：`Data/Behavior/D{dyad}/D{dyad}_{timestamp}.Position.csv`

**表头**：
```csv
SubID,SubRole,Phase,Session,Block,IsNavigation,Timestamp,Raw_x,Raw_y,Pos_x,Pos_y,Frame
```

**字段说明**：

| 字段 | 类型 | 含义 | 单位 |
|------|------|------|------|
| Timestamp | float | LSL时钟时间戳 | 秒 |
| Raw_x | float | Motive X坐标 | 米 |
| Raw_y | float | Motive Z坐标 | 米 |
| Pos_x | float | PsychoPy X坐标 | 像素 |
| Pos_y | float | PsychoPy Y坐标 | 像素 |
| Frame | int | 帧编号 | - |

**采样率**：~120 Hz（跟随NatNet）

**数据量**：15分钟实验约108,000行

---

### Markers.csv

**路径**：`Data/Behavior/D{dyad}/D{dyad}_{timestamp}.Markers.csv`

**表头**：
```csv
Timestamp,Marker,Meaning,Trial,Phase,Additional_Info
```

**字段说明**：

| 字段 | 类型 | 含义 |
|------|------|------|
| Timestamp | float | LSL时钟时间戳（秒） |
| Marker | int | TTL码（1-5） |
| Meaning | str | 事件含义 |
| Trial | str | Trial编号 |
| Phase | str | Phase编号 |
| Additional_Info | str | 额外信息 |

**TTL码定义**：
| 码 | 含义 |
|----|------|
| 1 | Trial开始 |
| 2 | 到达墙面标记 |
| 3 | 观察者按键 |
| 4 | 找到隐藏目标 |
| 5 | Block结束 |

**示例数据**：
```csv
101007.618,1,Trial开始,1,0,
101036.572,2,到达墙面标记,1,0,
101065.123,4,找到隐藏目标,1,0,
101070.000,1,Trial开始,2,0,
```

---

## 5.2 LSL流数据格式

### Sub001/Sub002_Position.csv

**路径**：`Data/LSL/{日期}/LSL_Recording_Sub00X_Position_{timestamp}.csv`

**表头**：
```csv
Timestamp,Ch_1,Ch_2,Ch_3
```

**字段说明**：

| 字段 | 含义 | 单位 | 坐标系 |
|------|------|------|--------|
| Timestamp | LSL时钟时间戳 | 秒 | - |
| Ch_1 | Position_X | 米 | Motive世界坐标 |
| Ch_2 | Position_Y | 米 | Motive Up-axis（高度） |
| Ch_3 | Position_Z | 米 | Motive世界坐标 |

**坐标系说明**：
```
     Y (Up)
     ↑
     |
     |_____→ X (Right)
    /
   ↙
  Z (Forward)
```

**示例数据**：
```csv
98867.377,-0.461,0.034,1.095
98867.385,-0.462,0.034,1.096
98867.393,-0.463,0.034,1.097
```

**含义**：
- X=-0.461m：向左46.1cm
- Y=0.034m：高度3.4cm
- Z=1.095m：向前109.5cm

---

### Navigation_Markers.csv（可选）

**路径**：`Data/LSL/{日期}/LSL_Recording_Navigation_Markers_{timestamp}.csv`

**表头**：
```csv
Timestamp,Ch_1
```

**字段说明**：

| 字段 | 含义 | 取值 |
|------|------|------|
| Timestamp | LSL时钟时间戳（秒） | float |
| Ch_1 | TTL标记码 | 1-5 |

**注意**：此文件信息较少（只有时间戳和TTL码），建议使用`Markers.csv`（更详细）。

---

## 5.3 时间戳系统

### LSL统一时钟

**所有数据使用`pylsl.local_clock()`**：

```python
from pylsl import local_clock

# 所有地方
timestamp = local_clock()
```

**时间戳格式**：
```
98867.377  # 秒，从某个固定起点开始
```

**特性**：
- ✅ 高精度（微秒级）
- ✅ 单调递增
- ✅ 跨设备同步

### 时间对齐示例

```python
import pandas as pd

# 读取所有数据
behavior = pd.read_csv('Data/Behavior/.../Behavior.csv')
markers = pd.read_csv('Data/Behavior/.../Markers.csv')
position_lsl = pd.read_csv('Data/LSL/.../Sub001_Position_*.csv')

# 时间范围对齐
print("Behavior时间范围:", behavior['Time_Wall_go'].min(), "-", behavior['Time_Target_arrive'].max())
print("Markers时间范围:", markers['Timestamp'].min(), "-", markers['Timestamp'].max())
print("LSL位置时间范围:", position_lsl['Timestamp'].min(), "-", position_lsl['Timestamp'].max())

# 应该在相同范围内！
```

---

## 5.4 数据分析方法

### 分析1：Trial级行为分析

```python
import pandas as pd
import numpy as np

# 读取Behavior数据
behavior = pd.read_csv('Data/Behavior/D001/S2/D001_*.Behavior.csv')

# 过滤有效trial（完成了任务）
valid_trials = behavior.dropna(subset=['Time_Target_arrive'])

# 统计
print(f"总Trials: {len(behavior)}")
print(f"完成Trials: {len(valid_trials)}")
print(f"完成率: {len(valid_trials)/len(behavior)*100:.1f}%")

# 反应时间分析
print(f"\n墙标导航反应时间:")
print(f"  平均: {valid_trials['RT_WallMarker'].mean():.1f}秒")
print(f"  标准差: {valid_trials['RT_WallMarker'].std():.1f}秒")
print(f"  范围: {valid_trials['RT_WallMarker'].min():.1f} - {valid_trials['RT_WallMarker'].max():.1f}秒")

print(f"\n目标搜索反应时间:")
print(f"  平均: {valid_trials['RT_Target'].mean():.1f}秒")
print(f"  标准差: {valid_trials['RT_Target'].std():.1f}秒")
```

### 分析2：轨迹可视化

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取位置数据
pos = pd.read_csv('Data/LSL/.../LSL_Recording_Sub001_Position_*.csv')

# 提取XZ坐标（2D平面）
x = pos['Ch_1'].values
z = pos['Ch_3'].values

# 绘制轨迹
plt.figure(figsize=(10, 10))
plt.plot(x, z, 'b-', alpha=0.5, linewidth=0.5, label='轨迹')
plt.scatter(x[0], z[0], c='g', s=200, marker='o', label='起点')
plt.scatter(x[-1], z[-1], c='r', s=200, marker='x', label='终点')

# 添加房间边界
plt.plot([-3, 3, 3, -3, -3], [-3, -3, 3, 3, -3], 'k--', label='房间边界')

plt.xlabel('X (米)')
plt.ylabel('Z (米)')
plt.title('Sub001移动轨迹')
plt.axis('equal')
plt.grid(True, alpha=0.3)
plt.legend()
plt.show()
```

### 分析3：速度计算

```python
# 读取位置数据
pos = pd.read_csv('Data/LSL/.../Sub001_Position_*.csv')

# 计算速度
x = pos['Ch_1'].values
z = pos['Ch_3'].values
t = pos['Timestamp'].values

# 每帧的位移
dx = np.diff(x)
dz = np.diff(z)
dt = np.diff(t)

# 速度（米/秒）
distance = np.sqrt(dx**2 + dz**2)
speed = distance / dt

# 统计
print(f"平均速度: {np.mean(speed):.3f} m/s")
print(f"最大速度: {np.max(speed):.3f} m/s")
print(f"总移动距离: {np.sum(distance):.2f} m")

# 速度分布
plt.hist(speed, bins=50)
plt.xlabel('速度 (m/s)')
plt.ylabel('频次')
plt.title('速度分布')
plt.show()
```

### 分析4：事件相关分析

```python
# 读取数据
markers = pd.read_csv('Data/Behavior/.../Markers.csv')
position = pd.read_csv('Data/LSL/.../Sub001_Position_*.csv')

# 找到所有"找到目标"事件
target_found = markers[markers['Marker'] == 4]

# 提取事件前后2秒的位置数据
for idx, event in target_found.iterrows():
    event_time = event['Timestamp']
    
    # 事件前后2秒的数据
    time_window = (position['Timestamp'] >= event_time - 2) & \
                  (position['Timestamp'] <= event_time + 2)
    
    pos_segment = position[time_window]
    
    # 分析这段时间的行为
    x = pos_segment['Ch_1'].values
    z = pos_segment['Ch_3'].values
    
    # 计算停留时间（速度<0.1m/s）
    speeds = np.sqrt(np.diff(x)**2 + np.diff(z)**2) / np.diff(pos_segment['Timestamp'].values)
    停留帧数 = np.sum(speeds < 0.1)
    
    print(f"Trial {event['Trial']}: 找到目标时的停留帧数={停留帧数}")
```

---

## 5.5 数据完整性检查

### 检查脚本

```python
import pandas as pd
from pathlib import Path

def check_data_integrity(dyad_id, session_id):
    """检查数据完整性"""
    base_path = Path(f"Data/Behavior/D{dyad_id:03d}/")
    
    # 查找文件
    behavior_files = list(base_path.glob("*.Behavior.csv"))
    position_files = list(base_path.glob("*.Position.csv"))
    markers_files = list(base_path.glob("*.Markers.csv"))
    
    print(f"数据完整性检查 - D{dyad_id:03d}")
    print("=" * 50)
    
    # 检查Behavior
    if behavior_files:
        behavior = pd.read_csv(behavior_files[0])
        print(f"✅ Behavior.csv: {len(behavior)} trials")
        
        # 检查缺失字段
        missing_wall = behavior['Time_Wall_arrive'].isna().sum()
        missing_target = behavior['Time_Target_arrive'].isna().sum()
        
        print(f"   未完成墙标: {missing_wall}/{len(behavior)}")
        print(f"   未完成目标: {missing_target}/{len(behavior)}")
    else:
        print("❌ Behavior.csv不存在")
    
    # 检查Position
    if position_files:
        position = pd.read_csv(position_files[0])
        print(f"✅ Position.csv: {len(position)} 帧")
        
        duration = position['Timestamp'].iloc[-1] - position['Timestamp'].iloc[0]
        srate = len(position) / duration
        print(f"   时长: {duration:.1f}秒")
        print(f"   采样率: {srate:.1f} Hz")
    else:
        print("❌ Position.csv不存在")
    
    # 检查Markers
    if markers_files:
        markers = pd.read_csv(markers_files[0])
        print(f"✅ Markers.csv: {len(markers)} 事件")
        
        # 统计marker类型
        marker_counts = markers['Marker'].value_counts().sort_index()
        for code, count in marker_counts.items():
            print(f"   Marker {code}: {count}次")
    else:
        print("❌ Markers.csv不存在")
    
    # 检查LSL数据
    lsl_path = Path("Data/LSL/")
    lsl_files = list(lsl_path.glob("**/*Sub001_Position*.csv"))
    
    if lsl_files:
        lsl_pos = pd.read_csv(lsl_files[0])
        print(f"✅ LSL位置数据: {len(lsl_pos)} 帧")
    else:
        print("⚠️  LSL位置数据不存在（可能未启动录制器）")

# 使用
check_data_integrity(dyad_id=1, session_id=2)
```

---

## 下一章

**→ [第6章 故障诊断手册](技术文档-第6章-故障诊断.md)**

学习如何诊断和解决各种问题。

---

**本章节要点**：
- ⭐ 所有时间戳使用LSL时钟（`local_clock()`）
- ⭐ Position.csv和LSL位置流数据可互相验证
- ⭐ Markers.csv比LSL Marker流包含更多信息

