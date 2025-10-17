"""
NatNet数据诊断工具
用于排查NatNet连接和数据接收问题
"""

import sys
import time
from pathlib import Path

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 添加NatNetSDK路径
natnet_path = Path(__file__).parent.parent.parent / 'Config' / 'NatNetSDK' / 'Samples' / 'PythonClient'
sys.path.insert(0, str(natnet_path))

from NatNetClient import NatNetClient


class NatNetDiagnostic:
    """NatNet数据诊断工具"""
    
    def __init__(self):
        self.client = None
        self.frame_count = 0
        self.start_time = None
        
        # 统计信息
        self.has_markerset_data = False
        self.has_skeleton_data = False
        self.has_rigidbody_data = False
        
        self.markerset_names = set()
        self.skeleton_names = set()
        self.rigidbody_ids = set()
    
    def on_new_frame(self, data_dict):
        """新帧回调 - 详细输出所有数据（使用new_frame_with_data_listener）
        
        data_dict包含:
            - "mocap_data": MoCapFrame对象
            - "frame_number": 帧号
            - 其他元数据...
        """
        self.frame_count += 1
        
        print("\n" + "=" * 80)
        print(f"帧 #{self.frame_count}")
        print("=" * 80)
        
        # 提取真正的MoCapData对象
        print("\n【数据字典检查】")
        print(f"data_dict类型: {type(data_dict)}")
        print(f"data_dict包含的键: {data_dict.keys() if isinstance(data_dict, dict) else 'N/A'}")
        
        if "mocap_data" not in data_dict:
            print("❌ data_dict中缺少mocap_data键！")
            return
        
        mocap_data = data_dict["mocap_data"]
        
        # 检查MoCapData对象
        print("\n【MoCapData对象检查】")
        print(f"mocap_data类型: {type(mocap_data)}")
        print(f"mocap_data属性: {dir(mocap_data)}")
        
        # 1. Markerset数据
        print("\n【Markerset数据检查】")
        if hasattr(mocap_data, 'marker_set_data'):
            marker_set_data = mocap_data.marker_set_data
            print(f"✅ marker_set_data存在: {marker_set_data}")
            
            if marker_set_data:
                self.has_markerset_data = True
                
                if hasattr(marker_set_data, 'marker_data_list'):
                    marker_data_list = marker_set_data.marker_data_list
                    print(f"   marker_data_list长度: {len(marker_data_list)}")
                    
                    for idx, marker_data in enumerate(marker_data_list):
                        print(f"\n   Markerset #{idx}:")
                        print(f"     类型: {type(marker_data)}")
                        print(f"     属性: {dir(marker_data)}")
                        
                        if hasattr(marker_data, 'model_name'):
                            model_name = marker_data.model_name
                            if isinstance(model_name, bytes):
                                model_name = model_name.decode('utf-8', errors='replace')
                            print(f"     Model Name: '{model_name}'")
                            self.markerset_names.add(model_name)
                        
                        if hasattr(marker_data, 'marker_pos_list'):
                            pos_list = marker_data.marker_pos_list
                            print(f"     标记数量: {len(pos_list)}")
                            
                            if pos_list:
                                # 计算质心
                                x_sum = sum(p[0] for p in pos_list if p and len(p) >= 3)
                                y_sum = sum(p[1] for p in pos_list if p and len(p) >= 3)
                                z_sum = sum(p[2] for p in pos_list if p and len(p) >= 3)
                                count = len(pos_list)
                                
                                if count > 0:
                                    centroid = (x_sum/count, y_sum/count, z_sum/count)
                                    print(f"     质心位置: X={centroid[0]:.3f}, Y={centroid[1]:.3f}, Z={centroid[2]:.3f}")
                                
                                # 显示前3个标记的位置
                                for i, pos in enumerate(pos_list[:3]):
                                    if pos and len(pos) >= 3:
                                        print(f"       Marker {i}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
                else:
                    print("   ⚠️  marker_data_list属性不存在")
            else:
                print("   ⚠️  marker_set_data为None")
        else:
            print("❌ marker_set_data属性不存在")
        
        # 2. 骨骼数据
        print("\n【Skeleton数据检查】")
        if hasattr(mocap_data, 'skeleton_data'):
            skeleton_data = mocap_data.skeleton_data
            print(f"✅ skeleton_data存在: {skeleton_data}")
            
            if skeleton_data:
                self.has_skeleton_data = True
                
                if hasattr(skeleton_data, 'skeleton_list'):
                    skeleton_list = skeleton_data.skeleton_list
                    print(f"   skeleton_list长度: {len(skeleton_list)}")
                    
                    for idx, skeleton in enumerate(skeleton_list):
                        print(f"\n   Skeleton #{idx}:")
                        print(f"     类型: {type(skeleton)}")
                        
                        if hasattr(skeleton, 'id_num'):
                            print(f"     ID: {skeleton.id_num}")
                        
                        if hasattr(skeleton, 'name'):
                            name = skeleton.name
                            if isinstance(name, bytes):
                                name = name.decode('utf-8', errors='replace')
                            print(f"     Name: '{name}'")
                            self.skeleton_names.add(name)
                        
                        if hasattr(skeleton, 'rigid_body_list'):
                            joints = skeleton.rigid_body_list
                            print(f"     关节数量: {len(joints)}")
                            
                            # 显示前3个关节
                            for i, joint in enumerate(joints[:3]):
                                if hasattr(joint, 'name'):
                                    joint_name = joint.name
                                    if isinstance(joint_name, bytes):
                                        joint_name = joint_name.decode('utf-8', errors='replace')
                                else:
                                    joint_name = "Unknown"
                                
                                if hasattr(joint, 'pos'):
                                    pos = joint.pos
                                    print(f"       Joint {i} ({joint_name}): ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
                else:
                    print("   ⚠️  skeleton_list属性不存在")
            else:
                print("   ⚠️  skeleton_data为None")
        else:
            print("❌ skeleton_data属性不存在")
        
        # 3. 刚体数据
        print("\n【RigidBody数据检查】")
        if hasattr(mocap_data, 'rigid_body_data'):
            rigidbody_data = mocap_data.rigid_body_data
            print(f"✅ rigid_body_data存在: {rigidbody_data}")
            
            if rigidbody_data:
                self.has_rigidbody_data = True
                
                if hasattr(rigidbody_data, 'rigid_body_list'):
                    rigidbody_list = rigidbody_data.rigid_body_list
                    print(f"   rigid_body_list长度: {len(rigidbody_list)}")
                    
                    # 只显示前5个刚体
                    for idx, rb in enumerate(rigidbody_list[:5]):
                        if hasattr(rb, 'id_num'):
                            rb_id = rb.id_num
                            self.rigidbody_ids.add(rb_id)
                        else:
                            rb_id = "Unknown"
                        
                        if hasattr(rb, 'pos'):
                            pos = rb.pos
                            print(f"   RigidBody {rb_id}: ({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})")
                else:
                    print("   ⚠️  rigid_body_list属性不存在")
            else:
                print("   ⚠️  rigid_body_data为None")
        else:
            print("❌ rigid_body_data属性不存在")
        
        # 统计摘要
        if self.frame_count == 1:
            print("\n" + "=" * 80)
            print("首帧数据摘要")
            print("=" * 80)
            print(f"Markerset数据: {'✅ 有' if self.has_markerset_data else '❌ 无'}")
            print(f"Skeleton数据: {'✅ 有' if self.has_skeleton_data else '❌ 无'}")
            print(f"RigidBody数据: {'✅ 有' if self.has_rigidbody_data else '❌ 无'}")
    
    def run(self):
        """运行诊断"""
        print("\n" + "=" * 80)
        print("NatNet数据流诊断工具")
        print("=" * 80)
        print("\n此工具将连接到Motive并详细输出所有接收到的数据")
        print("用于诊断数据流问题\n")
        
        # 配置
        server_ip = "192.168.3.58"
        client_ip = "192.168.3.55"
        use_multicast = True
        
        print(f"配置:")
        print(f"  服务器IP: {server_ip}")
        print(f"  客户端IP: {client_ip}")
        print(f"  组播模式: {use_multicast}")
        print()
        
        # 创建NatNet客户端
        print("🔗 正在连接NatNet...")
        self.client = NatNetClient()
        self.client.set_client_address(client_ip)
        self.client.set_server_address(server_ip)
        self.client.set_use_multicast(use_multicast)
        
        # 设置回调（使用new_frame_with_data_listener获取完整MoCapData对象）
        self.client.new_frame_with_data_listener = self.on_new_frame
        
        # 启动
        if not self.client.run('d'):
            print("❌ 无法启动NatNet客户端")
            return
        
        # 等待连接
        print("⏳ 等待连接...")
        time.sleep(2)
        
        if not self.client.connected():
            print("❌ 无法连接到OptiTrack服务器")
            print("\n请检查:")
            print("1. Motive是否正在运行")
            print("2. 流设置是否正确启用")
            print("3. IP地址是否正确")
            print("4. 网络连接是否正常")
            return
        
        print("✅ NatNet客户端已连接\n")
        print("=" * 80)
        print("开始接收数据（将显示前5帧的详细信息）")
        print("按Ctrl+C退出")
        print("=" * 80)
        
        self.start_time = time.time()
        
        try:
            # 运行一段时间，捕获前5帧的详细信息
            max_frames = 5
            while self.frame_count < max_frames:
                time.sleep(0.1)
            
            # 最终统计
            print("\n" + "=" * 80)
            print("诊断完成 - 最终统计")
            print("=" * 80)
            
            duration = time.time() - self.start_time
            fps = self.frame_count / duration if duration > 0 else 0
            
            print(f"\n运行时间: {duration:.1f}秒")
            print(f"总帧数: {self.frame_count}")
            print(f"帧率: {fps:.1f} FPS")
            
            print(f"\n数据类型摘要:")
            print(f"  Markerset数据: {'✅ 检测到' if self.has_markerset_data else '❌ 未检测到'}")
            print(f"  Skeleton数据: {'✅ 检测到' if self.has_skeleton_data else '❌ 未检测到'}")
            print(f"  RigidBody数据: {'✅ 检测到' if self.has_rigidbody_data else '❌ 未检测到'}")
            
            if self.markerset_names:
                print(f"\n检测到的Markerset名称:")
                for name in sorted(self.markerset_names):
                    print(f"  - '{name}'")
            
            if self.skeleton_names:
                print(f"\n检测到的Skeleton名称:")
                for name in sorted(self.skeleton_names):
                    print(f"  - '{name}'")
            
            if self.rigidbody_ids:
                print(f"\n检测到的RigidBody ID: {sorted(self.rigidbody_ids)}")
            
            # 诊断建议
            print("\n" + "=" * 80)
            print("诊断建议")
            print("=" * 80)
            
            if not self.has_markerset_data and not self.has_skeleton_data:
                print("\n⚠️  未检测到Markerset或Skeleton数据！")
                print("\n可能的原因:")
                print("1. Motive中未创建Markerset或Skeleton对象")
                print("2. 流设置中未启用相应数据类型")
                print("3. 对象未被正确跟踪（标记为红色）")
                print("\n解决方法:")
                print("1. 在Motive中创建Markerset（命名为Sub001）")
                print("2. 打开 编辑 > 设置 > 流设置")
                print("3. 确保勾选了 'Marker Set'（标记集）或 'Skeleton'（骨骼）")
                print("4. 确保对象正在被跟踪（绿色状态）")
            
            elif not self.has_markerset_data:
                print("\n⚠️  未检测到Markerset数据（但有其他数据）")
                print("如果您想使用Markerset跟踪，请:")
                print("1. 在Motive的流设置中启用 'Marker Set'")
                print("2. 确保Markerset对象已创建并正在被跟踪")
            
            elif "Sub001" not in self.markerset_names and "Sub001" not in self.skeleton_names:
                print("\n⚠️  未检测到名为'Sub001'的对象")
                print(f"检测到的对象名称: {self.markerset_names | self.skeleton_names}")
                print("\n解决方法:")
                print("1. 在Motive中将Markerset或Skeleton重命名为'Sub001'")
                print("2. 或修改测试程序中的skeleton_name变量")
            
            else:
                print("\n✅ 数据流正常！")
                print("如果PsychoPy仍无法显示，请检查:")
                print("1. 测试程序中的skeleton_name是否匹配")
                print("2. 坐标转换是否正确")
                print("3. PsychoPy窗口是否正常创建")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断")
        
        finally:
            # 清理
            if self.client:
                self.client.shutdown()
            print("\n✅ 诊断完成")


if __name__ == '__main__':
    diagnostic = NatNetDiagnostic()
    diagnostic.run()

