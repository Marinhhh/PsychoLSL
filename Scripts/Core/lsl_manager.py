"""
LSL/NatNet混合管理器 (V3.0版)
单例模式，统一管理NatNet数据接收和LSL Marker异步发送
支持骨骼数据获取和Degraded Mode

功能：
- NatNet客户端：持续接收Motive广播的刚体和骨骼数据
- LSL Marker异步发送：通过独立线程发送TTL标记，保证实时性
- 骨骼数据获取：提取指定骨骼的Root/Pelvis核心3D位置
- 刚体数据获取：获取最新刚体3D世界坐标
- Degraded Mode：仅NatNet接收，无LSL Marker发送
"""

import sys
import threading
import time
import logging
from queue import Queue, Empty
from collections import deque
from pathlib import Path

# 导入OptiTrack数据保存器
try:
    from .optitrack_data_saver import OptiTrackDataSaver
    print("✅ OptiTrackDataSaver已导入")
except ImportError as e:
    print(f"⚠️  OptiTrackDataSaver导入失败: {e}")
    OptiTrackDataSaver = None

# 添加NatNetSDK路径
natnet_path = Path(__file__).parent.parent.parent / 'Config' / 'NatNetSDK' / 'Samples' / 'PythonClient'
sys.path.insert(0, str(natnet_path))

# 导入NatNetSDK
try:
    from NatNetClient import NatNetClient
    import DataDescriptions
    import MoCapData
    print(f"✅ NatNetSDK已导入: {natnet_path}")
except ImportError as e:
    print(f"❌ 无法导入NatNetSDK: {e}")
    print(f"   请确保路径正确: {natnet_path}")
    NatNetClient = DataDescriptions = MoCapData = None

# 导入LSL
try:
    from pylsl import StreamInfo, StreamOutlet
    print("✅ pylsl已导入")
except ImportError as e:
    print(f"❌ 无法导入pylsl: {e}")
    print("   LSL Marker功能将不可用")
    StreamInfo = StreamOutlet = None


