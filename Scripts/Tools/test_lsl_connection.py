"""
LSL连接诊断与几何对齐验证工具 (V3.0版)
实时验证NatNet连接和固定线性映射转换
"""

import sys
import time
from pathlib import Path

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from Core.lsl_manager import LSLManager
from Core.transform_manager import TransformManager
import logging


class LSLDiagnosticTool:
    """LSL连接诊断与几何对齐验证工具"""
    
    def __init__(self):
        self.logger = logging.getLogger('LSLDiagnosticTool')
        
        # 初始化管理器
        self.lsl_manager = LSLManager()
        self.transform_manager = TransformManager()
        
        # 诊断结果
        self.diagnostic_results = {}
    
    def scan_lsl_streams(self):
        """扫描LSL数据流"""
        print("\n🔍 扫描LSL数据流...")
        
        try:
            from pylsl import resolve_streams
            streams = resolve_streams(wait_time=3.0)
            
            if not streams:
                print("⚠️  未发现任何LSL数据流")
                return []
            
            print(f"✅ 发现 {len(streams)} 个数据流:")
            stream_info = []
            for idx, stream in enumerate(streams):
                info = {
                    'name': stream.name(),
                    'type': stream.type(),
                    'channel_count': stream.channel_count(),
                    'nominal_srate': stream.nominal_srate(),
                    'source_id': stream.source_id()
                }
                stream_info.append(info)
                print(f"  [{idx+1}] {info['name']} | Type: {info['type']} | "
                      f"Channels: {info['channel_count']} | Rate: {info['nominal_srate']}Hz")
            
            return stream_info
            
        except Exception as e:
            print(f"❌ LSL流扫描失败: {e}")
            return []
    
    def test_natnet_connection(self):
        """测试NatNet连接"""
        print("\n🔗 测试NatNet连接...")
        
        try:
            # 启动LSL/NatNet服务
            success = self.lsl_manager.start_services()
            
            if not success:
                print("❌ NatNet连接失败")
                return False
            
            # 等待连接稳定
            print("⏳ 等待连接稳定...")
            time.sleep(3)
            
            # 检查连接状态
            status = self.lsl_manager.is_connected()
            
            print(f"📊 连接状态:")
            print(f"   NatNet: {'✅ 已连接' if status['natnet'] else '❌ 未连接'}")
            print(f"   LSL Marker: {'✅ 可用' if status['lsl_marker'] else '❌ 不可用'}")
            print(f"   Degraded Mode: {'⚠️  是' if status['degraded_mode'] else '✅ 否'}")
            
            return status['natnet']
            
        except Exception as e:
            print(f"❌ NatNet连接测试失败: {e}")
            return False
    
    def test_data_reception(self):
        """测试数据接收"""
        print("\n📡 测试数据接收...")
        
        try:
            # 测试骨骼数据
            skeleton_names = ["Skeleton_1", "Skeleton_2"]
            skeleton_data_found = False
            
            for skeleton_name in skeleton_names:
                data = self.lsl_manager.get_latest_skeleton_data(skeleton_name)
                if data and data['valid']:
                    print(f"✅ 骨骼数据 ({skeleton_name}): X={data['x']:.3f}, Y={data['y']:.3f}, Z={data['z']:.3f}")
                    skeleton_data_found = True
                else:
                    print(f"⚠️  骨骼数据 ({skeleton_name}): 无数据")
            
            # 测试刚体数据
            rigid_body_names = ["RigidBody_1", "RigidBody_2"]
            rigid_body_data_found = False
            
            for rb_name in rigid_body_names:
                data = self.lsl_manager.get_latest_rigid_body(rb_name)
                if data and data['valid']:
                    print(f"✅ 刚体数据 ({rb_name}): X={data['x']:.3f}, Y={data['y']:.3f}, Z={data['z']:.3f}")
                    rigid_body_data_found = True
                else:
                    print(f"⚠️  刚体数据 ({rb_name}): 无数据")
            
            return skeleton_data_found or rigid_body_data_found
            
        except Exception as e:
            print(f"❌ 数据接收测试失败: {e}")
            return False
    
    def run_geometry_check(self):
        """运行几何对齐验证"""
        print("\n📐 运行几何对齐验证...")
        print("   请移动刚体/骨骼，观察坐标转换结果")
        print("   按 Ctrl+C 停止...")
        
        try:
            # 验证固定线性映射参数
            if not self.transform_manager.validate_transform():
                print("❌ 线性映射参数验证失败")
                return False
            
            print("\n实时坐标转换预览:")
            print("格式: X_real -> X_screen, Z_real -> Y_screen")
            print("-" * 50)
            
            frame_count = 0
            
            while True:
                try:
                    frame_count += 1
                    found_data = False
                    
                    # 检查骨骼数据
                    for i in range(1, 3):
                        skeleton_name = f"Skeleton_{i}"
                        data = self.lsl_manager.get_latest_skeleton_data(skeleton_name)
                        
                        if data and data['valid']:
                            x_real, z_real = data['x'], data['z']
                            x_screen, y_screen = self.transform_manager.real_to_screen(x_real, z_real)
                            
                            print(f"[{frame_count:04d}] {skeleton_name}: "
                                  f"{x_real:+6.3f} -> {x_screen:+7.1f}, "
                                  f"{z_real:+6.3f} -> {y_screen:+7.1f}")
                            
                            found_data = True
                    
                    # 如果没有骨骼数据，检查刚体数据
                    if not found_data:
                        for i in range(1, 3):
                            rb_name = f"RigidBody_{i}"
                            data = self.lsl_manager.get_latest_rigid_body(rb_name)
                            
                            if data and data['valid']:
                                x_real, z_real = data['x'], data['z']
                                x_screen, y_screen = self.transform_manager.real_to_screen(x_real, z_real)
                                
                                print(f"[{frame_count:04d}] {rb_name}: "
                                      f"{x_real:+6.3f} -> {x_screen:+7.1f}, "
                                      f"{z_real:+6.3f} -> {y_screen:+7.1f}")
                                
                                found_data = True
                    
                    if not found_data and frame_count % 60 == 0:  # 每秒提示一次
                        print(f"[{frame_count:04d}] ⏳ 等待数据...")
                    
                    time.sleep(1/60)  # ~60 FPS
                    
                except KeyboardInterrupt:
                    break
            
            print("\n✅ 几何对齐验证完成")
            return True
            
        except Exception as e:
            print(f"❌ 几何对齐验证失败: {e}")
            return False
    
    def test_lsl_marker_sending(self):
        """测试LSL Marker发送"""
        print("\n📡 测试LSL Marker发送...")
        
        try:
            # 发送测试标记
            test_markers = [1, 2, 3, 4, 5]
            
            for marker in test_markers:
                success = self.lsl_manager.send_marker(marker, f"测试标记_{marker}")
                if success:
                    print(f"✅ 标记 {marker} 发送成功")
                else:
                    print(f"❌ 标记 {marker} 发送失败")
                
                time.sleep(0.5)
            
            return True
            
        except Exception as e:
            print(f"❌ LSL Marker发送测试失败: {e}")
            return False
    
    def generate_diagnostic_report(self):
        """生成诊断报告"""
        print("\n📋 生成诊断报告...")
        
        try:
            # 获取统计信息
            stats = self.lsl_manager.get_stats()
            
            print(f"\n📊 系统状态报告:")
            print(f"=" * 50)
            
            # NatNet状态
            natnet_stats = stats.get('natnet', {})
            print(f"NatNet连接: {'✅ 正常' if natnet_stats.get('connected', False) else '❌ 异常'}")
            print(f"帧率: {natnet_stats.get('fps', 0):.1f} FPS")
            print(f"总帧数: {natnet_stats.get('total_frames', 0)}")
            print(f"骨骼对象: {natnet_stats.get('skeleton_count', 0)} 个")
            print(f"刚体对象: {natnet_stats.get('rigid_body_count', 0)} 个")
            
            # LSL Marker状态
            marker_stats = stats.get('lsl_marker', {})
            print(f"LSL Marker: {'✅ 可用' if marker_stats.get('available', False) else '❌ 不可用'}")
            print(f"Degraded Mode: {'⚠️  是' if marker_stats.get('degraded_mode', False) else '✅ 否'}")
            print(f"队列大小: {marker_stats.get('queue_size', 0)}")
            
            # 线性映射参数
            print(f"\n📐 固定线性映射参数:")
            print(f"缩放因子: {self.transform_manager.scale_factor} 像素/米")
            print(f"Z轴翻转: {self.transform_manager.z_flip}")
            print(f"世界范围: ±{self.transform_manager.world_range/2:.1f} 米")
            print(f"屏幕范围: ±{self.transform_manager.screen_range/2:.0f} 像素")
            
            print(f"=" * 50)
            
            return True
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            return False
    
    def run_diagnostic(self):
        """运行完整诊断流程"""
        try:
            print("\n" + "=" * 60)
            print("LSL连接诊断与几何对齐验证工具 V3.0")
            print("=" * 60)
            
            # 1. 扫描LSL流
            self.scan_lsl_streams()
            
            # 2. 测试NatNet连接
            natnet_ok = self.test_natnet_connection()
            
            if natnet_ok:
                # 3. 测试数据接收
                data_ok = self.test_data_reception()
                
                if data_ok:
                    # 4. 测试LSL Marker发送
                    self.test_lsl_marker_sending()
                    
                    # 5. 几何对齐验证
                    print("\n准备运行几何对齐验证...")
                    input("按回车键开始实时坐标转换预览...")
                    self.run_geometry_check()
                
                # 6. 生成诊断报告
                self.generate_diagnostic_report()
            
            print("\n🎉 诊断完成！")
            return True
            
        except Exception as e:
            print(f"❌ 诊断过程失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # 清理资源
            self.lsl_manager.cleanup()
    
    def cleanup(self):
        """清理资源"""
        try:
            self.lsl_manager.cleanup()
        except Exception as e:
            print(f"❌ 资源清理错误: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("LSL连接诊断与几何对齐验证工具")
    print("=" * 60)
    
    tool = LSLDiagnosticTool()
    
    try:
        success = tool.run_diagnostic()
        
        if success:
            print("\n✅ 诊断成功完成")
        else:
            print("\n⚠️  诊断未完成")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  诊断被用户中断")
        tool.cleanup()
    
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        tool.cleanup()


if __name__ == '__main__':
    main()