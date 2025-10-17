"""
OptiTrack位置LSL流测试工具（V3.3新增）
验证NatNet→LSL位置广播功能是否正常工作
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


def test_optitrack_lsl_streams():
    """测试OptiTrack位置LSL流"""
    print("\n" + "=" * 70)
    print("OptiTrack位置LSL流测试工具")
    print("=" * 70)
    print("\n此工具验证NatNet数据是否能正确转发到LSL流")
    
    # 启动LSL管理器（启用位置广播）
    print("\n1️⃣  启动LSL管理器（启用位置广播）...")
    lsl_manager = LSLManager()
    
    if not lsl_manager.start_services(enable_position_broadcast=True, sub_ids=['001', '002']):
        print("❌ LSL服务启动失败")
        return False
    
    print("✅ LSL服务已启动")
    
    # 等待NatNet数据开始流动
    print("\n⏳ 等待5秒让NatNet连接稳定并开始接收数据...")
    time.sleep(5)
    
    # 扫描LSL流
    print("\n2️⃣  扫描LSL数据流...")
    streams = resolve_streams(wait_time=5.0)
    
    if not streams:
        print("❌ 未发现任何LSL流")
        return False
    
    print(f"✅ 发现 {len(streams)} 个LSL流:")
    
    marker_stream = None
    position_streams = []
    
    for idx, stream in enumerate(streams):
        name = stream.name()
        stream_type = stream.type()
        channels = stream.channel_count()
        rate = stream.nominal_srate()
        
        print(f"\n  [{idx+1}] {name}")
        print(f"      类型: {stream_type}")
        print(f"      通道数: {channels}")
        print(f"      采样率: {rate} Hz")
        print(f"      Source ID: {stream.source_id()}")
        
        if name == 'Navigation_Markers':
            marker_stream = stream
            print(f"      ✅ TTL Marker流")
        elif '_Position' in name:
            position_streams.append(stream)
            print(f"      ✅ OptiTrack位置流")
    
    # 验证流
    print("\n" + "=" * 70)
    print("流验证结果")
    print("=" * 70)
    
    print(f"\n📊 TTL Marker流: {'✅ 已发现' if marker_stream else '❌ 未发现'}")
    print(f"📊 OptiTrack位置流: {'✅ 已发现' if position_streams else '❌ 未发现'} ({len(position_streams)}个)")
    
    if position_streams:
        print(f"\n检测到的位置流:")
        for stream in position_streams:
            print(f"  - {stream.name()}")
    
    if not position_streams:
        print("\n⚠️  未检测到OptiTrack位置流！")
        print("可能原因:")
        print("  1. NatNet数据还未开始接收")
        print("  2. Motive中没有Sub001或Sub002的Markerset")
        print("  3. position_broadcast_enabled被禁用")
        
        # 检查缓存
        cached_names = list(lsl_manager.latest_skeleton_data.keys())
        print(f"\n当前NatNet缓存的对象: {cached_names}")
        
        return False
    
    # 测试接收位置数据
    print("\n3️⃣  连接到位置流并接收数据...")
    
    inlets = []
    for stream in position_streams:
        try:
            inlet = StreamInlet(stream)
            inlets.append((stream.name(), inlet))
            print(f"  ✅ 已连接: {stream.name()}")
        except Exception as e:
            print(f"  ❌ 连接失败 {stream.name()}: {e}")
    
    if not inlets:
        print("❌ 无法连接到任何位置流")
        return False
    
    print(f"\n📡 接收位置数据（持续10秒，移动Sub001/Sub002观察坐标变化）...")
    print("=" * 70)
    print(f"{'时间':<10} {'流名称':<20} {'X (米)':<12} {'Y (米)':<12} {'Z (米)':<12}")
    print("=" * 70)
    
    start_time = time.time()
    sample_counts = {name: 0 for name, _ in inlets}
    last_positions = {}
    
    while time.time() - start_time < 10.0:
        for stream_name, inlet in inlets:
            try:
                sample, timestamp = inlet.pull_sample(timeout=0.01)
                if sample and len(sample) >= 3:
                    sample_counts[stream_name] += 1
                    
                    x, y, z = sample[0], sample[1], sample[2]
                    
                    # 检查位置是否变化
                    if stream_name in last_positions:
                        last_x, last_y, last_z = last_positions[stream_name]
                        distance = ((x-last_x)**2 + (y-last_y)**2 + (z-last_z)**2)**0.5
                        if distance > 0.01:  # 移动超过1cm
                            print(f"{timestamp:10.3f} {stream_name:<20} {x:+11.3f} {y:+11.3f} {z:+11.3f} ⭐ 移动!")
                    else:
                        print(f"{timestamp:10.3f} {stream_name:<20} {x:+11.3f} {y:+11.3f} {z:+11.3f}")
                    
                    last_positions[stream_name] = (x, y, z)
                    
            except Exception as e:
                pass
        
        time.sleep(0.01)
    
    # 结果统计
    print("=" * 70)
    print("\n📊 接收统计:")
    total_samples = 0
    for stream_name, count in sample_counts.items():
        rate = count / 10.0  # 10秒
        print(f"  {stream_name}: {count} 样本 ({rate:.1f} Hz)")
        total_samples += count
    
    print(f"\n总样本数: {total_samples}")
    
    # 结论
    print("\n" + "=" * 70)
    print("测试结论")
    print("=" * 70)
    
    if total_samples > 0:
        print("\n✅ OptiTrack位置LSL流工作正常！")
        print(f"✅ LSL录制器应该能够录制这些流")
        print(f"\n建议:")
        print("  1. 运行LSL录制器GUI查看所有流")
        print("  2. 开始录制，运行实验")
        print("  3. 检查生成的XDF/CSV文件是否包含位置数据")
        return True
    else:
        print("\n❌ 未接收到任何位置数据")
        print("\n可能原因:")
        print("  1. NatNet未接收到Sub001/Sub002的数据")
        print("  2. Motive中对象名称不匹配")
        print("  3. 标记未被跟踪（红色状态）")
        return False
    
    # 清理
    lsl_manager.cleanup()


if __name__ == '__main__':
    try:
        success = test_optitrack_lsl_streams()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

