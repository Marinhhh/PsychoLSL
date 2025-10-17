"""
空间导航与神经同步实验系统 - 统一启动器 (V3.0版)
启动不同实验阶段：认知地图建立(Phase 0)、神经同步测量(Phase 1)
支持子进程管理和资源统一调度
"""

import sys
import subprocess
import threading
import time
from pathlib import Path
from psychopy import gui

# 添加Scripts目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'Scripts'))

from Core.lsl_manager import LSLManager
from Core.transform_manager import TransformManager
from Core.audio_manager import AudioManager


class ExperimentLauncher:
    """实验启动器和管理器"""
    
    def __init__(self):
        # 初始化核心管理器
        self.lsl_manager = LSLManager()
        self.transform_manager = TransformManager()
        self.audio_manager = AudioManager()
        
        # 子进程管理
        self.lsl_recorder_process = None
        self.managers = {
            'lsl_manager': self.lsl_manager,
            'transform_manager': self.transform_manager,
            'audio_manager': self.audio_manager
        }
    
    def show_main_menu(self):
        """显示主菜单GUI"""
        print("=" * 70)
        print("空间导航与神经同步实验系统 (V3.0)")
        print("=" * 70)
        
        # GUI选择界面
        dlg = gui.Dlg(title='实验系统 V3.0 - 选择阶段')
        dlg.addText('请选择要运行的实验阶段：')
        dlg.addField('实验阶段:', choices=[
            'Phase 0 - 认知地图建立',
            'Phase 1 - 神经同步测量',
            #'工具 - LSL连接测试',
            #'工具 - LSL数据录制器',
            '退出系统'
        ])
        dlg.addField('是否启动LSL录制器 (后台):', True)
        
        result = dlg.show()
        
        if not dlg.OK:
            return None, False
        
        return result[0], result[1]
    
    def start_lsl_recorder_subprocess(self, dyad_id=None, session_id=None):
        """启动LSL录制器作为子进程（CLI模式，后台）"""
        try:
            print("\n🎬 启动LSL录制器（后台进程）...")
            
            # 构建命令
            recorder_script = Path(__file__).parent / 'Scripts' / 'Tools' / 'lsl_recorder.py'
            data_dir = Path(__file__).parent / 'Data'
            
            cmd = [
                sys.executable, 
                str(recorder_script), 
                '--cli',
                '--output-dir', str(data_dir),
                '--scan-timeout', '5.0',  # 增加扫描时间
                '--verbose'  # 详细输出
            ]
            
            # 如果提供了dyad_id和session_id，添加前缀
            if dyad_id and session_id:
                prefix = f"D{dyad_id:03d}_S{session_id}"
                cmd.extend(['--prefix', prefix])
            
            print(f"   命令: {' '.join(cmd)}")
            
            # 启动子进程（不捕获输出，让它显示在控制台）
            self.lsl_recorder_process = subprocess.Popen(
                cmd,
                cwd=str(Path(__file__).parent),
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            print(f"✅ LSL录制器已启动 (PID: {self.lsl_recorder_process.pid})")
            print("   录制器将在新窗口中显示输出")
            return True
            
        except Exception as e:
            print(f"❌ LSL录制器启动失败: {e}")
            return False
    
    def start_lsl_recorder_gui(self):
        """启动LSL录制器GUI（独立进程，非阻塞）"""
        try:
            print("\n🎬 启动LSL录制器GUI...")
            
            # 构建命令
            recorder_script = Path(__file__).parent / 'Scripts' / 'Tools' / 'lsl_recorder.py'
            cmd = [sys.executable, str(recorder_script), '--gui']
            
            # 启动子进程（独立窗口）
            self.lsl_recorder_process = subprocess.Popen(
                cmd,
                cwd=str(Path(__file__).parent),
                # Windows下创建新控制台窗口
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            
            print(f"✅ LSL录制器GUI已启动 (PID: {self.lsl_recorder_process.pid})")
            print("⏳ 等待3秒让GUI初始化...")
            time.sleep(3)  # 给GUI窗口启动时间
            
            return True
            
        except Exception as e:
            print(f"❌ LSL录制器GUI启动失败: {e}")
            print("⚠️  将继续运行实验（不影响主流程）")
            return False
    
    def stop_lsl_recorder_subprocess(self):
        """停止LSL录制器子进程"""
        try:
            if self.lsl_recorder_process:
                print("\n⏹️  停止LSL录制器...")
                self.lsl_recorder_process.terminate()
                
                # 等待进程结束
                try:
                    self.lsl_recorder_process.wait(timeout=5)
                    print("✅ LSL录制器已停止")
                except subprocess.TimeoutExpired:
                    print("⚠️  强制终止LSL录制器")
                    self.lsl_recorder_process.kill()
                
                self.lsl_recorder_process = None
            
        except Exception as e:
            print(f"❌ 停止LSL录制器错误: {e}")
    
    def run_map_phase(self):
        """运行认知地图建立阶段 (Phase 0)"""
        try:
            print("\n🚀 启动认知地图建立 (Phase 0)...")
            
            from Procedures.map_phase import MapLearningSystem
            
            # 创建系统实例（会弹出GUI收集被试信息）
            system = MapLearningSystem()
            
            # 在GUI填写完成后，启动LSL录制器GUI
            print("\n📊 启动LSL录制器GUI（用于监控数据流）...")
            self.start_lsl_recorder_gui()
            
            # 运行实验（会弹出PsychoPy窗口）
            print("💡 提示：按ESC键可随时退出程序")
            success = system.run()
            
            if success:
                print("✅ 认知地图建立完成")
            else:
                print("⚠️  认知地图建立未完成")
            
            return success
            
        except SystemExit:
            print("⚠️  程序被用户终止")
            return False
        except Exception as e:
            print(f"❌ 认知地图建立失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_navigation_phase(self):
        """运行神经同步测量阶段 (Phase 1)"""
        try:
            print("\n🚀 启动神经同步测量 (Phase 1)...")
            
            from Procedures.navigation_phase import NavigationSystem
            
            # 创建系统实例（会弹出GUI收集被试信息）
            system = NavigationSystem()
            
            # 在GUI填写完成后，启动LSL录制器GUI
            print("\n📊 启动LSL录制器GUI（用于监控数据流）...")
            self.start_lsl_recorder_gui()
            
            # 运行实验（会弹出PsychoPy窗口）
            print("💡 提示：按ESC键可随时退出程序")
            success = system.run()
            
            if success:
                print("✅ 神经同步测量完成")
            else:
                print("⚠️  神经同步测量未完成")
            
            return success
            
        except SystemExit:
            print("⚠️  程序被用户终止")
            return False
        except Exception as e:
            print(f"❌ 神经同步测量失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_lsl_connection_test(self):
        """运行LSL连接测试工具"""
        try:
            print("\n🔧 启动LSL连接测试...")
            
            from Tools.test_lsl_connection import LSLDiagnosticTool
            
            tool = LSLDiagnosticTool()
            tool.run_diagnostic()
            
            return True
            
        except Exception as e:
            print(f"❌ LSL连接测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_lsl_recorder_gui(self):
        """运行LSL录制器GUI"""
        try:
            print("\n🎬 启动LSL录制器GUI...")
            
            from Tools.lsl_recorder import LSLRecorderGUI
            
            gui = LSLRecorderGUI()
            gui.run()
            
            return True
            
        except Exception as e:
            print(f"❌ LSL录制器GUI启动失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def initialize_managers(self):
        """初始化核心管理器"""
        try:
            print("\n⚙️  正在初始化核心管理器...")
            
            # 初始化LSL管理器（如果需要的话）
            # 这里可以根据需要预初始化某些服务
            
            print("✅ 核心管理器初始化完成")
            return True
            
        except Exception as e:
            print(f"❌ 管理器初始化失败: {e}")
            return False
    
    def cleanup_managers(self):
        """清理核心管理器"""
        try:
            print("\n🧹 正在清理核心管理器...")
            
            # 清理LSL管理器
            self.lsl_manager.cleanup()
            
            # 清理音频管理器
            self.audio_manager.cleanup()
            
            print("✅ 核心管理器清理完成")
            
        except Exception as e:
            print(f"❌ 管理器清理错误: {e}")
    
    def run(self):
        """运行实验启动器主流程"""
        try:
            # 初始化管理器
            if not self.initialize_managers():
                return False
            
            while True:
                # 显示主菜单
                choice, start_recorder = self.show_main_menu()
                
                if choice is None or choice == '退出系统':
                    print("\n👋 退出实验系统")
                    break
                
                # 启动LSL录制器（如果选择）
                if start_recorder:
                    self.start_lsl_recorder_subprocess()
                
                try:
                    # 根据选择运行相应模块
                    if choice == 'Phase 0 - 认知地图建立':
                        self.run_map_phase()
                    
                    elif choice == 'Phase 1 - 神经同步测量':
                        self.run_navigation_phase()
                    
                    #elif choice == '工具 - LSL连接测试':
                    #    self.run_lsl_connection_test()
                    
                    #elif choice == '工具 - LSL数据录制器':
                    #    self.run_lsl_recorder_gui()
                    
                finally:
                    # 停止LSL录制器
                    if start_recorder:
                        self.stop_lsl_recorder_subprocess()
                
                # 询问是否继续
                continue_dlg = gui.Dlg(title='继续?')
                continue_dlg.addText('是否继续运行其他实验?')
                continue_dlg.addField('选择:', choices=['继续', '退出'])
                
                result = continue_dlg.show()
                if not continue_dlg.OK or result[0] == '退出':
                    break
            
            return True
            
        except Exception as e:
            print(f"❌ 实验启动器运行错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # 清理资源
            self.stop_lsl_recorder_subprocess()
            self.cleanup_managers()


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("空间导航与神经同步实验系统 V3.0")
    print("=" * 70)
    print("\n新特性:")
    print("• Phase 0: 认知地图建立（原Phase 1）")
    print("• Phase 1: 神经同步测量（原Phase 2）")
    print("• 固定线性映射，无需校准")
    print("• 支持NatNet骨骼数据和LSL Marker异步发送")
    print("• 鲁棒性位置处理")
    print("• 子进程LSL录制器")
    
    launcher = ExperimentLauncher()
    
    try:
        success = launcher.run()
        
        if success:
            print("\n🎉 系统运行完成")
        else:
            print("\n⚠️  系统运行中断")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  系统被用户中断")
    
    except Exception as e:
        print(f"\n❌ 系统运行错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n👋 感谢使用空间导航与神经同步实验系统！")


if __name__ == '__main__':
    main()