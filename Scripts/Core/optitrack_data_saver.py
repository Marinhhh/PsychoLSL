"""
OptiTrack数据保存器 (V3.0版)
专门处理NatNet数据的CSV格式保存
支持Marker、Skeleton、RigidBody分类保存

数据格式参考NatNet SDK的DataDescriptions.py
保存路径：Data/Optitrack/{dyad_id}/
"""

import csv
import time
from pathlib import Path
from datetime import datetime
import logging
import threading
from collections import deque


class OptiTrackDataSaver:
    """OptiTrack数据保存器"""
    
    def __init__(self):
        self.logger = logging.getLogger('OptiTrackDataSaver')
        
        # 会话信息
        self.dyad_id = None
        self.session_id = None
        self.output_dir = None
        self.is_active = False
        
        # CSV文件句柄和写入器
        self.marker_file = None
        self.skeleton_file = None
        self.rigidbody_file = None
        
        self.marker_writer = None
        self.skeleton_writer = None
        self.rigidbody_writer = None
        
        # 数据缓冲（批量写入提高性能）
        self.marker_buffer = deque(maxlen=1000)
        self.skeleton_buffer = deque(maxlen=1000)
        self.rigidbody_buffer = deque(maxlen=1000)
        
        # 线程安全锁
        self.data_lock = threading.Lock()
        
        # 统计信息
        self.total_marker_count = 0
        self.total_skeleton_count = 0
        self.total_rigidbody_count = 0
        
        # LSL时间戳基准（用于时间同步）
        self.lsl_time_offset = None
    
    def initialize_session(self, dyad_id, session_id=None):
        """初始化数据保存会话"""
        try:
            self.dyad_id = dyad_id
            self.session_id = session_id or 1
            
            # 创建输出目录：Data/Optitrack/{dyad_id}/
            self.output_dir = Path(__file__).parent.parent.parent / 'Data' / 'Optitrack' / f'D{dyad_id:03d}'
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建CSV文件
            self._create_csv_files()
            
            # 获取LSL时间基准
            self._initialize_lsl_time()
            
            self.is_active = True
            print(f"✅ OptiTrack数据保存器已初始化: {self.output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"初始化OptiTrack数据保存器失败: {e}")
            return False
    
    def _create_csv_files(self):
        """创建CSV文件和表头"""
        try:
            # 生成带时间戳的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Optitrack_Marker.csv
            marker_path = self.output_dir / f'Optitrack_Marker_{timestamp}.csv'
            self.marker_file = open(marker_path, 'w', newline='', encoding='utf-8')
            self.marker_writer = csv.writer(self.marker_file)
            self.marker_writer.writerow([
                'Timestamp', 'FrameNumber', 'MarkerID', 'MarkerName', 
                'PosX', 'PosY', 'PosZ', 'Residual', 'Params'
            ])
            
            # Optitrack_Skeleton.csv
            skeleton_path = self.output_dir / f'Optitrack_Skeleton_{timestamp}.csv'
            self.skeleton_file = open(skeleton_path, 'w', newline='', encoding='utf-8')
            self.skeleton_writer = csv.writer(self.skeleton_file)
            self.skeleton_writer.writerow([
                'Timestamp', 'FrameNumber', 'SkeletonID', 'SkeletonName', 
                'JointID', 'JointName', 'PosX', 'PosY', 'PosZ', 
                'RotX', 'RotY', 'RotZ', 'RotW', 'Tracked'
            ])
            
            # Optitrack_RigidBody.csv  
            rigidbody_path = self.output_dir / f'Optitrack_RigidBody_{timestamp}.csv'
            self.rigidbody_file = open(rigidbody_path, 'w', newline='', encoding='utf-8')
            self.rigidbody_writer = csv.writer(self.rigidbody_file)
            self.rigidbody_writer.writerow([
                'Timestamp', 'FrameNumber', 'RigidBodyID', 'RigidBodyName',
                'PosX', 'PosY', 'PosZ', 'RotX', 'RotY', 'RotZ', 'RotW', 
                'MeanError', 'Tracked'
            ])
            
            print(f"✅ OptiTrack CSV文件已创建:")
            print(f"   标记数据: {marker_path.name}")
            print(f"   骨骼数据: {skeleton_path.name}")
            print(f"   刚体数据: {rigidbody_path.name}")
            
        except Exception as e:
            self.logger.error(f"创建CSV文件失败: {e}")
            raise
    
    def _initialize_lsl_time(self):
        """初始化LSL时间基准"""
        try:
            # 尝试导入pylsl获取时间基准
            from pylsl import local_clock
            self.lsl_time_offset = local_clock()
            print(f"✅ LSL时间基准已设置: {self.lsl_time_offset:.6f}")
        except ImportError:
            # 如果pylsl不可用，使用系统时间
            self.lsl_time_offset = time.time()
            print(f"⚠️  使用系统时间作为基准: {self.lsl_time_offset:.6f}")
    
    def _get_lsl_timestamp(self):
        """获取LSL时间戳"""
        try:
            from pylsl import local_clock
            return local_clock()
        except ImportError:
            return time.time()
    
    def save_marker_data(self, frame_number, marker_set_list):
        """保存Markerset数据（marker_set_data，包含命名的markerset如Sub001）
        
        Args:
            frame_number: 帧号
            marker_set_list: Markerset列表，每个包含model_name和marker_data_list
        """
        if not self.is_active:
            return
        
        try:
            timestamp = self._get_lsl_timestamp()
            
            with self.data_lock:
                for marker_set in marker_set_list:
                    # 获取Markerset名称（如Sub001）
                    model_name = getattr(marker_set, 'model_name', 'Unknown')
                    if isinstance(model_name, bytes):
                        model_name = model_name.decode('utf-8')
                    
                    # 获取这个markerset中的所有marker位置（NatNet SDK: marker_pos_list）
                    marker_positions = getattr(marker_set, 'marker_pos_list', [])
                    
                    for i, pos in enumerate(marker_positions):
                        # pos直接是[x, y, z]列表
                        if not (pos and len(pos) >= 3):
                            continue
                        
                        # 写入CSV（使用model_name作为MarkerName）
                        self.marker_writer.writerow([
                            timestamp,           # Timestamp
                            frame_number,        # FrameNumber
                            i,                  # MarkerID（在markerset内的序号）
                            f"{model_name}_M{i}",  # MarkerName（如Sub001_M0）
                            pos[0],             # PosX
                            pos[1],             # PosY  
                            pos[2],             # PosZ
                            0.0,                # Residual
                            0                   # Params
                        ])
                        
                        self.total_marker_count += 1
                
                # 定期刷新
                if self.total_marker_count % 100 == 0:
                    self.marker_file.flush()
                    
        except Exception as e:
            self.logger.error(f"保存标记数据错误: {e}")
    
    def save_skeleton_data(self, frame_number, skeleton_list):
        """保存骨骼数据
        
        Args:
            frame_number: 帧号
            skeleton_list: 骨骼列表，每个骨骼包含关节信息
        """
        if not self.is_active:
            return
        
        try:
            timestamp = self._get_lsl_timestamp()
            
            with self.data_lock:
                for skeleton in skeleton_list:
                    skeleton_id = getattr(skeleton, 'id_num', 0)
                    skeleton_name = getattr(skeleton, 'name', f'Skeleton_{skeleton_id}')
                    if isinstance(skeleton_name, bytes):
                        skeleton_name = skeleton_name.decode('utf-8')
                    
                    # 遍历骨骼的关节（刚体）
                    rigid_bodies = getattr(skeleton, 'rigid_body_list', [])
                    for joint in rigid_bodies:
                        joint_id = getattr(joint, 'id_num', 0)
                        joint_name = getattr(joint, 'name', f'Joint_{joint_id}')
                        if isinstance(joint_name, bytes):
                            joint_name = joint_name.decode('utf-8')
                        pos = getattr(joint, 'pos', [0.0, 0.0, 0.0])
                        rot = getattr(joint, 'rot', [0.0, 0.0, 0.0, 1.0])
                        tracked = getattr(joint, 'tracking_valid', True)
                        
                        # 写入CSV
                        self.skeleton_writer.writerow([
                            timestamp,          # Timestamp
                            frame_number,       # FrameNumber
                            skeleton_id,        # SkeletonID
                            skeleton_name,      # SkeletonName
                            joint_id,          # JointID
                            joint_name,        # JointName
                            pos[0],            # PosX
                            pos[1],            # PosY
                            pos[2],            # PosZ
                            rot[0],            # RotX
                            rot[1],            # RotY
                            rot[2],            # RotZ
                            rot[3],            # RotW
                            tracked            # Tracked
                        ])
                        
                        self.total_skeleton_count += 1
                
                # 定期刷新
                if self.total_skeleton_count % 100 == 0:
                    self.skeleton_file.flush()
                    
        except Exception as e:
            self.logger.error(f"保存骨骼数据错误: {e}")
    
    def save_rigidbody_data(self, frame_number, rigidbody_list):
        """保存刚体数据
        
        Args:
            frame_number: 帧号
            rigidbody_list: 刚体列表
        """
        if not self.is_active:
            return
        
        try:
            timestamp = self._get_lsl_timestamp()
            
            with self.data_lock:
                for rigidbody in rigidbody_list:
                    rb_id = getattr(rigidbody, 'id_num', 0)
                    rb_name = getattr(rigidbody, 'name', f'RigidBody_{rb_id}')
                    if isinstance(rb_name, bytes):
                        rb_name = rb_name.decode('utf-8')
                    pos = getattr(rigidbody, 'pos', [0.0, 0.0, 0.0])
                    rot = getattr(rigidbody, 'rot', [0.0, 0.0, 0.0, 1.0])
                    mean_error = getattr(rigidbody, 'error', 0.0)
                    tracked = getattr(rigidbody, 'tracking_valid', True)
                    
                    # 写入CSV
                    self.rigidbody_writer.writerow([
                        timestamp,          # Timestamp
                        frame_number,       # FrameNumber
                        rb_id,             # RigidBodyID
                        rb_name,           # RigidBodyName
                        pos[0],            # PosX
                        pos[1],            # PosY
                        pos[2],            # PosZ
                        rot[0],            # RotX
                        rot[1],            # RotY
                        rot[2],            # RotZ
                        rot[3],            # RotW
                        mean_error,        # MeanError
                        tracked            # Tracked
                    ])
                    
                    self.total_rigidbody_count += 1
                
                # 定期刷新
                if self.total_rigidbody_count % 100 == 0:
                    self.rigidbody_file.flush()
                    
        except Exception as e:
            self.logger.error(f"保存刚体数据错误: {e}")
    
    def get_statistics(self):
        """获取保存统计信息"""
        return {
            'marker_count': self.total_marker_count,
            'skeleton_count': self.total_skeleton_count,
            'rigidbody_count': self.total_rigidbody_count,
            'is_active': self.is_active,
            'output_dir': str(self.output_dir) if self.output_dir else None
        }
    
    def close(self):
        """关闭数据保存器并清理资源"""
        try:
            self.is_active = False
            
            # 关闭文件
            if self.marker_file:
                self.marker_file.flush()
                self.marker_file.close()
                self.marker_file = None
            
            if self.skeleton_file:
                self.skeleton_file.flush()
                self.skeleton_file.close()
                self.skeleton_file = None
            
            if self.rigidbody_file:
                self.rigidbody_file.flush()
                self.rigidbody_file.close()
                self.rigidbody_file = None
            
            # 输出统计信息
            stats = self.get_statistics()
            print(f"\n📊 OptiTrack数据保存统计:")
            print(f"   标记数据: {stats['marker_count']} 条")
            print(f"   骨骼数据: {stats['skeleton_count']} 条")
            print(f"   刚体数据: {stats['rigidbody_count']} 条")
            print(f"   保存路径: {stats['output_dir']}")
            print("✅ OptiTrack数据保存器已关闭")
            
        except Exception as e:
            self.logger.error(f"关闭OptiTrack数据保存器错误: {e}")


# ========== 字段含义说明 ==========

"""
字段含义说明：

Optitrack_Marker.csv:
- Timestamp: LSL时间戳，用于与其他数据流同步
- FrameNumber: Motive软件的帧号
- MarkerID: 标记点ID
- MarkerName: 标记点名称
- PosX/Y/Z: 标记点3D位置坐标（米）
- Residual: 标记点重建误差（像素）
- Params: 标记点参数标志

Optitrack_Skeleton.csv:
- Timestamp: LSL时间戳
- FrameNumber: Motive软件的帧号
- SkeletonID: 骨骼ID
- SkeletonName: 骨骼名称（如Sub001）
- JointID: 关节/骨骼段ID
- JointName: 关节名称（如Pelvis, Root等）
- PosX/Y/Z: 关节3D位置坐标（米）
- RotX/Y/Z/W: 关节旋转四元数
- Tracked: 是否被成功跟踪

Optitrack_RigidBody.csv:
- Timestamp: LSL时间戳
- FrameNumber: Motive软件的帧号
- RigidBodyID: 刚体ID
- RigidBodyName: 刚体名称
- PosX/Y/Z: 刚体3D位置坐标（米）
- RotX/Y/Z/W: 刚体旋转四元数
- MeanError: 刚体重建均方误差
- Tracked: 是否被成功跟踪
"""
