"""
数据记录工具 (V3.0版)
实时记录行为数据、位置数据、TTL标记到CSV文件
强制使用LSL时钟确保时间同步

数据格式：
- Behavior.csv: Map阶段和Navigation阶段的行为数据
- Position.csv: Map阶段（单人骨骼）和Navigation阶段（双人骨骼）PsychoPy位置数据
- Markers.csv: 所有LSL Marker的文本含义，便于事后分析
"""

import csv
from pathlib import Path
import time
from datetime import datetime
import logging


class DataLogger:
    """数据记录工具（强制LSL时钟）"""
    
    def __init__(self, lsl_manager):
        """
        初始化数据记录器
        
        Args:
            lsl_manager: LSLManager实例，用于获取LSL时钟
        """
        if lsl_manager is None:
            raise ValueError("DataLogger需要LSLManager实例以获取LSL时钟")
        
        self.logger = logging.getLogger('DataLogger')
        self.lsl_manager = lsl_manager
        
        # 会话信息
        self.session_info = None
        self.output_dir = None
        
        # CSV文件句柄
        self.behavior_file = None
        self.position_file = None
        self.markers_file = None
        
        # CSV写入器
        self.behavior_writer = None
        self.position_writer = None
        self.markers_writer = None
        
        # 数据缓冲
        self.position_buffer = []
        self.buffer_size = 100
        
        # 帧计数
        self.frame_count = 0
        
        # LSL时钟基准
        self.lsl_clock_offset = None
    
    def create_session(self, dyad_id, session_id, sub_a_id=None, sub_b_id=None, block=None):
        """创建会话并初始化CSV文件"""
        try:
            # 保存会话信息
            self.session_info = {
                'dyad_id': dyad_id,
                'session_id': session_id,
                'sub_a_id': sub_a_id,
                'sub_b_id': sub_b_id,
                'block': block
            }
            
            # 构建输出目录
            self.output_dir = Path(__file__).parent.parent.parent / 'Data' / 'Behavior' / f'D{dyad_id:03d}' / f'S{session_id}'
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化LSL时钟基准
            self._initialize_lsl_clock()
            
            # 创建CSV文件
            self._create_csv_files()
            
            print(f"✅ 数据会话已创建: {self.output_dir}")
            print(f"   Dyad ID: D{dyad_id:03d}")
            print(f"   Session: S{session_id}")
            if sub_a_id:
                print(f"   SubA ID: {sub_a_id}")
            if sub_b_id:
                print(f"   SubB ID: {sub_b_id}")
            if block:
                print(f"   Block: {block}")
            
            return True
            
        except Exception as e:
            print(f"❌ 创建数据会话失败: {e}")
            self.logger.error(f"创建会话错误: {e}")
            return False
    
    def _initialize_lsl_clock(self):
        """初始化LSL时钟基准"""
        try:
            # 获取当前本地时间和LSL时钟的对应关系
            local_time = time.time()
            
            # 如果LSL管理器连接正常，尝试获取LSL时钟
            # 这里简化处理，使用本地时间作为基准
            # 在实际应用中，可以使用pylsl.local_clock()
            self.lsl_clock_offset = local_time
            
            self.logger.info(f"LSL时钟基准已设置: {self.lsl_clock_offset}")
            
        except Exception as e:
            self.logger.error(f"LSL时钟初始化错误: {e}")
            self.lsl_clock_offset = time.time()
    
    def _get_lsl_timestamp(self):
        """获取LSL时钟时间戳（使用LSL统一时钟确保多设备同步）"""
        try:
            # V3.3改进：使用LSL统一时钟
            from pylsl import local_clock
            return local_clock()
        except ImportError:
            # pylsl不可用，降级到本地时间
            self.logger.warning("pylsl不可用，使用本地时间戳")
            return time.time()
        except Exception as e:
            self.logger.error(f"获取LSL时间戳错误: {e}")
            return time.time()
    
    def _create_csv_files(self):
        """创建CSV文件和写入器"""
        try:
            # 生成带时间戳的文件名
            from datetime import datetime
            session_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            dyad_id = self.session_info['dyad_id']
            session_id = self.session_info['session_id']
            
            # Behavior.csv (V3.0新格式，支持追加模式)
            behavior_filename = f'D{dyad_id:03d}_{session_timestamp}.Behavior.csv'
            behavior_path = self.output_dir / behavior_filename
            
            # 检查文件是否存在，决定是否写入表头
            behavior_file_exists = behavior_path.exists() and behavior_path.stat().st_size > 0
            
            self.behavior_file = open(behavior_path, 'a', newline='', encoding='utf-8')
            self.behavior_writer = csv.writer(self.behavior_file)
            
            # 只在文件为空时写入Behavior表头
            if not behavior_file_exists:
                self.behavior_writer.writerow([
                    'SubID', 'SubRole', 'Phase', 'Session', 'Block', 'IsNavigation',
                    'Trial', 'WallMarker', 'Time_Wall_go', 'Time_Wall_arrive', 'RT_WallMarker',
                    'Target', 'Target_position', 'Time_Target_go', 'Time_Target_arrive', 'RT_Target',
                    'KeyNumber', 'Key_Navigation_position', 'Key_Time', 'AccNumber', 'PerAcc'
                ])
                print(f"✅ 创建Behavior文件并写入表头: {behavior_filename}")
            else:
                print(f"✅ 追加到现有Behavior文件: {behavior_filename}")
            
            # Position.csv (V3.0新格式，带时间戳)
            position_filename = f'D{dyad_id:03d}_{session_timestamp}.Position.csv'
            position_path = self.output_dir / position_filename
            self.position_file = open(position_path, 'w', newline='', encoding='utf-8')
            self.position_writer = csv.writer(self.position_file)
            
            # 写入Position表头 (V3.0格式)
            self.position_writer.writerow([
                'SubID', 'SubRole', 'Phase', 'Session', 'Block', 'IsNavigation',
                'Timestamp', 'Raw_x', 'Raw_y', 'Pos_x', 'Pos_y', 'Frame'
            ])
            print(f"✅ 创建Position文件: {position_filename}")
            
            # Markers.csv (带时间戳)
            markers_filename = f'D{dyad_id:03d}_{session_timestamp}.Markers.csv'
            markers_path = self.output_dir / markers_filename
            self.markers_file = open(markers_path, 'w', newline='', encoding='utf-8')
            self.markers_writer = csv.writer(self.markers_file)
            
            # 写入Markers表头
            self.markers_writer.writerow([
                'Timestamp', 'Marker', 'Meaning', 'Trial', 'Phase', 'Additional_Info'
            ])
            print(f"✅ 创建Markers文件: {markers_filename}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"创建CSV文件错误: {e}")
            return False
    
    def log_behavior(self, behavior_data):
        """记录行为数据到Behavior.csv"""
        if self.behavior_writer is None:
            self.logger.warning("Behavior写入器未初始化")
            return False
        
        try:
            # 获取LSL时间戳
            lsl_timestamp = self._get_lsl_timestamp()
            
            # 写入行为数据行
            self.behavior_writer.writerow([
                behavior_data.get('sub_id', ''),           # SubID
                behavior_data.get('sub_role', ''),         # SubRole: A或B
                behavior_data.get('phase', ''),            # Phase: 0或1
                behavior_data.get('session', ''),          # Session: 1或2
                behavior_data.get('block', ''),            # Block: 1或2
                behavior_data.get('is_navigation', ''),    # IsNavigation: 0或1
                behavior_data.get('trial', ''),            # Trial
                behavior_data.get('wall_marker', ''),      # WallMarker
                behavior_data.get('time_wall_go', ''),     # Time_Wall_go
                behavior_data.get('time_wall_arrive', ''), # Time_Wall_arrive
                behavior_data.get('rt_wallmarker', ''),    # RT_WallMarker
                behavior_data.get('target', ''),           # Target
                behavior_data.get('target_position', ''),  # Target_position
                behavior_data.get('time_target_go', ''),   # Time_Target_go
                behavior_data.get('time_target_arrive', ''), # Time_Target_arrive
                behavior_data.get('rt_target', ''),        # RT_Target
                behavior_data.get('key_number', 0),        # KeyNumber
                behavior_data.get('key_navigation_position', ''), # Key_Navigation_position
                behavior_data.get('key_time', ''),         # Key_Time
                behavior_data.get('acc_number', 0),        # AccNumber
                behavior_data.get('per_acc', 0.0)          # PerAcc
            ])
            
            self.behavior_file.flush()
            return True
            
        except Exception as e:
            self.logger.error(f"记录行为数据错误: {e}")
            return False
    
    def log_position(self, position_data):
        """记录位置数据到Position.csv（缓冲模式）"""
        if self.position_writer is None:
            self.logger.warning("Position写入器未初始化")
            return False
        
        self.frame_count += 1
        
        try:
            # 获取LSL时间戳
            lsl_timestamp = self._get_lsl_timestamp()
            
            # 添加到缓冲
            self.position_buffer.append([
                position_data.get('sub_id', ''),           # SubID
                position_data.get('sub_role', ''),         # SubRole: A或B
                position_data.get('phase', ''),            # Phase: 0或1
                position_data.get('session', ''),          # Session: 1或2
                position_data.get('block', ''),            # Block: 1或2
                position_data.get('is_navigation', ''),    # IsNavigation: 0或1
                lsl_timestamp,                             # Timestamp (LSL时钟)
                position_data.get('raw_x', ''),            # Raw_x (Motive原始坐标)
                position_data.get('raw_y', ''),            # Raw_y (Motive原始坐标)
                position_data.get('pos_x', ''),            # Pos_x (PsychoPy屏幕坐标)
                position_data.get('pos_y', ''),            # Pos_y (PsychoPy屏幕坐标)
                self.frame_count                           # Frame
            ])
            
            # 缓冲满时写入
            if len(self.position_buffer) >= self.buffer_size:
                self.flush_position_buffer()
            
            return True
            
        except Exception as e:
            self.logger.error(f"记录位置数据错误: {e}")
            return False
    
    def flush_position_buffer(self):
        """刷新位置数据缓冲到文件"""
        if self.position_writer and self.position_buffer:
            try:
                self.position_writer.writerows(self.position_buffer)
                self.position_file.flush()
                self.position_buffer.clear()
                
            except Exception as e:
                self.logger.error(f"刷新位置缓冲错误: {e}")
    
    def log_marker(self, marker_code, meaning="", trial="", phase="", additional_info=""):
        """记录LSL Marker的文本含义到Markers.csv"""
        if self.markers_writer is None:
            self.logger.warning("Markers写入器未初始化")
            return False
        
        try:
            # 获取LSL时间戳
            lsl_timestamp = self._get_lsl_timestamp()
            
            # 如果没有提供含义，查找预定义含义
            if not meaning:
                meaning = get_marker_meaning(marker_code)
            
            # 写入标记数据
            self.markers_writer.writerow([
                lsl_timestamp,      # Timestamp (LSL时钟)
                marker_code,        # Marker (TTL代码)
                meaning,            # Meaning (文本含义)
                trial,              # Trial
                phase,              # Phase
                additional_info     # Additional_Info
            ])
            
            self.markers_file.flush()
            
            # 同步发送到LSL流（V3.3修复：确保内部记录和LSL流同步）
            if hasattr(self, 'lsl_manager') and self.lsl_manager:
                try:
                    success = self.lsl_manager.send_marker(marker_code, meaning)
                    if success:
                        self.logger.debug(f"LSL Marker已同步发送: {marker_code} ({meaning})")
                    else:
                        self.logger.warning(f"LSL Marker发送失败: {marker_code}")
                except Exception as e:
                    self.logger.warning(f"LSL Marker同步发送异常: {e}")
            else:
                self.logger.warning("LSL管理器不可用，无法同步发送marker")
            
            return True
            
        except Exception as e:
            self.logger.error(f"记录标记错误: {e}")
            return False
    
    def generate_summary(self):
        """生成数据汇总报告"""
        try:
            summary = {
                'session_info': self.session_info,
                'output_dir': str(self.output_dir),
                'total_frames': self.frame_count,
                'buffer_size': len(self.position_buffer),
                'lsl_clock_offset': self.lsl_clock_offset,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 保存汇总到JSON文件
            import json
            summary_file = self.output_dir / 'data_summary.json'
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print(f"📊 数据汇总:")
            print(f"   总帧数: {self.frame_count}")
            print(f"   缓冲大小: {len(self.position_buffer)}")
            print(f"   汇总文件: {summary_file}")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"生成汇总错误: {e}")
            return None
    
    def close(self):
        """关闭数据记录器并清理资源"""
        try:
            # 刷新缓冲
            self.flush_position_buffer()
            
            # 关闭文件
            if self.behavior_file:
                self.behavior_file.close()
                self.behavior_file = None
                self.behavior_writer = None
            
            if self.position_file:
                self.position_file.close()
                self.position_file = None
                self.position_writer = None
            
            if self.markers_file:
                self.markers_file.close()
                self.markers_file = None
                self.markers_writer = None
            
            # 生成汇总
            self.generate_summary()
            
            print("✅ 数据记录器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭数据记录器错误: {e}")


# TTL标记定义 (V3.0)
TTL_MARKERS = {
    1: 'Trial开始',
    2: '到达墙面标记',
    3: '观察者按键',
    4: '找到隐藏目标',
    5: 'Block结束'
}


def get_marker_meaning(marker_code):
    """获取TTL标记含义"""
    return TTL_MARKERS.get(marker_code, f'Unknown_Marker_{marker_code}')


# ========== 兼容性函数 ==========

def create_data_logger_with_lsl(lsl_manager, output_dir=None):
    """创建带LSL支持的数据记录器（兼容性函数）"""
    if output_dir:
        # 如果提供了output_dir，创建传统模式的记录器
        logger = DataLogger.__new__(DataLogger)
        logger.logger = logging.getLogger('DataLogger')
        logger.lsl_manager = lsl_manager
        logger.output_dir = Path(output_dir)
        logger.output_dir.mkdir(parents=True, exist_ok=True)
        logger._initialize_lsl_clock()
        return logger
    else:
        # 创建新模式的记录器
        return DataLogger(lsl_manager)