"""
认知地图建立脚本 (V3.0版)
Phase 0: 参与者A和B分别学习空间布局和隐藏目标位置
使用固定线性映射，无需校准
支持单人骨骼跟踪，鲁棒性处理数据丢失
"""

import sys
from pathlib import Path

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from psychopy import visual, core, event, gui
from Core.lsl_manager import LSLManager
from Core.transform_manager import TransformManager
from Core.audio_manager import AudioManager
from Utils.data_logger import DataLogger
import json
import random
import time
from datetime import datetime
import logging
from pathlib import Path

# ========== 路径配置常量 ==========
BEHAVIOR_DIR = str(Path(__file__).parent.parent.parent / 'Data' / 'Behavior')
LOGS_DIR = str(Path(__file__).parent.parent.parent / 'Logs')

# 配置日志
log_dir = Path(LOGS_DIR)
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f'MapPhase_{datetime.now().strftime("%Y%m%d-%H%M")}.log'),
        logging.StreamHandler()
    ]
)


class MapLearningSystem:
    """认知地图学习系统 (Phase 0)"""
    
    def __init__(self):
        self.logger = logging.getLogger('MapLearningSystem')
        
        # 实验信息
        self.dyad_id = None
        self.session_id = None
        self.sub_id = None
        self.sub_role = None  # 'A' or 'B'
        self.sub_name = None
        self.trial_num = 20  # 默认试次数
        
        # 初始化模块
        self.lsl_manager = LSLManager()
        self.transform_manager = TransformManager()
        self.audio_manager = AudioManager()
        self.data_logger = None
        
        # 窗口配置
        self.win = None
        self.window_size = (1920, 1080)  # 全屏分辨率
        self.scene_size = (1080, 1080)   # 场景正方形区域
        
        # 标记和目标
        self.wall_markers = {}
        self.hidden_targets = {}
        
        # 可视化对象
        self.marker_stims = {}
        self.target_stims = {}
        self.participant_dot = None
        
        # 实验时钟
        self.exp_clock = None
        
        # 鲁棒性处理
        self.last_valid_position = None
        self.position_lost_time = None
        self.max_position_loss = 2.0  # 最大位置丢失时间（秒）
    
    def collect_info(self):
        """收集实验信息（单人GUI）"""
        print("\n" + "=" * 60)
        print("认知地图建立 (Phase 0) - 收集实验信息")
        print("=" * 60)
        
        # GUI对话框
        dlg = gui.Dlg(title='认知地图建立 - Phase 0')
        dlg.addField('Dyad ID (数字):', 1)
        dlg.addField('Session (1/2):', choices=['1', '2'])
        dlg.addField('参与者ID (数字):', 1)
        dlg.addField('参与者角色 (A/B):', choices=['A', 'B'])
        dlg.addField('参与者姓名:', '')
        dlg.addField('参与者性别:', choices=['男', '女'])
        dlg.addField('参与者年龄:', 25)
        dlg.addField('试次数量:', 20)
        
        info = dlg.show()
        
        if not dlg.OK:
            print("❌ 用户取消")
            return False
        
        # 保存信息
        self.dyad_id = int(info[0])
        self.session_id = int(info[1])
        self.sub_id = f"{int(info[2]):03d}"
        self.sub_role = info[3]
        self.sub_name = info[4]
        self.trial_num = int(info[7])
        
        print(f"\n✅ 实验信息:")
        print(f"   Dyad ID: D{self.dyad_id:03d}")
        print(f"   Session: S{self.session_id}")
        print(f"   参与者: {self.sub_id} ({self.sub_role}) - {self.sub_name}")
        print(f"   性别: {info[5]}, 年龄: {info[6]}")
        print(f"   试次数: {self.trial_num}")
        
        return True
    
    def setup(self):
        """初始化设置"""
        print("\n" + "=" * 60)
        print("初始化系统")
        print("=" * 60)
        
        # 启动LSL/NatNet服务（启用OptiTrack位置LSL广播）
        print("\n🚀 启动LSL/NatNet服务...")
        if not self.lsl_manager.start_services(enable_position_broadcast=True, sub_ids=['001', '002']):
            print("❌ LSL/NatNet服务启动失败")
            return False
        
        # 启动OptiTrack数据保存
        print("\n💾 启动OptiTrack数据保存...")
        if not self.lsl_manager.start_optitrack_data_saving(self.dyad_id, self.session_id):
            print("⚠️  OptiTrack数据保存启动失败，但继续运行")
        
        # 验证固定线性映射
        print("\n📐 验证固定线性映射...")
        if not self.transform_manager.validate_transform():
            print("❌ 线性映射验证失败")
            return False
        
        # 加载或生成场景布局
        print(f"\n🗺️  加载场景布局...")
        if not self.transform_manager.load_scene_layout(self.dyad_id, self.session_id):
            print("❌ 场景布局加载失败")
            return False
        
        # 获取场景数据
        self.wall_markers = self.transform_manager.wall_markers
        self.hidden_targets = self.transform_manager.hidden_targets
        
        # 初始化数据记录器
        print(f"\n📊 初始化数据记录器...")
        self.data_logger = DataLogger(self.lsl_manager)
        if not self.data_logger.create_session(self.dyad_id, self.session_id, 
                                              sub_a_id=self.sub_id if self.sub_role == 'A' else None,
                                              sub_b_id=self.sub_id if self.sub_role == 'B' else None):
            print("❌ 数据记录器初始化失败")
            return False
        
        # 加载音频
        print(f"\n🔊 加载音频文件...")
        if not self.audio_manager.load_all_audios():
            print("⚠️  音频加载失败，但继续运行")
        
        # 创建PsychoPy窗口
        print(f"\n🖥️  创建显示窗口...")
        self.win = visual.Window(
            size=self.window_size,
            units='pix',
            fullscr=False,
            color=[0, 0, 0],
            allowGUI=False,
            waitBlanking=True,
            useFBO=True
        )
        
        # 预创建场景元素（性能优化：避免每帧创建）
        self.scene_border = visual.Rect(
            self.win,
            width=1080,
            height=1080,
            lineColor=[0.5, 0.5, 0.5],
            lineWidth=3,
            fillColor=None
        )
        
        # 隐藏鼠标指针
        self.win.mouseVisible = False
        
        # 创建实验时钟
        self.exp_clock = core.Clock()
        
        # 创建可视化对象
        self.create_visual_objects()
        
        print("✅ 系统初始化完成")
        return True
    
    def create_visual_objects(self):
        """创建可视化对象"""
        try:
            # 创建参与者光点（单人模拟人）
            self.participant_dot = visual.Circle(
                self.win,
                radius=20,
                fillColor='#FF69B4',  # 亮粉色
                lineColor=[0, 0, 0],
                lineWidth=2,
                pos=(0, 0)
            )
            
            # 创建墙面标记
            for marker_id, marker_data in self.wall_markers.items():
                screen_pos = marker_data['screen_pos']
                color = marker_data['color']
                
                marker_circle = visual.Circle(
                    self.win,
                    radius=12,
                    fillColor=color,
                    lineColor=[1, 1, 1],
                    lineWidth=2,
                    pos=screen_pos
                )
                
                marker_text = visual.TextStim(
                    self.win,
                    text=marker_id,
                    color=[1, 1, 1],
                    height=20,
                    pos=(screen_pos[0], screen_pos[1] - 25)
                )
                
                self.marker_stims[marker_id] = {
                    'circle': marker_circle,
                    'text': marker_text,
                    'data': marker_data
                }
            
            # 创建隐藏目标区域（可见圆圈）
            for target_id, target_data in self.hidden_targets.items():
                screen_pos = target_data['screen_center']
                screen_radius = target_data['screen_radius']
                
                # 创建目标圆圈
                target_circle = visual.Circle(
                    self.win,
                    radius=screen_radius,
                    fillColor=None,
                    lineColor=[1, 1, 1],  # 灰色边框
                    lineWidth=3,
                    pos=screen_pos
                )
                
                # 创建目标标签
                target_text = visual.TextStim(
                    self.win,
                    text=target_id,
                    color=[0.7, 0.7, 0.7],
                    height=25,
                    pos=screen_pos
                )
                
                self.target_stims[target_id] = {
                    'circle': target_circle,
                    'text': target_text,
                    'data': target_data,
                    'status': 'normal'  # normal, searching, found
                }
            
            print(f"✅ 可视化对象已创建: {len(self.marker_stims)}个标记, {len(self.target_stims)}个目标")
            
        except Exception as e:
            self.logger.error(f"创建可视化对象错误: {e}")
            print(f"❌ 创建可视化对象失败: {e}")
    
    def update_participant_position(self):
        """更新参与者位置（鲁棒性处理）"""
        try:
            # 获取骨骼数据（支持多种命名格式）
            skeleton_names = [
                f"Sub{self.sub_id}",  # Sub001格式
                f"Skeleton_{self.dyad_id}",  # Skeleton_1格式
                f"Skeleton_{int(self.sub_id)}"  # Skeleton_1格式（从sub_id转换）
            ]
            
            skeleton_data = None
            for skeleton_name in skeleton_names:
                skeleton_data = self.lsl_manager.get_latest_skeleton_data(skeleton_name)
                if skeleton_data and skeleton_data['valid']:
                    break
            
            current_time = time.time()
            
            if skeleton_data and skeleton_data['valid']:
                # 有效数据：更新位置
                x_real, z_real = skeleton_data['x'], skeleton_data['z']
                x_screen, y_screen = self.transform_manager.real_to_screen(x_real, z_real)
                
                # 限制在场景范围内
                x_screen = max(-540, min(540, x_screen))
                y_screen = max(-540, min(540, y_screen))
                
                # 更新光点位置
                self.participant_dot.pos = (x_screen, y_screen)
                
                # 保存有效位置
                self.last_valid_position = {
                    'x_real': x_real,
                    'z_real': z_real,
                    'x_screen': x_screen,
                    'y_screen': y_screen,
                    'timestamp': current_time
                }
                self.position_lost_time = None
                
                # 记录位置数据
                self.data_logger.log_position({
                    'sub_id': self.sub_id,
                    'sub_role': self.sub_role,
                    'phase': 0,
                    'session': self.session_id,
                    'block': 1,
                    'is_navigation': 1,  # Phase 0时恒为1
                    'raw_x': x_real,
                    'raw_y': z_real,
                    'pos_x': x_screen,
                    'pos_y': y_screen
                })
                
                return True
                
            else:
                # 无效数据：鲁棒性处理
                if self.position_lost_time is None:
                    self.position_lost_time = current_time
                
                # 检查是否超过最大丢失时间
                if current_time - self.position_lost_time > self.max_position_loss:
                    # 长时间丢失：光点保持静止在最后有效位置
                    if self.last_valid_position:
                        self.participant_dot.pos = (
                            self.last_valid_position['x_screen'],
                            self.last_valid_position['y_screen']
                        )
                
                return False
                
        except Exception as e:
            self.logger.error(f"更新参与者位置错误: {e}")
            return False
    
    def draw_scene(self, highlight_marker=None, highlight_target=None):
        """绘制场景"""
        try:
            # 绘制边框（使用预创建的对象）
            if hasattr(self, 'scene_border'):
                self.scene_border.draw()
            
            # 绘制墙面标记
            for marker_id, marker_stim in self.marker_stims.items():
                if marker_id == highlight_marker:
                    # 高亮显示
                    marker_stim['circle'].fillColor = '#00FFFF'  # 青色高亮
                else:
                    # 正常颜色
                    marker_stim['circle'].fillColor = marker_stim['data']['color']
                
                marker_stim['circle'].draw()
                marker_stim['text'].draw()
            
            # 绘制隐藏目标区域
            for target_id, target_stim in self.target_stims.items():
                if target_id == highlight_target:
                    if target_stim['status'] == 'found':
                        # 找到时：绿色高亮
                        target_stim['circle'].lineColor = [0, 1, 0]  # 绿色边框
                        target_stim['circle'].fillColor = [0, 1, 0, 0.3]  # 半透明绿色填充
                        target_stim['text'].color = [0, 1, 0]
                    else:
                        # 搜索时：黄色高亮
                        target_stim['circle'].lineColor = [1, 1, 0]  # 黄色边框
                        target_stim['circle'].fillColor = [1, 1, 0, 0.2]  # 半透明黄色填充
                        target_stim['text'].color = [1, 1, 0]
                else:
                    # 正常状态：灰色
                    target_stim['circle'].lineColor = [0.5, 0.5, 0.5]
                    target_stim['circle'].fillColor = None
                    target_stim['text'].color = [0.7, 0.7, 0.7]
                
                target_stim['circle'].draw()
                target_stim['text'].draw()
            
            # 绘制参与者光点
            if self.participant_dot:
                self.participant_dot.draw()
            
            # 绘制信息文本
            info_text = visual.TextStim(
                self.win,
                text=f"Phase 0 - 认知地图学习\n参与者: {self.sub_id} ({self.sub_role})",
                color=[1, 1, 1],
                height=25,
                pos=(0, 450)
            )
            info_text.draw()
            
        except Exception as e:
            self.logger.error(f"绘制场景错误: {e}")
    
    def run_learning_phase(self):
        """运行学习阶段"""
        print(f"\n" + "=" * 60)
        print(f"开始学习阶段 - 参与者{self.sub_role}")
        print("=" * 60)
        
        # 播放开始提示
        self.audio_manager.play_common('begin')
        
        # 发送LSL Marker
        self.data_logger.log_marker(1, "Trial开始", phase="0")
        
        # 获取墙面标记和隐藏目标列表
        wall_marker_list = list(self.wall_markers.keys())
        target_list = list(self.hidden_targets.keys())
        
        # 随机化顺序
        random.shuffle(wall_marker_list)
        random.shuffle(target_list)
        
        for trial in range(1, self.trial_num + 1):
            print(f"\n--- Trial {trial}/{self.trial_num} ---")
            
            # 选择墙面标记和隐藏目标
            wall_marker = wall_marker_list[(trial - 1) % len(wall_marker_list)]
            hidden_target = target_list[(trial - 1) % len(target_list)]
            
            trial_success = self.run_trial(trial, wall_marker, hidden_target)
            
            if not trial_success:
                print(f"⚠️  Trial {trial} 未完成")
            
            # Trial间隔
            time.sleep(3.0)
        
        # 播放结束提示
        self.audio_manager.play_common('end')
        
        # 发送结束标记
        self.data_logger.log_marker(5, "Block结束", phase="0")
        
        print(f"\n✅ 参与者{self.sub_role} 学习完成")
    
    def run_trial(self, trial_num, wall_marker, hidden_target):
        """运行单个试次"""
        try:
            print(f"   墙面标记: {wall_marker}")
            print(f"   隐藏目标: {hidden_target}")
            
            trial_start_time = self.exp_clock.getTime()
            
            # 记录Trial数据
            trial_data = {
                'sub_id': self.sub_id,
                'sub_role': self.sub_role,
                'phase': 0,
                'session': self.session_id,
                'block': 1,
                'is_navigation': 1,
                'trial': trial_num,
                'wall_marker': wall_marker,
                'target': hidden_target
            }
            
            # 记录任务开始时间
            trial_data['Time_Wall_go'] = trial_start_time  # 开始前往墙标的时间
            
            # 第一阶段：导航到墙面标记
            marker_success = self.navigate_to_wall_marker(wall_marker, trial_num)
            if marker_success:
                trial_data['Time_Wall_arrive'] = self.exp_clock.getTime()  # 修正字段名
                trial_data['RT_WallMarker'] = trial_data['Time_Wall_arrive'] - trial_start_time  # 修正字段名
            
            # 记录开始搜索目标的时间
            if marker_success:
                trial_data['Time_Target_go'] = self.exp_clock.getTime()  # 开始寻找目标的时间
                trial_data['Target_position'] = f"{self.hidden_targets[hidden_target]['real_pos'][0]:.3f},{self.hidden_targets[hidden_target]['real_pos'][1]:.3f}"  # 目标位置
            
            # 第二阶段：搜索隐藏目标
            target_success = self.search_hidden_target(hidden_target, trial_num)
            if target_success:
                trial_data['Time_Target_arrive'] = self.exp_clock.getTime()  # 修正字段名
                trial_data['RT_Target'] = trial_data['Time_Target_arrive'] - trial_data.get('Time_Target_go', trial_start_time)  # 修正字段名
            
            # 记录行为数据
            self.data_logger.log_behavior(trial_data)
            
            success = marker_success and target_success
            print(f"   结果: {'成功' if success else '失败'}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Trial {trial_num} 执行错误: {e}")
            return False
    
    def navigate_to_wall_marker(self, marker_id, trial_num):
        """导航到墙面标记"""
        print(f"   → 前往墙面标记: {marker_id}")
        
        # 播放音频
        self.audio_manager.play_wallmarker_go(marker_id)
        
        # 获取标记信息
        marker_data = self.wall_markers[marker_id]
        marker_pos = marker_data['real_pos']
        
        # 等待到达
        arrived = False
        timeout = 30.0
        start_time = time.time()
        
        while not arrived and (time.time() - start_time < timeout):
            # 更新参与者位置
            position_valid = self.update_participant_position()
            
            if position_valid and self.last_valid_position:
                # 检测是否到达标记
                current_pos = (self.last_valid_position['x_real'], self.last_valid_position['z_real'])
                if self.transform_manager.check_point_near_marker(current_pos, marker_id, threshold=1.0):
                    arrived = True
                    print(f"   ✅ 到达墙面标记: {marker_id}")
                    
                    # 播放到达音频
                    self.audio_manager.play_wallmarker_arrive(marker_id)
                    
                    # 发送LSL Marker
                    self.data_logger.log_marker(2, "到达墙面标记", trial=str(trial_num), phase="0")
            
            # 绘制场景
            self.draw_scene(highlight_marker=marker_id)
            self.win.flip()
            
            # 检查ESC退出
            keys = event.getKeys(['escape'])
            if 'escape' in keys:
                print("\n⚠️  用户按ESC键，立即退出程序...")
                self.cleanup()
                import sys
                sys.exit(0)
        
        if not arrived:
            print(f"   ⏱️  超时，未到达墙面标记")
        
        return arrived
    
    def search_hidden_target(self, target_id, trial_num):
        """搜索隐藏目标"""
        print(f"   → 搜索隐藏目标: {target_id}")
        
        # 设置目标状态为搜索中
        if target_id in self.target_stims:
            self.target_stims[target_id]['status'] = 'searching'
        
        # 播放音频
        self.audio_manager.play_target_go(target_id)
        
        # 获取目标信息
        target_data = self.hidden_targets[target_id]
        target_center = target_data['center']
        target_radius = target_data['radius']
        
        # 等待找到
        found = False
        timeout = 45.0
        start_time = time.time()
        
        while not found and (time.time() - start_time < timeout):
            # 更新参与者位置
            position_valid = self.update_participant_position()
            
            if position_valid and self.last_valid_position:
                # 检测是否进入目标区域
                current_pos = (self.last_valid_position['x_real'], self.last_valid_position['z_real'])
                if self.transform_manager.check_point_in_circle(current_pos, target_center, target_radius):
                    found = True
                    
                    # 更新目标状态为已找到
                    if target_id in self.target_stims:
                        self.target_stims[target_id]['status'] = 'found'
                    
                    print(f"   ✅ 找到隐藏目标: {target_id} - 目标区域高亮为绿色！")
                    
                    # 播放找到音频
                    self.audio_manager.play_target_arrive(target_id)
                    
                    # 发送LSL Marker
                    self.data_logger.log_marker(4, "找到隐藏目标", trial=str(trial_num), phase="0")
                    
                    # 等待2秒后再继续下一个指令（给予反应时间）
                    print(f"   ⏳ 等待2秒后继续...")
                    time.sleep(2.0)
            
            # 绘制场景（高亮当前搜索的目标）
            self.draw_scene(highlight_target=target_id)
            self.win.flip()
            
            # 检查ESC退出
            keys = event.getKeys(['escape'])
            if 'escape' in keys:
                print("\n⚠️  用户按ESC键，立即退出程序...")
                self.cleanup()
                import sys
                sys.exit(0)
        
        if not found:
            print(f"   ⏱️  超时，未找到隐藏目标")
            # 重置目标状态
            if target_id in self.target_stims:
                self.target_stims[target_id]['status'] = 'normal'
        
        return found
    
    def cleanup(self):
        """清理资源"""
        try:
            print("\n🧹 正在清理资源...")
            
            # 关闭窗口
            if self.win:
                self.win.close()
            
            # 关闭数据记录器
            if self.data_logger:
                self.data_logger.close()
            
            # 清理LSL管理器
            self.lsl_manager.cleanup()
            
            # 清理音频管理器
            self.audio_manager.cleanup()
            
            print("✅ 资源清理完成")
            
        except Exception as e:
            self.logger.error(f"资源清理错误: {e}")
    
    def run(self):
        """运行完整的认知地图学习流程"""
        try:
            # 收集实验信息
            if not self.collect_info():
                return False
            
            # 初始化设置
            if not self.setup():
                return False
            
            # 显示说明
            self.show_instructions()
            
            # 运行学习阶段
            self.run_learning_phase()
            
            print("\n🎉 认知地图学习完成！")
            return True
            
        except Exception as e:
            self.logger.error(f"认知地图学习错误: {e}")
            print(f"\n❌ 认知地图学习失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup()
    
    def show_instructions(self):
        """显示实验说明"""
        instruction_text = visual.TextStim(
            self.win,
            text=f'认知地图学习 (Phase 0)\n\n'
                 f'参与者: {self.sub_id} ({self.sub_role})\n\n'
                 f'任务说明：\n'
                 f'1. 根据语音指令前往指定的墙面标记\n'
                 f'2. 到达后搜索指定的隐藏目标区域\n'
                 f'3. 亮粉色光点代表您的位置\n'
                 f'4. 按 [Esc] 键可提前退出\n\n'
                 f'按 [空格键] 开始学习',
            color=[1, 1, 1],
            height=30,
            wrapWidth=800
        )
        
        instruction_text.draw()
        self.win.flip()
        
        # 等待空格键
        event.waitKeys(keyList=['space'])


def run(managers, dyad_id, session_id, sub_id, sub_role, trial_num):
    """外部调用接口（兼容新架构）"""
    try:
        system = MapLearningSystem()
        
        # 设置参数
        system.dyad_id = dyad_id
        system.session_id = session_id
        system.sub_id = sub_id
        system.sub_role = sub_role
        system.trial_num = trial_num
        
        # 使用外部管理器
        if managers:
            system.lsl_manager = managers.get('lsl_manager', system.lsl_manager)
            system.transform_manager = managers.get('transform_manager', system.transform_manager)
            system.audio_manager = managers.get('audio_manager', system.audio_manager)
        
        # 跳过collect_info，直接setup和运行
        if system.setup():
            system.show_instructions()
            system.run_learning_phase()
            return True
        
        return False
        
    except Exception as e:
        print(f"❌ 外部调用认知地图学习失败: {e}")
        return False
    finally:
        if 'system' in locals():
            system.cleanup()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("认知地图学习脚本 - Phase 0")
    print("=" * 60)
    
    system = MapLearningSystem()
    
    try:
        success = system.run()
        
        if success:
            print("\n🎉 认知地图学习成功完成！")
        else:
            print("\n⚠️  认知地图学习未完成")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  认知地图学习被用户中断")
        system.cleanup()
    
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        system.cleanup()