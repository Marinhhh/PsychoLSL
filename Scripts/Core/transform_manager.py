"""
坐标转换管理器与场景标记生成器 (V3.0 线性映射版)
处理Motive世界坐标与PsychoPy屏幕坐标的固定线性映射
生成墙面标记和隐藏目标布局

固定映射参数：
- Motive世界范围：X, Z ∈ [-3.0, +3.0]米 (6m × 6m)
- PsychoPy屏幕范围：X, Y ∈ [-540, +540]像素 (1080px × 1080px)
- 固定缩放因子：S = 180.0 像素/米
- Z轴翻转：Motive Z → PsychoPy Y
"""

import json
import random
from pathlib import Path
import logging


class TransformManager:
    """坐标系转换与场景标记管理器 (V3.0 固定线性映射版)"""
    
    def __init__(self, config=None):
        self.logger = logging.getLogger('TransformManager')
        
        # 固定线性映射参数 (V3.0)
        self.scale_factor = 180.0  # 像素/米
        self.z_flip = -1  # Z轴翻转因子
        
        # 世界坐标范围 (米)
        self.world_range = 6.0  # [-3.0, +3.0]
        
        # 屏幕坐标范围 (像素)
        self.screen_range = 1080  # [-540, +540]
        
        # 场景配置 (固定为6米×6米)
        self.room_width = 6.0
        self.room_height = 6.0
        
        # 墙面标记配置
        self.wall_markers = {}
        
        # 隐藏目标配置
        self.hidden_targets = {}
        
        # 颜色配置 (RGBA格式，适用于PsychoPy)
        self.wall_colors = {
            'A': [-1, -1, 1],      # 蓝色
            'B': [-1, 1, -1],      # 绿色
            'C': [1, -1, -1],      # 红色
            'D': [1, 1, -1]        # 黄色
        }
    
    def validate_transform(self):
        """验证固定线性映射参数"""
        try:
            # 验证映射常数
            expected_scale = self.screen_range / self.world_range  # 1080 / 6 = 180
            
            if abs(self.scale_factor - expected_scale) > 0.1:
                self.logger.warning(f"缩放因子不匹配: {self.scale_factor} != {expected_scale}")
                return False
            
            print(f"✅ 线性映射参数验证通过")
            print(f"   缩放因子: {self.scale_factor} 像素/米")
            print(f"   Z轴翻转: {self.z_flip}")
            print(f"   世界范围: ±{self.world_range/2:.1f}米")
            print(f"   屏幕范围: ±{self.screen_range/2:.0f}像素")
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证线性映射错误: {e}")
            return False
    
    def real_to_screen(self, x_real, z_real):
        """Motive世界坐标 → PsychoPy屏幕坐标 (固定线性映射)
        
        Args:
            x_real: Motive X坐标 (米)
            z_real: Motive Z坐标 (米)
            
        Returns:
            tuple: (x_screen, y_screen) PsychoPy屏幕像素坐标
        """
        # 固定线性映射公式
        x_screen = self.scale_factor * x_real
        y_screen = self.scale_factor * z_real * self.z_flip  # Z轴翻转
        
        return x_screen, y_screen
    
    def screen_to_real(self, x_screen, y_screen):
        """PsychoPy屏幕坐标 → Motive世界坐标 (固定线性逆映射)
        
        Args:
            x_screen: PsychoPy X坐标 (像素)
            y_screen: PsychoPy Y坐标 (像素)
            
        Returns:
            tuple: (x_real, z_real) Motive世界坐标 (米)
        """
        # 固定线性逆映射公式
        x_real = x_screen / self.scale_factor
        z_real = (y_screen * self.z_flip) / self.scale_factor  # Z轴翻转
        
        return x_real, z_real
    
    def generate_wall_markers(self):
        """生成墙面标记点 (A1-D5)"""
        print("📍 正在生成墙面标记...")
        
        markers_per_wall = 5
        marker_spacing = self.room_width / (markers_per_wall + 1)
        
        walls = {
            'A': 'bottom',   # 下墙
            'B': 'right',    # 右墙
            'C': 'top',      # 上墙
            'D': 'left'      # 左墙
        }
        
        for wall_id, wall_pos in walls.items():
            for i in range(1, markers_per_wall + 1):
                marker_id = f"{wall_id}{i}"
                
                # 计算位置（以世界中心为原点，范围[-3,+3]）
                if wall_pos == 'bottom':
                    x = -3.0 + i * marker_spacing
                    z = -3.0
                elif wall_pos == 'right':
                    x = 3.0
                    z = -3.0 + i * marker_spacing
                elif wall_pos == 'top':
                    x = 3.0 - i * marker_spacing
                    z = 3.0
                elif wall_pos == 'left':
                    x = -3.0
                    z = 3.0 - i * marker_spacing
                
                # 转换到屏幕坐标
                screen_x, screen_y = self.real_to_screen(x, z)
                
                self.wall_markers[marker_id] = {
                    'id': marker_id,
                    'wall': wall_id,
                    'position': wall_pos,
                    'real_pos': (x, z),
                    'screen_pos': (screen_x, screen_y),
                    'color': self.wall_colors[wall_id]
                }
        
        print(f"✅ 已生成 {len(self.wall_markers)} 个墙面标记")
        return self.wall_markers
    
    def generate_hidden_targets(self, num_targets=3, min_distance=2.0):
        """
        生成隐藏目标区域 (P1-P3)
        num_targets: 目标数量
        min_distance: 目标间最小距离
        """
        print("🎯 正在生成隐藏目标...")
        
        target_radius = 0.4  # 隐藏区域半径（米）
        edge_margin = 1.0    # 距离边缘的最小距离
        
        attempts = 0
        max_attempts = 100
        
        targets = []
        
        while len(targets) < num_targets and attempts < max_attempts:
            attempts += 1
            
            # 随机生成位置（世界坐标）
            x = random.uniform(-3.0 + edge_margin, 3.0 - edge_margin)
            z = random.uniform(-3.0 + edge_margin, 3.0 - edge_margin)
            
            # 检查与已有目标的距离
            valid = True
            for existing_target in targets:
                ex, ez = existing_target['center']
                distance = ((x - ex)**2 + (z - ez)**2) ** 0.5
                if distance < min_distance:
                    valid = False
                    break
            
            if valid:
                target_id = f"P{len(targets) + 1}"
                
                # 转换到屏幕坐标
                screen_x, screen_y = self.real_to_screen(x, z)
                screen_radius = target_radius * self.scale_factor
                
                targets.append({
                    'id': target_id,
                    'center': (x, z),
                    'radius': target_radius,
                    'screen_center': (screen_x, screen_y),
                    'screen_radius': screen_radius
                })
        
        if len(targets) < num_targets:
            print(f"⚠️  仅生成了 {len(targets)}/{num_targets} 个目标")
        
        # 转换为字典
        for target in targets:
            self.hidden_targets[target['id']] = target
        
        print(f"✅ 已生成 {len(self.hidden_targets)} 个隐藏目标")
        return self.hidden_targets
    
    def load_scene_layout(self, dyad_id, session_id):
        """加载场景布局配置，如不存在则生成默认布局"""
        try:
            # 构建文件路径
            input_file = Path(__file__).parent.parent.parent / 'Data' / 'Behavior' / f'D{dyad_id:03d}' / f'S{session_id}' / 'scene_layout.json'
            
            if not input_file.exists():
                print(f"ℹ️  场景布局文件不存在，将生成默认布局: {input_file}")
                # 生成默认布局
                self.generate_wall_markers()
                self.generate_hidden_targets()
                self.save_scene_layout(dyad_id, session_id)
                return True
            
            with open(input_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            # 加载布局数据
            if 'transform_params' in layout_data:
                params = layout_data['transform_params']
                self.scale_factor = params.get('scale_factor', 180.0)
                self.z_flip = params.get('z_flip', -1)
                self.world_range = params.get('world_range', 6.0)
                self.screen_range = params.get('screen_range', 1080)
            
            self.room_width, self.room_height = layout_data.get('room_size', [6.0, 6.0])
            self.wall_markers = layout_data.get('wall_markers', {})
            self.hidden_targets = layout_data.get('hidden_targets', {})
            
            print(f"✅ 已加载场景布局: {input_file}")
            print(f"   墙面标记: {len(self.wall_markers)} 个")
            print(f"   隐藏目标: {len(self.hidden_targets)} 个")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载场景布局失败: {e}")
            self.logger.error(f"加载场景布局错误: {e}")
            return False
    
    def save_scene_layout(self, dyad_id, session_id):
        """保存场景布局配置到指定路径"""
        try:
            # 构建保存路径：Data/Behavior/{dyad_id}/{session_id}/scene_layout.json
            output_dir = Path(__file__).parent.parent.parent / 'Data' / 'Behavior' / f'D{dyad_id:03d}' / f'S{session_id}'
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / 'scene_layout.json'
            
            layout_data = {
                'room_size': [self.room_width, self.room_height],
                'transform_params': {
                    'scale_factor': self.scale_factor,
                    'z_flip': self.z_flip,
                    'world_range': self.world_range,
                    'screen_range': self.screen_range
                },
                'wall_markers': self.wall_markers,
                'hidden_targets': self.hidden_targets
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 场景布局已保存: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存场景布局失败: {e}")
            self.logger.error(f"保存场景布局错误: {e}")
            return False
    
    def validate_scene_layout(self):
        """验证场景布局（目标不重叠）"""
        if len(self.hidden_targets) < 2:
            return True
        
        target_list = list(self.hidden_targets.values())
        
        for i, target1 in enumerate(target_list):
            for target2 in target_list[i+1:]:
                x1, z1 = target1['center']
                x2, z2 = target2['center']
                r1 = target1['radius']
                r2 = target2['radius']
                
                distance = ((x1 - x2)**2 + (z1 - z2)**2) ** 0.5
                
                if distance < (r1 + r2):
                    print(f"⚠️  目标重叠: {target1['id']} 和 {target2['id']}")
                    return False
        
        print("✅ 场景布局验证通过")
        return True
    
    def get_wall_marker_list(self):
        """获取所有墙面标记ID列表"""
        return list(self.wall_markers.keys())
    
    def get_target_list(self):
        """获取所有隐藏目标ID列表"""
        return list(self.hidden_targets.keys())
    
    def get_marker_position(self, marker_id):
        """获取标记位置 (世界坐标)"""
        if marker_id in self.wall_markers:
            return self.wall_markers[marker_id]['real_pos']
        return None
    
    def get_marker_screen_position(self, marker_id):
        """获取标记屏幕位置"""
        if marker_id in self.wall_markers:
            return self.wall_markers[marker_id]['screen_pos']
        return None
    
    def get_target_info(self, target_id):
        """获取目标信息"""
        if target_id in self.hidden_targets:
            return self.hidden_targets[target_id]
        return None
    
    def check_point_in_circle(self, point, center, radius):
        """检查点是否在圆内（碰撞检测）
        使用屏幕坐标进行计算，确保精度
        """
        # 将点和中心都转换为屏幕坐标进行计算
        if len(point) == 2 and len(center) == 2:
            # 如果是世界坐标，转换为屏幕坐标
            if abs(point[0]) <= 5 and abs(point[1]) <= 5:  # 判断是否为世界坐标范围
                screen_point = self.real_to_screen(point[0], point[1])
                screen_center = self.real_to_screen(center[0], center[1])
                screen_radius = radius * self.scale_factor
            else:
                # 已经是屏幕坐标
                screen_point = point
                screen_center = center
                screen_radius = radius
            
            px, py = screen_point
            cx, cy = screen_center
            distance = ((px - cx)**2 + (py - cy)**2) ** 0.5
            return distance <= screen_radius
        
        return False
    
    def check_point_near_marker(self, point, marker_id, threshold=1.0):
        """检查点是否靠近墙面标记
        使用屏幕坐标进行计算，确保精度
        """
        if marker_id not in self.wall_markers:
            return False
        
        marker_pos = self.wall_markers[marker_id]['real_pos']
        
        # 转换为屏幕坐标进行距离计算
        if len(point) == 2:
            # 如果是世界坐标，转换为屏幕坐标
            if abs(point[0]) <= 5 and abs(point[1]) <= 5:
                screen_point = self.real_to_screen(point[0], point[1])
            else:
                screen_point = point
            
            screen_marker = self.real_to_screen(marker_pos[0], marker_pos[1])
            screen_threshold = threshold * self.scale_factor
            
            px, py = screen_point
            mx, my = screen_marker
            
            distance = ((px - mx)**2 + (py - my)**2) ** 0.5
            return distance <= screen_threshold
        
        return False