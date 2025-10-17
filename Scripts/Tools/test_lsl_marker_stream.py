"""
LSL Marker流测试工具
验证Navigation_Markers流是否能被发现和接收
"""

import sys
import time
from pathlib import Path

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pylsl import resolve_streams, StreamInlet
    print("✅ pylsl已导入")
except ImportError:
    print("❌ pylsl未安装")
    sys.exit(1)

from Core.lsl_manager import LSLManager


def test_marker_stream():
    """测试LSL Marker流"""
    print("\n" + "=" * 70)
    print("LSL Marker流测试工具")
    print("=" * 70)
    
    # 启动LSL管理器（会创建Navigation_Markers流）
    print("\n1️⃣  启动LSL管理器...")
    lsl_manager = LSLManager()
    
    if not lsl_manager.start_services():
        print("❌ LSL服务启动失败")
        return False
    
    print("✅ LSL服务已启动")
    
    # 等待流创建
    print("\n⏳ 等待3秒让流注册到LSL网络...")
    time.sleep(3)
    
    # 扫描LSL流
    print("\n2️⃣  扫描LSL数据流...")
    streams = resolve_streams(wait_time=5.0)
    
    if not streams:
        print("❌ 未发现任何LSL流")
        print("\n可能原因:")
        print("  - LSL Marker流创建失败（检查是否有错误信息）")
        print("  - pylsl版本不兼容")
        return False
    
    print(f"✅ 发现 {len(streams)} 个LSL流:")
    
    marker_stream = None
    for idx, stream in enumerate(streams):
        name = stream.name()
        stream_type = stream.type()
        channels = stream.channel_count()
        rate = stream.nominal_srate()
        
        print(f"  [{idx+1}] {name}")
        print(f"      类型: {stream_type}")
        print(f"      通道数: {channels}")
        print(f"      采样率: {rate} Hz")
        print(f"      Source ID: {stream.source_id()}")
        
        if name == 'Navigation_Markers':
            marker_stream = stream
            print(f"      ✅ 这是我们要找的Marker流！")
    
    if not marker_stream:
        print("\n⚠️  未找到'Navigation_Markers'流")
        print("可用的流:")
        for s in streams:
            print(f"  - {s.name()}")
        return False
    
    # 连接并接收数据
    print("\n3️⃣  连接到Navigation_Markers流并接收数据...")
    inlet = StreamInlet(marker_stream)
    
    print("   发送几个测试marker...")
    lsl_manager.send_marker(99, "测试marker 1")
    time.sleep(0.5)
    lsl_manager.send_marker(88, "测试marker 2")
    time.sleep(0.5)
    lsl_manager.send_marker(77, "测试marker 3")
    
    print("\n   接收marker（等待5秒）...")
    received_markers = []
    timeout = time.time() + 5.0
    
    while time.time() < timeout:
        sample, timestamp = inlet.pull_sample(timeout=0.1)
        if sample:
            marker_code = int(sample[0])
            received_markers.append((marker_code, timestamp))
            print(f"   ✅ 接收到marker: {marker_code} @ {timestamp:.3f}秒")
    
    # 结果
    print("\n" + "=" * 70)
    print("测试结果")
    print("=" * 70)
    
    if received_markers:
        print(f"✅ 成功接收 {len(received_markers)} 个marker")
        print(f"   LSL Marker流工作正常！")
        print(f"\n📊 LSL录制器应该能够录制这个流")
        return True
    else:
        print("❌ 未接收到任何marker")
        print("\n可能原因:")
        print("  - LSL Marker发送线程未运行")
        print("  - Marker队列有问题")
        print("  - pylsl版本兼容性问题")
        return False
    
    # 清理
    lsl_manager.cleanup()


if __name__ == '__main__':
    try:
        success = test_marker_stream()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

