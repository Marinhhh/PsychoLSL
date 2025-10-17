#============================================================================= #type: ignore  # noqa E501
# 版权所有 © 2025 NaturalPoint, Inc. 保留所有权利。
#
# 本软件受 OPTITRACK 插件 EULA（最终用户许可协议）约束，可在 https://www.optitrack.com/about/legal/eula.html #type: ignore  # noqa E501
# 查看，和/或可与相关软件文件一起下载（"插件 EULA"）。通过下载、安装、激活 #type: ignore  # noqa E501
# 和/或以其他方式使用软件，您同意您已阅读并同意遵守 #type: ignore  # noqa E501
# 插件 EULA 和所有适用的法律法规。如果您不同意受插件 EULA 约束， #type: ignore  # noqa E501
# 则您不得下载、安装、激活或以其他方式使用软件，并且您必须立即删除或 #type: ignore  # noqa E501
# 退回软件。如果您代表一个实体下载、安装、激活和/或以其他方式使用软件， #type: ignore  # noqa E501
# 那么这样做即表示并保证您有适当的权限代表该实体接受插件 EULA。 #type: ignore  # noqa E501
# 请参阅根目录中的许可文件以了解其他管理条款和信息。 #type: ignore  # noqa E501
#============================================================================= #type: ignore  # noqa E501


# OptiTrack NatNet 直接解包 Python 3.x 示例
#
# 使用 Python NatNetClient.py 库来建立
# 连接并通过 NatNet 连接接收数据
# 使用 NatNetClientLibrary 进行解码。

import sys
import time
from NatNetClient import NatNetClient
import DataDescriptions
import MoCapData

# 这是一个回调函数，连接到 NatNet 客户端
# 每个动作捕捉帧调用一次。


def receive_new_frame(data_dict):
    order_list = ["frameNumber", "markerSetCount", "unlabeledMarkersCount", #type: ignore  # noqa F841
                  "rigidBodyCount", "skeletonCount", "labeledMarkerCount",
                  "timecode", "timecodeSub", "timestamp", "isRecording",
                  "trackedModelsChanged"]
    dump_args = False
    if dump_args is True:
        out_string = "    "
        for key in data_dict:
            out_string += key + "= "
            if key in data_dict:
                out_string += data_dict[key] + " "
            out_string += "/"
        print(out_string)


def receive_new_frame_with_data(data_dict):
    order_list = ["frameNumber", "markerSetCount", "unlabeledMarkersCount", #type: ignore  # noqa F841
                  "rigidBodyCount", "skeletonCount", "labeledMarkerCount",
                  "timecode", "timecodeSub", "timestamp", "isRecording",
                  "trackedModelsChanged", "offset", "mocap_data"]
    dump_args = True
    if dump_args is True:
        out_string = "    "
        for key in data_dict:
            out_string += key + "= "
            if key in data_dict:
                out_string += str(data_dict[key]) + " "
            out_string += "/"
        print(out_string)


# 这是一个连接到 NatNet 客户端的回调函数。
# 每帧每个刚体调用一次。
def receive_rigid_body_frame(new_id, position, rotation):
    pass
    # print("接收到刚体的帧", new_id)
    # print("接收到刚体的帧", new_id," ",position," ",rotation)


def add_lists(totals, totals_tmp):
    totals[0] += totals_tmp[0]
    totals[1] += totals_tmp[1]
    totals[2] += totals_tmp[2]
    return totals


