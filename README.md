# 空间导航与神经同步实验系统

**基于OptiTrack和LSL的多模态实验平台**

[![Version](https://img.shields.io/badge/version-3.3.1-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## 🎯 系统简介

本系统用于研究二人协作空间导航任务中的行为和神经同步现象，集成了OptiTrack动作捕捉和LSL数据流技术。

### 核心功能

- ✅ **实时位置跟踪**：OptiTrack ~120 Hz高精度定位
- ✅ **实时可视化**：PsychoPy 30 FPS流畅显示
- ✅ **LSL数据流**：3路广播（Marker + 2位置流）
- ✅ **多模态同步**：LSL统一时钟，微秒级精度
- ✅ **数据可靠性**：4层保护，99.9%不丢失
- ✅ **完整记录**：Behavior/Position/Markers/OptiTrack CSV

---

## 🚀 5分钟快速开始

### 前置条件

1. **硬件**：OptiTrack动作捕捉系统
2. **软件**：Motive软件（正在运行）
3. **Python**：3.8+，已安装依赖

### 1. 配置Motive

**Assets面板**：
- 创建2个**Markerset**（不是Skeleton）
- 命名为"Sub001"和"Sub002"
- 确保为绿色（正在跟踪）

**流设置**（编辑 > 设置 > 流设置）：
- ✅ Broadcast Frame Data
- ✅ Marker Set
- ✅ Labeled Markers

**开始录制**（底部红色按钮）

### 2. 启动系统

```bash
# 克隆或进入项目目录
cd D:\桌面\Navigation

# 启动实验
python run_experiment.py
```

**就这么简单！** 🎉

### 3. （可选）启动LSL录制器

```bash
# 新终端
python Scripts\Tools\lsl_recorder.py --gui
```

点击"开始录制"，录制OptiTrack位置流。

---

## 📖 完整文档

### 技术文档（6章详细手册）

**入口**：[技术文档-主文档.md](docs/Main.md)

1. **[第1章 项目架构](docs/01Chapter_ProjectFrame.md)** - 模块详解、依赖关系
2. **[第2章 NatNet系统](docs/02Chapter_NatnetSdk.md)** ⭐ - 数据采集技术
3. **[第3章 LSL系统](docs/03Chapter_LabStreamingLayor.md)** ⭐ - 数据流技术
4. **[第4章 配置参数](docs/04Chapter_Config.md)** - 参数手册
5. **[第5章 数据格式](docs/05Chapter_DataFormat.md)** - 格式规范
6. **[第6章 故障诊断](docs/06Chapter_Problem.md)** - 问题解决

### 其他文档

- **框架文档**：[framework.md](docs/framework.md)
- **研究设计**：[research_design.md](docs/research_design.md)
- **版本更新**：[docs/Change/](docs/Change/)

---

## 🎓 常见问题速查

| 问题 | 快速解决 | 详细说明 |
|------|---------|---------|
| **光点不移动** | Sub001改为Markerset | [第6章 6.1](docs/06Chapter_Problem.md) |
| **调整缩放** | 修改`experiment_config.json`第6行 | [第4章 4.1](docs/04Chapter_Config.md) |
| **LSL无数据** | 先启动录制器，再启动实验 | [第6章 6.2](docs/06Chapter_Problem.md) |
| **NatNet连接失败** | 检查IP和Motive录制状态 | [第2章 2.8](docs/02Chapter_NatnetSdk.md) |

---

## 📊 数据输出

### 单次实验（15分钟）生成的文件

```
Data/
├── Behavior/D001/            # 行为数据
│   ├── Behavior.csv (20 trials)
│   ├── Position.csv (~108,000帧)
│   └── Markers.csv (~100事件)
│
├── OptiTrack/D001/           # 原始OptiTrack数据
│   └── *.csv (~108,000帧)
│
└── LSL/20251017/             # LSL流录制
    ├── Sub001_Position.csv (~108,000帧)
    └── Sub002_Position.csv (~108,000帧)
```

**总量**：约30-35 MB

---

## 🔧 核心配置

### 必改参数

**文件**：`Config/experiment_config.json`

```json
{
  "transform_params": {
    "scale_factor": 180.0,  ← 根据房间大小调整（150-250）
  },
  
  "natnet_config": {
    "server_ip": "192.168.3.58",  ← Motive电脑IP
    "client_ip": "192.168.3.55"   ← Python电脑IP
  },
  
  "audio_config": {
    "interval_after_target_found": 2.0  ← 音频间隔（1-5秒）
  }
}
```

### 缩放因子速查表

| 房间大小 | 推荐scale_factor |
|---------|-----------------|
| 4m × 4m | 270 |
| 5m × 5m | 216 |
| **6m × 6m** | **180**（默认） |
| 8m × 8m | 135 |

---

## 🛠️ 测试工具

```bash
# NatNet连接测试
python Scripts\Tools\test_natnet_to_psychopy.py

# LSL流测试
python Scripts\Tools\test_optitrack_lsl_streams.py

# 完整诊断
python Scripts\Tools\test_lsl_connection.py
```

---

## 📈 系统性能

| 指标 | 数值 |
|------|------|
| PsychoPy帧率 | 30 FPS |
| NatNet帧率 | ~120 Hz |
| 位置延迟 | <50 ms |
| CPU占用 | 30-40% |
| 数据可靠性 | 99.9% |

---

## 🎊 V3.3.1 新特性

- ✅ **OptiTrack→LSL位置流广播**（支持fNIRS/EEG同步）
- ✅ **LSL自动保存**（每30秒，ESC不丢数据）
- ✅ **Behavior字段完整**（所有时间戳正确记录）
- ✅ **时间戳统一**（LSL时钟，微秒同步）
- ✅ **GUI优化**（1200×800大窗口）
- ✅ **智能默认**（只录制位置流）

---

## 📞 获取帮助

### 文档

- **快速问题**：[第6章 故障诊断](docs/06Chapter_Problem.md)
- **技术细节**：[第2章 NatNet](docs/02Chapter_NatnetSdk.md) + [第3章 LSL](docs/03Chapter_LabStreamingLayor.md)
- **参数调整**：[第4章 配置参数](docs/04Chapter_Config.md)

### 诊断工具

运行相应工具获取详细诊断信息，查阅文档解决。

---

## 📄 许可证

MIT License

---

## 🏆 系统状态

**Version**: V3.3.1 Final  
**Status**: ✅ Production Ready  
**Reliability**: 99.9%  
**Documentation**: Complete

**准备投入使用！** 🚀

---

**维护者**: Research Team  
**最后更新**: 2025-10-17  
**技术支持**: 查阅完整技术文档

