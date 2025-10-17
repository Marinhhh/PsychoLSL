"""
NatNet到PsychoPy数据流测试工具
实时显示Motive坐标和PsychoPy坐标，验证数据提取和转换
"""

import sys
import time
from pathlib import Path
from psychopy import visual, core, event

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from Core.lsl_manager import LSLManager
from Core.transform_manager import TransformManager


class NatNetToPsychopyTest:
    """NatNet到PsychoPy数据流测试"""
    
    def __init__(self):
        print("\n" + "=" * 70)
        print("NatNet到PsychoPy数据流测试工具")
        print("=" * 70)
        
        # 初始化管理器
        self.lsl_manager = LSLManager()
        self.transform_manager = TransformManager()
        
        # PsychoPy窗口
        self.win = None
        self.dot = None
        self.motive_text_stim = None
        self.psychopy_text_stim = None
        self.status_text_stim = None
        self.no_data_text_stim = None
        
        # 测试参数
        self.sub_id = "002"  # 默认测试Sub001（如果Sub001是Skeleton类型请改为Markerset）
    
    def setup(self):
        """初始化设置"""
        try:
            # 启动LSL/NatNet服务（启用位置广播）
            print("\n🚀 启动LSL/NatNet服务...")
            if not self.lsl_manager.start_services(enable_position_broadcast=True, sub_ids=['001', '002']):
                print("❌ LSL/NatNet服务启动失败")
                return False
            
            # 等待连接稳定并接收数据
            print("⏳ 等待5秒，让NatNet连接稳定并开始接收数据...")
            time.sleep(5)
            
            # 验证连接
            status = self.lsl_manager.is_connected()
            print(f"\n📊 连接状态:")
            print(f"   NatNet: {'✅ 已连接' if status['natnet'] else '❌ 未连接'}")
            print(f"   LSL Marker: {'✅ 可用' if status['lsl_marker'] else '❌ 不可用'}")
            
            if not status['natnet']:
                print("❌ NatNet未连接，无法继续")
                return False
            
            # 创建PsychoPy窗口
            print("\n🖥️  创建PsychoPy窗口...")
            self.win = visual.Window(
                size=(1920, 1080),
                units='pix',
                fullscr=True,
                color=[0, 0, 0],
                allowGUI=True,
                waitBlanking=True
            )
            self.win.mouseVisible = False
            
            # 创建光点
            self.dot = visual.Circle(
                self.win,
                radius=20,
                fillColor=[1, 1, 1],  # 白色
                lineColor=[1, 1, 1],
                lineWidth=2,
                pos=(0, 0)
            )
            
            # 创建场景元素（一次性创建，避免每帧重新创建）
            self.border = visual.Rect(
                self.win,
                width=1080,
                height=1080,
                lineColor=[0.5, 0.5, 0.5],
                lineWidth=3,
                fillColor=None
            )
            
            self.center_h = visual.Line(
                self.win,
                start=(-50, 0),
                end=(50, 0),
                lineColor=[0.3, 0.3, 0.3],
                lineWidth=1
            )
            
            self.center_v = visual.Line(
                self.win,
                start=(0, -50),
                end=(0, 50),
                lineColor=[0.3, 0.3, 0.3],
                lineWidth=1
            )
            
            # 创建文本对象（一次性创建，后续只更新内容）
            self.motive_text_stim = visual.TextStim(
                self.win,
                text="",
                color=[0, 1, 1],  # 青色
                height=25,
                pos=(-700, 400),
                alignText='left',
                anchorHoriz='left'
            )
            
            self.psychopy_text_stim = visual.TextStim(
                self.win,
                text="",
                color=[1, 1, 0],  # 黄色
                height=25,
                pos=(700, 400),
                alignText='right',
                anchorHoriz='right'
            )
            
            self.status_text_stim = visual.TextStim(
                self.win,
                text="",
                color=[1, 1, 1],
                height=20,
                pos=(0, -450)
            )
            
            self.no_data_text_stim = visual.TextStim(
                self.win,
                text="⏳ 等待Markerset数据...\n\n"
                     "请确保：\n"
                     "1. Motive正在录制\n"
                     "2. Markerset Sub001已创建\n"
                     "3. 标记正在被跟踪（绿色状态）",
                color=[1, 0.5, 0],  # 橙色
                height=30,
                pos=(0, 0)
            )
            
            print("✅ 设置完成")
            return True
            
        except Exception as e:
            print(f"❌ 设置失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_test(self):
        """运行实时测试"""
        try:
            print("\n📡 开始实时数据流测试...")
            print("=" * 70)
            print("说明：")
            print("  - 窗口中将显示Motive坐标和PsychoPy坐标")
            print("  - 白色光点将跟踪Sub001的Markerset质心位置")
            print("  - 按ESC键退出")
            print("=" * 70)
            
            # 检查是否已有数据缓存
            print("\n🔍 检查数据缓存...")
            cached_names = list(self.lsl_manager.latest_skeleton_data.keys())
            print(f"   当前缓存的骨骼名称: {cached_names}")
            
            if not cached_names:
                print("⚠️  警告：当前没有缓存数据，再等待2秒...")
                time.sleep(2)
                cached_names = list(self.lsl_manager.latest_skeleton_data.keys())
                print(f"   重新检查缓存: {cached_names}")
            
            print("\n开始实时更新...")
            
            frame_count = 0
            
            while True:
                frame_count += 1
                
                # 尝试获取Sub001的Markerset数据
                skeleton_names = [
                    f"Sub{self.sub_id}",  # Sub001
                    f"Skeleton_{int(self.sub_id)}",  # Skeleton_1
                    f"Skeleton_{self.sub_id}"  # Skeleton_001
                ]
                
                skeleton_data = None
                found_name = None
                for skeleton_name in skeleton_names:
                    skeleton_data = self.lsl_manager.get_latest_skeleton_data(skeleton_name)
                    
                    # 调试：首次或每100帧打印一次查找结果
                    if frame_count == 1 or frame_count % 100 == 0:
                        if skeleton_data:
                            print(f"[调试] 尝试'{skeleton_name}': 获取到数据 valid={skeleton_data.get('valid', False)}")
                        else:
                            print(f"[调试] 尝试'{skeleton_name}': 无数据")
                    
                    if skeleton_data and skeleton_data['valid']:
                        found_name = skeleton_name
                        break
                
                # 调试：显示缓存的所有骨骼名称
                if frame_count == 1 or frame_count % 100 == 0:
                    cached_names = list(self.lsl_manager.latest_skeleton_data.keys())
                    print(f"[调试] LSLManager缓存的骨骼名称: {cached_names}")
                
                if skeleton_data and skeleton_data['valid']:
                    # 提取Motive坐标
                    x_real = skeleton_data['x']
                    y_real = skeleton_data['y']  # Y是Up-axis
                    z_real = skeleton_data['z']
                    
                    # 转换为PsychoPy坐标
                    x_screen, y_screen = self.transform_manager.real_to_screen(x_real, z_real)
                    
                    # 限制在场景范围内
                    x_screen = max(-960, min(960, x_screen))
                    y_screen = max(-540, min(540, y_screen))
                    
                    # 更新光点位置
                    self.dot.pos = (x_screen, y_screen)
                    
                    # 更新Motive坐标文本
                    motive_text = f"Motive坐标 (世界坐标):\n"
                    motive_text += f"X = {x_real:+7.3f} 米\n"
                    motive_text += f"Y = {y_real:+7.3f} 米 (Up-axis)\n"
                    motive_text += f"Z = {z_real:+7.3f} 米\n"
                    motive_text += f"数据来源: {found_name}"
                    self.motive_text_stim.text = motive_text
                    
                    # 更新PsychoPy坐标文本
                    psychopy_text = f"PsychoPy坐标 (屏幕像素):\n"
                    psychopy_text += f"X = {x_screen:+7.1f} 像素\n"
                    psychopy_text += f"Y = {y_screen:+7.1f} 像素\n"
                    psychopy_text += f"映射: Z→Y × 180.0 × (-1)"
                    self.psychopy_text_stim.text = psychopy_text
                    
                    # 绘制场景
                    self.border.draw()
                    self.center_h.draw()
                    self.center_v.draw()
                    
                    # 光点
                    self.dot.draw()
                    
                    # 文本
                    self.motive_text_stim.draw()
                    self.psychopy_text_stim.draw()
                    
                    # 状态文本（底部）
                    status_text = f"帧数: {frame_count} | 按ESC退出"
                    self.status_text_stim.text = status_text
                    self.status_text_stim.draw()
                    
                    # 每30帧打印一次到终端
                    if frame_count % 30 == 0:
                        print(f"[测试] 帧{frame_count}: Motive({x_real:+.3f}, {y_real:+.3f}, {z_real:+.3f}) -> PsychoPy({x_screen:+.1f}, {y_screen:+.1f})")
                    
                else:
                    # 没有数据 - 显示等待提示
                    self.no_data_text_stim.draw()
                    
                    # 每60帧打印一次警告
                    if frame_count % 60 == 0:
                        print(f"[测试] ⚠️ 未获取到Sub001数据，已尝试: {skeleton_names}")
                
                # 刷新窗口
                self.win.flip()
                
                # 检查退出
                keys = event.getKeys(['escape'])
                if 'escape' in keys:
                    print("\n⚠️  用户按ESC退出")
                    break
                
                # 控制帧率（降低到30 FPS以减少卡顿）
                time.sleep(1/30)  # 30 FPS
            
            print("\n✅ 测试完成")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """清理资源"""
        try:
            print("\n🧹 正在清理资源...")
            
            if self.win:
                self.win.close()
            
            self.lsl_manager.cleanup()
            
            print("✅ 资源清理完成")
            
        except Exception as e:
            print(f"❌ 清理错误: {e}")


def main():
    """主函数"""
    test = NatNetToPsychopyTest()
    
    try:
        if not test.setup():
            print("\n❌ 设置失败")
            return
        
        test.run_test()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()


if __name__ == '__main__':
    print("=" * 80)
    print("NatNet到PsychoPy数据流测试工具 - 启动中...")
    print("=" * 80)
    import sys
    sys.stdout.flush()  # 强制刷新输出
    main()