def print_configuration(natnet_client):
    natnet_client.refresh_configuration()
    print("连接配置:")
    print("  客户端:          %s" % natnet_client.local_ip_address)
    print("  服务器:          %s" % natnet_client.server_ip_address)
    print("  命令端口:        %d" % natnet_client.command_port)
    print("  数据端口:        %d" % natnet_client.data_port)

    changeBitstreamString = "  可以更改位流版本 = "
    if natnet_client.use_multicast:
        print("  使用组播")
        print("  组播组: %s" % natnet_client.multicast_address)
        changeBitstreamString += "false"
    else:
        print("  使用单播")
        changeBitstreamString += "true"

    # NatNet 服务器信息
    application_name = natnet_client.get_application_name()
    nat_net_requested_version = natnet_client.get_nat_net_requested_version()
    nat_net_version_server = natnet_client.get_nat_net_version_server()
    server_version = natnet_client.get_server_version()

    print("  NatNet 服务器信息")
    print("    应用程序名称 %s" % (application_name))
    print("    Motive版本  %d %d %d %d" % (server_version[0], server_version[1], server_version[2], server_version[3]))  #type: ignore  # noqa F501
    print("    NatNet版本  %d %d %d %d" % (nat_net_version_server[0], nat_net_version_server[1], nat_net_version_server[2], nat_net_version_server[3])) #type: ignore  # noqa F501
    print("  NatNet 位流请求")
    print("    NatNet版本  %d %d %d %d" % (nat_net_requested_version[0], nat_net_requested_version[1], #type: ignore  # noqa F501
                                              nat_net_requested_version[2], nat_net_requested_version[3])) #type: ignore  # noqa F501

    print(changeBitstreamString)
    # print("command_socket = %s" % (str(natnet_client.command_socket)))
    # print("data_socket    = %s" % (str(natnet_client.data_socket)))
    print("  Python版本    %s" % (sys.version))


def print_commands(can_change_bitstream):
    outstring = "命令:\n"
    outstring += "从 Motive 返回数据\n"
    outstring += "  s  发送数据描述\n"
    outstring += "  r  恢复/开始帧播放\n"
    outstring += "  p  暂停帧播放\n"
    outstring += "     暂停可能需要几秒钟\n"
    outstring += "     取决于帧数据大小\n"
    outstring += "更改工作范围\n"
    outstring += "  o  重置工作范围为: 开始/当前/结束帧 0/0/take结束\n" #type: ignore  # noqa F501
    outstring += "  w  设置工作范围为: 开始/当前/结束帧 1/100/1500\n" #type: ignore  # noqa F501
    outstring += "返回数据显示模式\n"
    outstring += "  j  print_level = 0 抑制数据描述和动作捕捉帧数据\n" #type: ignore  # noqa F501
    outstring += "  k  print_level = 1 显示数据描述和动作捕捉帧数据\n" #type: ignore  # noqa F501
    outstring += "  l  print_level = 20 显示数据描述和每20个动作捕捉帧数据\n" #type: ignore  # noqa F501
    outstring += "更改 NatNet 数据流版本（仅单播）\n"
    outstring += "  3  请求 NatNet 3.1 数据流（仅单播）\n"
    outstring += "  4  请求 NatNet 4.1 数据流（仅单播）\n"
    outstring += "常规\n"
    outstring += "  t  数据结构自测试（无 motive/服务器交互）\n" #type: ignore  # noqa F501
    outstring += "  c  打印配置\n"
    outstring += "  h  打印命令\n"
    outstring += "  q  退出\n"
    outstring += "\n"
    outstring += "注意: Motive 帧播放在端点、循环和反弹播放模式下\n"
    outstring += "       会有不同的响应。\n"
    outstring += "\n"
    outstring += "示例: PacketClient [服务器IP [ 客户端IP [ 组播/单播]]]\n" #type: ignore  # noqa F501
    outstring += "         PacketClient \"192.168.10.14\" \"192.168.10.14\" Multicast\n" #type: ignore  # noqa F501
    outstring += "         PacketClient \"127.0.0.1\" \"127.0.0.1\" u\n"
    outstring += "\n"
    print(outstring)


def request_data_descriptions(s_client):
    # 请求模型定义
    s_client.send_request(s_client.command_socket, s_client.NAT_REQUEST_MODELDEF, "",  (s_client.server_ip_address, s_client.command_port)) #type: ignore  # noqa F501


