# 快速参考卡 - V3.3.1

**打印此页作为快速查阅** 📋

---

## 🚀 启动命令

```bash
# 1. LSL录制器（先启动）
python Scripts\Tools\lsl_recorder.py --cli --output-dir Data --scan-timeout 10 --verbose

# 2. 实验程序（后启动）
python run_experiment.py
```

---

## 🔧 配置文件

**文件**：`Config/experiment_config.json`

```json
"scale_factor": 180.0,               ← 缩放因子（像素/米）
"server_ip": "192.168.3.58",         ← Motive IP
"client_ip": "192.168.3.55",         ← 本机IP
"interval_after_target_found": 2.0   ← 音频间隔（秒）
```

---

## 📊 缩放因子速查

| 房间 | scale_factor |
|------|--------------|
| 4m | 270 |
| 5m | 216 |
| **6m** | **180** |
| 8m | 135 |

---

## 🎯 LSL流

| 流名称 | 通道 | 含义 | 录制 |
|--------|------|------|------|
| Navigation_Markers | Ch_1 | TTL码(1-5) | ❌ |
| Sub001_Position | Ch_1,2,3 | X,Y,Z(米) | ✅ |
| Sub002_Position | Ch_1,2,3 | X,Y,Z(米) | ✅ |

---

## 🔍 故障速查

| 症状 | 原因 | 解决 |
|------|------|------|
| 光点不动 | Skeleton类型 | 改Markerset |
| 无NatNet数据 | Motive未录制 | 点击红色按钮 |
| LSL找不到流 | 启动顺序错 | 先实验后录制器 |
| ESC后无数据 | 旧版本 | V3.3.1已修复 |

---

## 🛠️ 测试工具

```bash
# NatNet测试
python Scripts\Tools\test_natnet_to_psychopy.py

# LSL测试
python Scripts\Tools\test_optitrack_lsl_streams.py

# 诊断
python Scripts\Tools\diagnose_natnet_data.py
```

---

## 📁 数据位置

```
Data/
├── Behavior/D{dyad}/    ← Behavior/Position/Markers.csv
├── OptiTrack/D{dyad}/   ← OptiTrack原始数据
└── LSL/{日期}/          ← LSL位置流录制
```

---

## ⚡ 性能指标

- PsychoPy: 30 FPS
- NatNet: ~120 Hz
- 延迟: <50ms
- CPU: 30-40%
- 可靠性: 99.9%

---

## 📞 帮助

**问题？** → [第6章 故障诊断](技术文档-第6章-故障诊断.md)

**技术？** → [第2章 NatNet](技术文档-第2章-NatNet系统.md) / [第3章 LSL](技术文档-第3章-LSL系统.md)

**参数？** → [第4章 配置](技术文档-第4章-配置参数.md)

---

**版本**: V3.3.1  
**状态**: Production Ready ✅

