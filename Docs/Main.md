# 空间导航与神经同步实验系统 - 完整技术文档

**版本**: V3.3.1 Final  
**最后更新**: 2025年10月17日  
**文档状态**: Production Ready ✅

---

## 📖 文档导航

本技术文档分为以下章节，每个章节都是独立的详细文档：

### 核心文档

1. **[第1章 项目架构与模块详解](01Chapter_ProjectFrame.md)**
   - 项目结构
   - 目录组织原则
   - 模块职责划分
   - 依赖关系

2. **[第2章 NatNet数据采集系统](02Chapter_NatnetSdk.md)** ⭐重点
   - NatNet协议原理
   - Markerset vs Skeleton vs RigidBody
   - 数据接收和处理
   - 常见问题和解决方案

3. **[第3章 LSL数据流系统](03Chapter_LabStreamingLayor.md)** ⭐重点
   - LSL核心概念
   - 流创建和广播
   - 流接收和录制
   - 时间同步机制

4. **[第4章 配置参数完全手册](04Chapter_Config.md)**
   - 所有可调参数
   - 参数效果说明
   - 推荐值和调优指南

5. **[第5章 数据格式规范](05Chapter_DataFormat.md)**
   - CSV文件格式
   - LSL流格式
   - 时间戳系统
   - 数据分析方法

6. **[第6章 故障诊断手册](06Chapter_Problem.md)**
   - 问题分类
   - 诊断工具
   - 解决方案
   - 常见问题FAQ

---

## 🎯 快速查找

### 按需求查找

**我想了解...**

- NatNet如何工作 → [第2章](02Chapter_NatnetSdk.md)
- LSL如何使用 → [第3章](03Chapter_LabStreamingLayor.md)
- 如何调整缩放因子 → [第4章 4.1节](04Chapter_Config.md#41-坐标转换参数)
- 数据文件格式 → [第5章](05Chapter_DataFormat.md)
- 为什么光点不动 → [第6章 6.1节](06Chapter_Problem.md#61-natnet连接问题)
- LSL录制失败 → [第6章 6.2节](06Chapter_Problem.md#62-lsl流问题)

### 按角色查找

**研究者/操作员**：
- 快速开始 → [第1章 1.5节](01Chapter_ProjectFrame.md#15-快速开始)
- 实验操作 → [第1章 1.6节](01Chapter_ProjectFrame.md#16-标准实验流程)

**技术人员**：
- 系统架构 → [第1章](01Chapter_ProjectFrame.md)
- NatNet集成 → [第2章](02Chapter_NatnetSdk.md)
- LSL集成 → [第3章](03Chapter_LabStreamingLayor.md)

**数据分析师**：
- 数据格式 → [第5章](05Chapter_DataFormat.md)
- 分析示例 → [第5章 5.5节](05Chapter_DataFormat.md#55-数据分析示例)

**故障排查**：
- 诊断手册 → [第6章](06Chapter_Problem.md)

---

## 🔧 系统概览

### 核心功能

```
Motive OptiTrack (动作捕捉)
    ↓ NatNet协议
LSLManager (Python核心)
    ├─→ PsychoPy (实时显示，30 FPS)
    ├─→ LSL位置流 (Sub001/002_Position, ~120 Hz)
    ├─→ LSL Marker流 (Navigation_Markers, 事件驱动)
    └─→ 数据保存 (Behavior/Position/Markers/OptiTrack CSV)
```

### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.9.7 | 核心语言 |
| **NatNet SDK** | 3.x | OptiTrack数据接收 |
| **pylsl** | 1.17.6 | LSL数据流 |
| **PsychoPy** | 2024.x | 实时可视化 |
| **PyQt5** | 5.x | LSL的GUI界面 |

### 数据流向

```
输入：Motive OptiTrack标记点
  ↓
处理：NatNet → Python → 坐标转换
  ↓
输出：
  ├─ PsychoPy窗口（实时）
  ├─ LSL流（广播）
  └─ CSV文件（存储）
```

---

## 📊 关键指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **NatNet帧率** | ~120 Hz | OptiTrack原生 |
| **LSL位置流** | ~120 Hz | 跟随NatNet |
| **PsychoPy显示** | 30 FPS | 视觉流畅 |
| **数据延迟** | <50 ms | 实时性保证 |
| **时间同步精度** | <1 ms | LSL时钟 |
| **数据可靠性** | 99.9% | 自动保存 |
| **CPU占用** | 30-40% | 轻量级 |

---

## 🎯 文档使用指南

### 首次阅读建议

1. **第1章**（必读）- 了解整体架构
2. **第2章**（重要）- 理解NatNet数据采集
3. **第3章**（重要）- 理解LSL数据流
4. **第4章**（参考）- 需要时查阅配置
5. **第5章**（参考）- 数据分析时查阅
6. **第6章**（备用）- 遇到问题时查阅

### 快速问题解决

遇到问题时，直接跳转到第6章相应小节。

### 技术深入学习

按章节顺序阅读第2-3章，理解NatNet和LSL的技术细节。

---

## 📝 文档维护

### 版本历史

- **V3.3.1** (2025-10-17) - 当前版本


### 文档更新日志
- **2025-10-17** - 完成V3.3.1文档，添加所有章节内容

---

**开始阅读** → [第1章 项目架构与模块详解](01Chapter_ProjectFrame.md)