class LSLManager:
    """LSL/NatNet混合管理器（单例）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.logger = logging.getLogger('LSLManager')
        
        # NatNet客户端配置
        self.natnet_client = None
        self.server_ip = "192.168.3.58"
        self.client_ip = "192.168.3.55"
        self.use_multicast = True
        
        # LSL Marker异步发送
        self.marker_outlet = None
        self.marker_queue = Queue(maxsize=1000)
        self.marker_thread = None
        self.marker_running = False
        
        # LSL OptiTrack位置广播（新增V3.3）
        self.position_outlets = {}  # {Sub001: outlet, Sub002: outlet}
        self.position_broadcast_enabled = True  # 是否启用位置广播
        
        # NatNet数据接收
        self.natnet_running = False
        self.natnet_connected = False
        
        # 数据缓存
        self.latest_rigid_bodies = {}
        self.latest_skeleton_data = {}
        self.frame_count = 0
        self.start_time = None
        
        # 统计信息（最近5秒）
        self.frame_timestamps = deque(maxlen=600)  # 假设120Hz
        
        # Degraded Mode
        self.degraded_mode = False
        
        # OptiTrack数据保存器
        self.optitrack_saver = None
        if OptiTrackDataSaver:
            self.optitrack_saver = OptiTrackDataSaver()
        
        # 帧计数（用于数据保存）
        self.natnet_frame_number = 0
    
    def initialize_marker_outlet(self):
        """创建LSL Marker Stream Outlet"""
        try:
            if not StreamInfo or not StreamOutlet:
                print("⚠️  LSL不可用，启用Degraded Mode")
                self.degraded_mode = True
                return True
            
            # 创建LSL Marker流
            marker_info = StreamInfo(
                name='Navigation_Markers',
                type='Markers',
                channel_count=1,
                nominal_srate=0,  # 不规则采样
                channel_format='int32',
                source_id='navigation_ttl_markers'
            )
            
            # 添加通道描述
            channels = marker_info.desc().append_child("channels")
            ch = channels.append_child("channel")
            ch.append_child_value("label", "TTL_Code")
            ch.append_child_value("unit", "")
            ch.append_child_value("type", "marker")
            
            self.marker_outlet = StreamOutlet(marker_info)
            
            print("✅ LSL Marker流已创建")
            return True
            
        except Exception as e:
            self.logger.error(f"LSL Marker流创建失败: {e}")
            print(f"⚠️  LSL Marker创建失败，启用Degraded Mode: {e}")
            self.degraded_mode = True
            return True  # Degraded Mode下仍然返回True
    
    def initialize_position_outlets(self, sub_ids=['001', '002']):
        """创建OptiTrack位置LSL流（V3.3新增）
        
        为每个被试创建一个LSL流广播其位置数据
        这样其他LSL设备（fNIRS/EEG）可以接收OptiTrack位置进行同步
        
        Args:
            sub_ids: 被试ID列表，如['001', '002']
        """
        try:
            if not StreamInfo or not StreamOutlet:
                print("⚠️  LSL不可用，无法创建位置流")
                return False
            
            if not self.position_broadcast_enabled:
                print("ℹ️  位置广播未启用，跳过")
                return True
            
            print(f"\n📡 创建OptiTrack位置LSL流...")
            
            for sub_id in sub_ids:
                # 为每个Sub创建一个LSL流
                stream_name = f"Sub{sub_id}_Position"
                
                # 创建StreamInfo（3通道：X, Y, Z）
                position_info = StreamInfo(
                    name=stream_name,
                    type='MoCap',  # 动作捕捉类型
                    channel_count=3,  # X, Y, Z
                    nominal_srate=0,  # 不规则采样（跟随NatNet帧率~120Hz）
                    channel_format='float32',
                    source_id=f'optitrack_sub{sub_id}'
                )
                
                # 添加通道描述（详细元数据）
                channels = position_info.desc().append_child("channels")
                
                for axis in ['X', 'Y', 'Z']:
                    ch = channels.append_child("channel")
                    ch.append_child_value("label", f"Position_{axis}")
                    ch.append_child_value("unit", "meters")
                    ch.append_child_value("type", "Position")
                    ch.append_child_value("coordinate_system", "Motive_World")
                
                # 添加设备信息
                acquisition = position_info.desc().append_child("acquisition")
                acquisition.append_child_value("manufacturer", "OptiTrack")
                acquisition.append_child_value("system", "Motive")
                acquisition.append_child_value("protocol", "NatNet")
                acquisition.append_child_value("subject_id", f"Sub{sub_id}")
                
                # 创建Outlet
                outlet = StreamOutlet(position_info)
                self.position_outlets[f"Sub{sub_id}"] = outlet
                
                print(f"  ✅ 已创建: {stream_name} (3通道: X, Y, Z)")
            
            print(f"✅ OptiTrack位置LSL流已创建（共{len(self.position_outlets)}个）")
            return True
            
        except Exception as e:
            self.logger.error(f"位置LSL流创建失败: {e}")
            print(f"⚠️  位置LSL流创建失败: {e}")
            return False
    
    def _marker_send_loop(self):
        """(独立线程) 从队列中取出Marker Code，异步发送"""
        while self.marker_running:
            try:
                # 从队列获取标记
                marker_code = self.marker_queue.get(timeout=0.1)
                
                if self.marker_outlet and not self.degraded_mode:
                    # 发送到LSL
                    self.marker_outlet.push_sample([marker_code])
                    self.logger.info(f"LSL Marker发送: {marker_code}")  # 移除emoji避免编码错误
                else:
                    # Degraded Mode: 只记录到日志
                    self.logger.info(f"[Degraded] LSL Marker模拟发送: {marker_code}")
                
                self.marker_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"LSL Marker发送错误: {e}")
                time.sleep(0.01)
    
    def send_marker(self, code: int, meaning: str = ""):
        """主线程调用：将TTL Code放入异步发送队列"""
        try:
            if not self.marker_running:
                self.logger.warning("Marker发送线程未运行")
                return False
            
            # 放入发送队列
            if not self.marker_queue.full():
                self.marker_queue.put(code)
                info_msg = f"⏰ Marker已排队: {code}"
                if meaning:
                    info_msg += f" ({meaning})"
                print(info_msg)
                return True
            else:
                self.logger.warning("Marker队列已满，丢弃标记")
                return False
            
        except Exception as e:
            self.logger.error(f"Marker排队错误: {e}")
            return False
    
    def initialize_natnet_client(self, server_ip="192.168.3.58", client_ip="192.168.3.55", use_multicast=True):
        """初始化NatNet客户端连接Motive"""
        try:
            if not NatNetClient:
                self.logger.error("NatNetSDK不可用")
                return False
            
            self.server_ip = server_ip
            self.client_ip = client_ip
            self.use_multicast = use_multicast
            
            print(f"🔗 正在初始化NatNet客户端...")
            print(f"   服务器IP: {server_ip}")
            print(f"   客户端IP: {client_ip}")
            print(f"   组播模式: {use_multicast}")
            
            # 创建NatNet客户端
            self.natnet_client = NatNetClient()
            self.natnet_client.set_client_address(client_ip)
            self.natnet_client.set_server_address(server_ip)
            self.natnet_client.set_use_multicast(use_multicast)
            
            # 关闭NatNet的verbose输出（避免淹没我们的调试信息）
            self.natnet_client.set_print_level(0)  # 0=关闭, 1=开启, >1=每N帧打印一次
            
            # 设置回调函数（使用new_frame_with_data_listener获取完整MoCapData对象）
            self.natnet_client.new_frame_with_data_listener = self._on_new_frame
            self.natnet_client.rigid_body_listener = self._on_rigid_body_frame
            
            # 启动NatNet客户端（使用数据流模式）
            self.natnet_running = self.natnet_client.run('d')  # 'd' = 数据流模式
            if not self.natnet_running:
                self.logger.error("NatNet客户端启动失败")
                return False
            
            # 等待连接
            print("⏳ 等待NatNet连接...")
            time.sleep(2)
            
            if not self.natnet_client.connected():
                print("❌ 无法连接到OptiTrack服务器")
                print("   请检查:")
                print("   1. Motive是否正在运行")
                print("   2. 流设置是否正确")
                print("   3. 网络连接是否正常")
                print("   4. IP地址是否正确")
                return False
            
            self.natnet_connected = True
            self.start_time = time.time()
            self.frame_count = 0
            
            print("✅ NatNet客户端连接成功")
            return True
            
        except Exception as e:
            self.logger.error(f"NatNet客户端初始化失败: {e}")
            print(f"❌ NatNet初始化失败: {e}")
            return False
    
    def _on_new_frame(self, data_dict):
        """NatNet新帧回调函数（使用new_frame_with_data_listener）
        
        data_dict包含:
            - "mocap_data": MoCapFrame对象（包含marker_set_data, skeleton_data等）
            - "frame_number": 帧号
            - 其他元数据...
        """
        try:
            # 提取真正的MoCapData对象
            if "mocap_data" not in data_dict:
                self.logger.warning("data_dict中缺少mocap_data")
                return
            
            mocap_data = data_dict["mocap_data"]
            
            self.frame_count += 1
            self.natnet_frame_number += 1
            current_time = time.time()
            self.frame_timestamps.append(current_time)
            
            # 保存原始NatNet数据（如果数据保存器可用）
            if self.optitrack_saver and self.optitrack_saver.is_active:
                # 保存Markerset数据（marker_set_data，包含命名的markerset如Sub001）
                if hasattr(mocap_data, 'marker_set_data') and mocap_data.marker_set_data:
                    marker_set_list = getattr(mocap_data.marker_set_data, 'marker_data_list', [])
                    if marker_set_list:
                        self.optitrack_saver.save_marker_data(self.natnet_frame_number, marker_set_list)
                
                # 保存骨骼数据
                if hasattr(mocap_data, 'skeleton_data') and mocap_data.skeleton_data:
                    skeleton_list = getattr(mocap_data.skeleton_data, 'skeleton_list', [])
                    if skeleton_list:
                        self.optitrack_saver.save_skeleton_data(self.natnet_frame_number, skeleton_list)
                
                # 保存刚体数据
                if hasattr(mocap_data, 'rigid_body_data') and mocap_data.rigid_body_data:
                    rigidbody_list = getattr(mocap_data.rigid_body_data, 'rigid_body_list', [])
                    if rigidbody_list:
                        self.optitrack_saver.save_rigidbody_data(self.natnet_frame_number, rigidbody_list)
            
            # 处理Markerset数据（优先，用于实时跟踪）
            if hasattr(mocap_data, 'marker_set_data') and mocap_data.marker_set_data:
                marker_set_list = getattr(mocap_data.marker_set_data, 'marker_data_list', [])
                
                for marker_set in marker_set_list:
                    # 获取Markerset名称（如"Sub001"）
                    model_name = getattr(marker_set, 'model_name', None)
                    if model_name:
                        try:
                            if isinstance(model_name, bytes):
                                model_name = model_name.decode('utf-8', errors='replace')
                        except Exception as e:
                            self.logger.warning(f"无法解码model_name: {e}")
                            model_name = str(model_name)
                    
                    # 跳过"all"这个总集合
                    if model_name and model_name.lower() != 'all':
                        # 获取marker位置列表（NatNet SDK: marker_pos_list是位置列表，不是对象列表）
                        marker_positions = getattr(marker_set, 'marker_pos_list', [])
                        
                        if marker_positions:
                            # 计算所有marker的质心作为这个subject的位置
                            pos_x_sum = 0.0
                            pos_y_sum = 0.0
                            pos_z_sum = 0.0
                            valid_marker_count = 0
                            
                            for pos in marker_positions:
                                # pos直接是[x, y, z]列表（Y是Up-axis）
                                if pos and len(pos) >= 3:
                                    pos_x_sum += pos[0]
                                    pos_y_sum += pos[1]  # Y是Up-axis
                                    pos_z_sum += pos[2]
                                    valid_marker_count += 1
                            
                            if valid_marker_count > 0:
                                # 质心位置
                                centroid_position = (
                                    pos_x_sum / valid_marker_count,
                                    pos_y_sum / valid_marker_count,
                                    pos_z_sum / valid_marker_count
                                )
                                
                                # 存储到latest_skeleton_data（复用相同的数据结构）
                                storage_names = [model_name]  # Sub001格式
                                
                                # 提取ID号（如从"Sub001"提取1）
                                if model_name.startswith('Sub'):
                                    try:
                                        sub_id_str = model_name[3:]  # "001"
                                        sub_id = int(sub_id_str)
                                        storage_names.append(f"Skeleton_{sub_id}")  # Skeleton_1
                                    except ValueError:
                                        pass
                                
                                for name in storage_names:
                                    self.latest_skeleton_data[name] = {
                                        'skeleton_id': 0,
                                        'model_name': model_name,
                                        'pelvis_position': centroid_position,
                                        'timestamp': current_time,
                                        'valid': True,
                                        'source': 'markerset'  # 标记数据来源
                                    }
                                
                                # 推送到LSL位置流（V3.3新增）
                                if self.position_broadcast_enabled and model_name in self.position_outlets:
                                    try:
                                        position_sample = [
                                            float(centroid_position[0]),  # X
                                            float(centroid_position[1]),  # Y
                                            float(centroid_position[2])   # Z
                                        ]
                                        self.position_outlets[model_name].push_sample(position_sample)
                                    except Exception as e:
                                        self.logger.warning(f"LSL位置推送失败 {model_name}: {e}")
                                
                                # 调试信息（每120帧打印一次）
                                if self.frame_count % 120 == 1:
                                    print(f"[NatNet] Markerset数据: {model_name} -> 质心: ({centroid_position[0]:.3f}, {centroid_position[1]:.3f}, {centroid_position[2]:.3f}) [{valid_marker_count}个标记] -> 已存储为: {storage_names}")
            
            # 处理骨骼数据（用于实时跟踪，作为备选）
            if hasattr(mocap_data, 'skeleton_data') and mocap_data.skeleton_data:
                skeleton_list = getattr(mocap_data.skeleton_data, 'skeleton_list', [])
                
                # 调试：首次发现骨骼时打印
                if skeleton_list and self.frame_count % 120 == 1:
                    print(f"🔍 发现 {len(skeleton_list)} 个骨骼对象")
                
                for skeleton in skeleton_list:
                    skeleton_id = skeleton.id_num
                    
                    # 获取Motive中的Model Name（如Sub001）
                    model_name = getattr(skeleton, 'name', None)
                    if model_name and isinstance(model_name, bytes):
                        model_name = model_name.decode('utf-8')
                    
                    # 查找Pelvis/Root Joint
                    pelvis_position = None
                    joints = getattr(skeleton, 'rigid_body_list', [])
                    if joints:
                        for joint in joints:
                            joint_name = getattr(joint, 'name', '')
                            if isinstance(joint_name, bytes):
                                joint_name = joint_name.decode('utf-8')
                            joint_name_lower = joint_name.lower()
                            
                            # 查找Pelvis或第一个关节
                            if 'pelvis' in joint_name_lower or 'root' in joint_name_lower or joint.id_num == 0:
                                pelvis_position = (joint.pos[0], joint.pos[1], joint.pos[2])
                                break
                    
                    # 如果没有找到特定关节，使用第一个关节
                    if not pelvis_position and joints and len(joints) > 0:
                        first_joint = joints[0]
                        pelvis_position = (first_joint.pos[0], first_joint.pos[1], first_joint.pos[2])
                    
                    if pelvis_position:
                        # 存储多种命名格式
                        storage_names = []
                        if model_name:
                            storage_names.append(model_name)  # Sub001
                        storage_names.append(f"Skeleton_{skeleton_id}")  # Skeleton_1
                        
                        for name in storage_names:
                            self.latest_skeleton_data[name] = {
                                'skeleton_id': skeleton_id,
                                'model_name': model_name,
                                'pelvis_position': pelvis_position,
                                'timestamp': current_time,
                                'valid': True
                            }
                        
                        # 调试信息（每120帧打印一次）
                        if self.frame_count % 120 == 1:
                            print(f"📊 骨骼数据: {model_name} (ID={skeleton_id}) -> Pelvis位置: ({pelvis_position[0]:.3f}, {pelvis_position[1]:.3f}, {pelvis_position[2]:.3f})")
            
            # 每100帧打印一次统计
            if self.frame_count % 100 == 0:
                if self.start_time:
                    duration = current_time - self.start_time
                    fps = self.frame_count / duration if duration > 0 else 0
                    print(f"[NatNet] 帧数: {self.frame_count}, FPS: {fps:.1f}, 缓存骨骼: {list(self.latest_skeleton_data.keys())}")
                    
                    # 输出数据保存统计
                    if self.optitrack_saver and self.optitrack_saver.is_active:
                        stats = self.optitrack_saver.get_statistics()
                        print(f"💾 OptiTrack数据: Marker={stats['marker_count']}, Skeleton={stats['skeleton_count']}, RigidBody={stats['rigidbody_count']}")
                    
        except Exception as e:
            self.logger.error(f"新帧处理错误: {e}")
    
    def _on_rigid_body_frame(self, rigid_body_id, position, rotation):
        """NatNet刚体帧回调函数"""
        try:
            current_time = time.time()
            
            # 缓存最新刚体数据
            rigid_body_name = f"RigidBody_{rigid_body_id}"
            self.latest_rigid_bodies[rigid_body_name] = {
                'rigid_body_id': rigid_body_id,
                'position': position,
                'rotation': rotation,
                'timestamp': current_time,
                'valid': True
            }
            
        except Exception as e:
            self.logger.error(f"刚体数据处理错误: {e}")
    
    def get_latest_skeleton_data(self, skeleton_name):
        """提取指定骨骼的Root/Pelvis核心3D位置
        
        Args:
            skeleton_name: 骨骼名称，支持多种格式：
                - "Sub001" -> 映射到存储的"Skeleton_1"格式
                - "Skeleton_1" -> 直接使用
                
        Returns:
            dict: {
                'x': float, 'y': float, 'z': float,
                'timestamp': float, 'valid': bool
            } 或 None
        """
        try:
            # 生成可能的骨骼名称列表
            possible_names = []
            
            if skeleton_name.startswith('Sub'):
                # Sub001格式 -> 转换为多种可能的存储格式
                try:
                    sub_id = skeleton_name[3:]  # 提取001部分
                    skeleton_id = int(sub_id)   # 转换为数字1
                    possible_names = [
                        skeleton_name,  # Sub001
                        f"Skeleton_{skeleton_id}",  # Skeleton_1
                        f"Skeleton_{sub_id}"  # Skeleton_001
                    ]
                except ValueError:
                    possible_names = [skeleton_name]
            else:
                # 其他格式直接使用
                possible_names = [skeleton_name]
            
            # 尝试每种可能的名称
            for name in possible_names:
                if name in self.latest_skeleton_data:
                    skeleton_data = self.latest_skeleton_data[name]
                    
                    if skeleton_data['valid']:
                        pos = skeleton_data['pelvis_position']
                        return {
                            'x': pos[0],
                            'y': pos[1],
                            'z': pos[2],
                            'timestamp': skeleton_data['timestamp'],
                            'valid': True
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取骨骼数据错误: {e}")
            return None
    
    def get_latest_rigid_body(self, rigid_body_name):
        """获取最新刚体3D世界坐标（用于Tools/几何对齐验证）
        
        Args:
            rigid_body_name: 刚体名称，如"RigidBody_1"
            
        Returns:
            dict: {
                'x': float, 'y': float, 'z': float,
                'qx': float, 'qy': float, 'qz': float, 'qw': float,
                'timestamp': float, 'valid': bool
            } 或 None
        """
        try:
            if rigid_body_name in self.latest_rigid_bodies:
                rigid_data = self.latest_rigid_bodies[rigid_body_name]
                
                if rigid_data['valid']:
                    pos = rigid_data['position']
                    rot = rigid_data['rotation']
                    return {
                        'x': pos[0],
                        'y': pos[1],
                        'z': pos[2],
                        'qx': rot[0],
                        'qy': rot[1],
                        'qz': rot[2],
                        'qw': rot[3],
                        'timestamp': rigid_data['timestamp'],
                        'valid': True
                    }
            
            return None
    
        except Exception as e:
            self.logger.error(f"获取刚体数据错误: {e}")
            return None
    
    def is_connected(self):
        """检查NatNet/LSL连接状态"""
        current_time = time.time()
        
        # NatNet连接检查：最近3秒内有数据帧，或者刚连接成功（10秒内）
        natnet_connected = False
        if self.natnet_connected:
            if self.frame_timestamps:
                # 有数据帧：检查最后一帧时间
                last_frame_time = self.frame_timestamps[-1]
                natnet_connected = (current_time - last_frame_time) < 3.0
            elif self.start_time:
                # 刚连接，还没有数据帧：给10秒缓冲时间
                time_since_start = current_time - self.start_time
                natnet_connected = time_since_start < 10.0
            else:
                # 使用NatNet客户端的连接状态
                natnet_connected = self.natnet_client and self.natnet_client.connected()
        
        # LSL Marker连接检查
        marker_available = not self.degraded_mode and self.marker_outlet is not None
        
        return {
            'natnet': natnet_connected,
            'lsl_marker': marker_available,
            'degraded_mode': self.degraded_mode
        }
    
    def get_stats(self):
        """获取统计信息"""
        current_time = time.time()
        
        # NatNet统计
        natnet_stats = {
            'connected': False,
            'fps': 0.0,
            'total_frames': self.frame_count,
            'skeleton_count': len(self.latest_skeleton_data),
            'rigid_body_count': len(self.latest_rigid_bodies),
            'last_frame_age': None
        }
        
        if self.frame_timestamps:
            # 计算帧率（最近5秒）
            recent_timestamps = [t for t in self.frame_timestamps if current_time - t < 5.0]
            if len(recent_timestamps) > 1:
                time_span = recent_timestamps[-1] - recent_timestamps[0]
                if time_span > 0:
                    natnet_stats['fps'] = len(recent_timestamps) / time_span
            
            # 最后一帧的年龄
            last_time = self.frame_timestamps[-1]
            natnet_stats['last_frame_age'] = current_time - last_time
            natnet_stats['connected'] = natnet_stats['last_frame_age'] < 3.0
        
        # LSL Marker统计
        marker_stats = {
            'available': not self.degraded_mode,
            'degraded_mode': self.degraded_mode,
            'queue_size': self.marker_queue.qsize(),
            'thread_running': self.marker_running
        }
        
        return {
            'natnet': natnet_stats,
            'lsl_marker': marker_stats
        }
    
    def start_optitrack_data_saving(self, dyad_id, session_id=None):
        """启动OptiTrack数据保存"""
        try:
            if not self.optitrack_saver:
                print("⚠️  OptiTrack数据保存器不可用")
                return False
            
            if self.optitrack_saver.initialize_session(dyad_id, session_id):
                print(f"✅ OptiTrack数据保存已启动: D{dyad_id:03d}")
                return True
            else:
                print("❌ OptiTrack数据保存启动失败")
                return False
                
        except Exception as e:
            self.logger.error(f"启动OptiTrack数据保存失败: {e}")
            return False
        
    def stop_optitrack_data_saving(self):
        """停止OptiTrack数据保存"""
        try:
            if self.optitrack_saver and self.optitrack_saver.is_active:
                self.optitrack_saver.close()
                print("✅ OptiTrack数据保存已停止")
                return True
            return False
        except Exception as e:
            self.logger.error(f"停止OptiTrack数据保存失败: {e}")
            return False
        
    def start_services(self, server_ip="192.168.3.58", client_ip="192.168.3.55", use_multicast=True, 
                       enable_position_broadcast=True, sub_ids=['001', '002']):
        """启动所有服务（NatNet + LSL Marker + LSL位置流）
        
        Args:
            server_ip: Motive服务器IP
            client_ip: 本机IP
            use_multicast: 是否使用组播
            enable_position_broadcast: 是否启用OptiTrack位置LSL广播（V3.3新增）
            sub_ids: 要广播的被试ID列表（V3.3新增）
        """
        try:
            print("\n🚀 启动LSL/NatNet混合管理器...")
            
            # 设置位置广播开关
            self.position_broadcast_enabled = enable_position_broadcast
            
            # 1. 初始化LSL Marker输出流
            if not self.initialize_marker_outlet():
                print("⚠️  LSL Marker初始化失败，但继续运行")
            
            # 1.5 初始化LSL OptiTrack位置流（V3.3新增）
            if enable_position_broadcast:
                if not self.initialize_position_outlets(sub_ids):
                    print("⚠️  位置LSL流初始化失败，但继续运行")
            
            # 2. 启动LSL Marker异步发送线程
            if not self.degraded_mode:
                self.marker_running = True
                self.marker_thread = threading.Thread(
                    target=self._marker_send_loop,
                    daemon=True
                )
                self.marker_thread.start()
                print("✅ LSL Marker异步发送线程已启动")
            else:
                print("⚠️  Degraded Mode: 仅NatNet接收，无LSL Marker发送")
            
            # 3. 初始化NatNet客户端
            if not self.initialize_natnet_client(server_ip, client_ip, use_multicast):
                print("❌ NatNet客户端初始化失败")
                return False
            
            print("✅ LSL/NatNet混合管理器启动成功")
            print(f"   数据流: Motive → NatNet → Python")
            if not self.degraded_mode:
                print(f"   标记流: Python → LSL → 外部设备")
            if self.position_outlets:
                print(f"   位置流: NatNet → LSL → 外部设备（{len(self.position_outlets)}个流）")
            if self.optitrack_saver:
                print(f"   数据保存: 支持OptiTrack CSV保存")
            
            return True
            
        except Exception as e:
            self.logger.error(f"服务启动失败: {e}")
            print(f"❌ 服务启动失败: {e}")
            return False
    
    def cleanup(self):
        """清理连接和线程"""
        try:
            print("\n🧹 正在清理LSL/NatNet资源...")
            
            # 停止OptiTrack数据保存
            self.stop_optitrack_data_saving()
            
            # 清理LSL位置流（V3.3新增）
            if self.position_outlets:
                print(f"   清理 {len(self.position_outlets)} 个LSL位置流...")
                self.position_outlets.clear()
            
            # 停止LSL Marker线程
            if self.marker_running:
                self.marker_running = False
                if self.marker_thread and self.marker_thread.is_alive():
                    self.marker_thread.join(timeout=1.0)
                print("✅ LSL Marker线程已停止")
            
            # 停止NatNet客户端
            if self.natnet_client and self.natnet_running:
                self.natnet_running = False
                self.natnet_connected = False
                self.natnet_client.shutdown()
                print("✅ NatNet客户端已停止")
            
            # 统计信息
            if self.start_time:
                duration = time.time() - self.start_time
                fps = self.frame_count / duration if duration > 0 else 0
                print(f"📊 运行统计:")
                print(f"   运行时长: {duration:.1f}秒")
                print(f"   总帧数: {self.frame_count}")
                print(f"   平均帧率: {fps:.1f} FPS")
                print(f"   骨骼对象: {len(self.latest_skeleton_data)} 个")
                print(f"   刚体对象: {len(self.latest_rigid_bodies)} 个")
                
                # OptiTrack数据保存统计
                if self.optitrack_saver:
                    stats = self.optitrack_saver.get_statistics()
                    print(f"   OptiTrack数据: Marker={stats['marker_count']}, Skeleton={stats['skeleton_count']}, RigidBody={stats['rigidbody_count']}")
            
            print("✅ LSL/NatNet资源已清理")
            
        except Exception as e:
            self.logger.error(f"资源清理错误: {e}")
    
    # ========== 兼容性接口（保持与旧版本兼容） ==========
    
    def connect_optitrack(self, timeout=5.0, auto_bridge=True):
        """兼容性接口：连接OptiTrack（映射到NatNet客户端）"""
        return self.initialize_natnet_client()
    
    def get_optitrack_position(self):
        """兼容性接口：获取OptiTrack位置（映射到第一个可用骨骼或刚体）"""
        # 优先返回骨骼数据
        for skeleton_name in self.latest_skeleton_data:
            skeleton_data = self.get_latest_skeleton_data(skeleton_name)
            if skeleton_data and skeleton_data['valid']:
                return skeleton_data
        
        # 如果没有骨骼数据，返回刚体数据
        for rigid_body_name in self.latest_rigid_bodies:
            rigid_data = self.get_latest_rigid_body(rigid_body_name)
            if rigid_data and rigid_data['valid']:
                return {
                    'x': rigid_data['x'],
                    'y': rigid_data['y'],
                    'z': rigid_data['z'],
                    'timestamp': rigid_data['timestamp'],
                    'valid': rigid_data['valid']
                }
        
        return None