def test_classes():
    totals = [0, 0, 0]
    print("测试数据描述类")
    totals_tmp = DataDescriptions.test_all()
    totals = add_lists(totals, totals_tmp)
    print("")
    print("测试动作捕捉帧类")
    totals_tmp = MoCapData.test_all()
    totals = add_lists(totals, totals_tmp)
    print("")
    print("所有测试总计")
    print("--------------------")
    print("[通过] 计数 = %3.1d" % totals[0])
    print("[失败] 计数 = %3.1d" % totals[1])
    print("[跳过] 计数 = %3.1d" % totals[2])


def my_parse_args(arg_list, args_dict):
    # 设置基本值
    arg_list_len = len(arg_list)
    if arg_list_len > 1:
        args_dict["serverAddress"] = arg_list[1]
        if arg_list_len > 2:
            args_dict["clientAddress"] = arg_list[2]
        if arg_list_len > 3:
            if len(arg_list[3]):
                args_dict["use_multicast"] = True
                if arg_list[3][0].upper() == "U":
                    args_dict["use_multicast"] = False
        if arg_list_len > 4:
            args_dict["stream_type"] = arg_list[4]
    return args_dict


if __name__ == "__main__":

    optionsDict = {}
    optionsDict["clientAddress"] = "127.0.0.1"
    optionsDict["serverAddress"] = "127.0.0.1"
    optionsDict["use_multicast"] = None
    optionsDict["stream_type"] = None
    stream_type_arg = None

    # 这将创建一个新的 NatNet 客户端
    optionsDict = my_parse_args(sys.argv, optionsDict)
    streaming_client = NatNetClient()
    streaming_client.set_client_address(optionsDict["clientAddress"])
    streaming_client.set_server_address(optionsDict["serverAddress"])

    # 流客户端配置。
    # 在模拟器上调用刚体处理程序进行数据传输。
    streaming_client.new_frame_listener = receive_new_frame
    # streaming_client.new_frame_with_data_listener = receive_new_frame_with_data  # type ignore # noqa E501
    streaming_client.rigid_body_listener = receive_rigid_body_frame

    # 打印说明
    print("NatNet Python 客户端 4.3\n")

    # 选择组播或单播
    cast_choice = input("选择 0 进行组播，选择 1 进行单播: ")
    cast_choice = int(cast_choice)
    while cast_choice != 0 and cast_choice != 1:
        cast_choice = input("无效选项。选择 0 进行组播或选择 1 进行单播: ") #type: ignore  # noqa F501
        cast_choice = int(cast_choice)
    # 建立组播或单播
    if cast_choice == 0:
        optionsDict["use_multicast"] = True
    else:
        optionsDict["use_multicast"] = False
    streaming_client.set_use_multicast(optionsDict["use_multicast"])

    # 允许用户设置本地地址:
    client_addr_choice = input("客户端地址 (192.168.3.55): ") #127.0.0.1
    if client_addr_choice != "":
        streaming_client.set_client_address(client_addr_choice)

    # 允许用户设置远程地址
    server_addr_choice = input("服务器地址 (192.168.3.58): ") #127.0.0.1
    if server_addr_choice != "":
        streaming_client.set_server_address(server_addr_choice)

    # 选择数据流偏好
    stream_choice = None
    while stream_choice != 'd' and stream_choice != 'c':
        stream_choice = input("选择 d 进行数据流，选择 c 进行命令流: ") #type: ignore  # noqa F501
    optionsDict["stream_type"] = stream_choice

    # 现在回调已设置，启动流客户端。
    # 这将持续运行，并在单独的线程上操作。
    is_running = streaming_client.run(optionsDict["stream_type"])
    if not is_running:
        print("错误: 无法启动流客户端。")
        try:
            sys.exit(1)
        except SystemExit:
            print("...")
        finally:
            print("正在退出")

    is_looping = True
    time.sleep(1)
    if streaming_client.connected() is False:
        print("错误: 无法正确连接。检查 Motive 流是否已开启。") #type: ignore  # noqa F501
        try:
            sys.exit(2)
        except SystemExit:
            print("...")
        finally:
            print("正在退出")

    print_configuration(streaming_client)
    print("\n")
    print_commands(streaming_client.can_change_bitstream_version())

    while is_looping:
        inchars = input('输入命令或按 (\'h\' 查看命令列表)\n')
        if len(inchars) > 0:
            c1 = inchars[0].lower()
            if c1 == 'h':
                print_commands(streaming_client.can_change_bitstream_version())
            elif c1 == 'c':
                print_configuration(streaming_client)
            elif c1 == 's':
                request_data_descriptions(streaming_client)
                time.sleep(1)
            elif (c1 == '3') or (c1 == '4'):
                if streaming_client.can_change_bitstream_version():
                    tmp_major = 4
                    tmp_minor = 2
                    if (c1 == '3'):
                        tmp_major = 3
                        tmp_minor = 1
                    return_code = streaming_client.set_nat_net_version(tmp_major, tmp_minor) #type: ignore  # noqa F501
                    time.sleep(1)
                    if return_code == -1:
                        print("无法将位流版本更改为 %d.%d" % (tmp_major, tmp_minor)) #type: ignore  # noqa F501
                    else:
                        print("位流版本为 %d.%d" % (tmp_major, tmp_minor)) #type: ignore  # noqa F501
                else:
                    print("只能在单播模式下更改位流")

            elif c1 == 'p':
                sz_command = "TimelineStop"
                return_code = streaming_client.send_command(sz_command)
                time.sleep(1)
                print("命令: %s - 返回代码: %d" % (sz_command, return_code)) #type: ignore  # noqa F501
            elif c1 == 'r':
                sz_command = "TimelinePlay"
                return_code = streaming_client.send_command(sz_command)
                print("命令: %s - 返回代码: %d" % (sz_command, return_code)) #type: ignore  # noqa F501
            elif c1 == 'o':
                tmpCommands = ["TimelinePlay",
                               "TimelineStop",
                               "SetPlaybackStartFrame,0",
                               "SetPlaybackStopFrame,1000000",
                               "SetPlaybackLooping,0",
                               "SetPlaybackCurrentFrame,0",
                               "TimelineStop"]
                for sz_command in tmpCommands:
                    return_code = streaming_client.send_command(sz_command)
                    print("命令: %s - 返回代码: %d" % (sz_command, return_code)) #type: ignore  # noqa F501
                time.sleep(1)
            elif c1 == 'w':
                tmp_commands = ["TimelinePlay",
                                "TimelineStop",
                                "SetPlaybackStartFrame,1",
                                "SetPlaybackStopFrame,1500",
                                "SetPlaybackLooping,0",
                                "SetPlaybackCurrentFrame,100",
                                "TimelineStop"]
                for sz_command in tmp_commands:
                    return_code = streaming_client.send_command(sz_command)
                    print("命令: %s - 返回代码: %d" % (sz_command, return_code)) #type: ignore  # noqa F501
                time.sleep(1)
            elif c1 == 't':
                test_classes()

            elif c1 == 'j':
                streaming_client.set_print_level(0)
                print("仅显示接收到的帧号并抑制数据描述") #type: ignore  # noqa F501
            elif c1 == 'k':
                streaming_client.set_print_level(1)
                print("显示每个接收到的帧")

            elif c1 == 'l':
                print_level = streaming_client.set_print_level(20)
                print_level_mod = print_level % 100
                if (print_level == 0):
                    print("仅显示接收到的帧号并抑制数据描述") #type: ignore  # noqa F501
                elif (print_level == 1):
                    print("显示每一帧")
                elif (print_level_mod == 1):
                    print("显示每第 %d 帧" % print_level)
                elif (print_level_mod == 2):
                    print("显示每第 %d 帧" % print_level)
                elif (print_level == 3):
                    print("显示每第 %d 帧" % print_level)
                else:
                    print("显示每第 %d 帧" % print_level)

            elif c1 == 'q':
                is_looping = False
                streaming_client.shutdown()
                break
            else:
                print("错误: 命令 %s 未识别" % c1)
            print("准备好了...\n")
    print("正在退出")
