//=============================================================================
// 版权所有 © 2025 NaturalPoint, Inc. 保留所有权利。
// 
// 本软件受 OPTITRACK 插件 EULA（最终用户许可协议）约束，可在 https://www.optitrack.com/about/legal/eula.html 
// 查看，和/或可与相关软件文件一起下载（"插件 EULA"）。通过下载、安装、激活
// 和/或以其他方式使用软件，您同意您已阅读并同意遵守
// 插件 EULA 和所有适用的法律法规。如果您不同意受插件 EULA 约束，
// 则您不得下载、安装、激活或以其他方式使用软件，并且您必须立即删除或
// 退回软件。如果您代表一个实体下载、安装、激活和/或以其他方式使用软件，
// 那么这样做即表示并保证您有适当的权限代表该实体接受插件 EULA。
// 请参阅根目录中的许可文件以了解其他管理条款和信息。
//=============================================================================

/*********************************************************************
 * \page   MinimalClient.cpp
 * \file   MinimalClient.cpp
 * \brief  连接到 Motive 并获取数据所需的*最少*代码量。
 * 有关具有附加功能的更完整示例，请参阅
 * NatNet SDK 中的 SampleClient.cpp 示例
 *********************************************************************/

// 使用 STL 进行跨平台睡眠
#include <thread>

// NatNet SDK 包含
#include "../../include/NatNetTypes.h"
#include "../../include/NatNetCAPI.h"
#include "../../include/NatNetClient.h"

void NATNET_CALLCONV DataHandler(sFrameOfMocapData* data, void* pUserData);    // 从服务器接收数据
void PrintData(sFrameOfMocapData* data, NatNetClient* pClient);
void PrintDataDescriptions(sDataDescriptions* pDataDefs);

NatNetClient* g_pClient = nullptr;
sNatNetClientConnectParams g_connectParams;
sServerDescription g_serverDescription;
sDataDescriptions* g_pDataDefs = nullptr;

/**
 * \brief 最小客户端示例。
 * 
 * \param argc
 * \param argv
 * \return 返回 NatNetTypes 错误代码。
 */
int main(int argc, char* argv[])
{
    ErrorCode ret = ErrorCode_OK;

    // 创建一个 NatNet 客户端
    g_pClient = new NatNetClient();

    // 设置客户端的帧回调处理程序
    ret = g_pClient->SetFrameReceivedCallback(DataHandler, g_pClient);	

    // 指定客户端 PC 的 IP 地址、Motive PC 的 IP 地址和网络连接类型
    g_connectParams.localAddress = "127.0.0.1";
    g_connectParams.serverAddress = "127.0.0.1";
    g_connectParams.connectionType = ConnectionType_Multicast;

    // 连接到 Motive
    ret = g_pClient->Connect(g_connectParams);
    
    if (ret != ErrorCode_OK)
    {
        try {
            //尝试单播形式
            g_connectParams.localAddress = "127.0.0.1";
            g_connectParams.serverAddress = "127.0.0.1";
            g_connectParams.connectionType = ConnectionType_Unicast;
            ret = g_pClient->Connect(g_connectParams);
        }
        //捕获任何其他错误
        catch (...) {
            // 连接失败
            printf("无法连接到服务器。错误代码: %d。正在退出。\n", ret);
            return 1;
        } 
    }
    

     
    // 获取 Motive 服务器描述
    memset(&g_serverDescription, 0, sizeof(g_serverDescription));
    ret = g_pClient->GetServerDescription(&g_serverDescription);
    if (ret != ErrorCode_OK || !g_serverDescription.HostPresent)
    {
        printf("无法获取服务器描述。错误代码:%d。正在退出。\n", ret);
        return 1;
    }
    else
    {
        printf("已连接 : %s (版本 %d.%d.%d.%d)\n", g_serverDescription.szHostApp, g_serverDescription.HostAppVersion[0],
            g_serverDescription.HostAppVersion[1], g_serverDescription.HostAppVersion[2], g_serverDescription.HostAppVersion[3]);
    }

    // 从 Motive 获取当前活动资产列表
    ret = g_pClient->GetDataDescriptionList(&g_pDataDefs);
    if (ret != ErrorCode_OK || g_pDataDefs == NULL)
    {
        printf("获取资产列表时出错。错误代码:%d 正在退出。\n", ret);
        return 1;
    }
    else
    {
        PrintDataDescriptions(g_pDataDefs);
    }

    printf("\n客户端已连接并正在监听数据...\n");
    
    // 在主应用程序线程上做一些事情...
    while (true)
    {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    // 清理
    if (g_pClient)
    {
        g_pClient->Disconnect();
        delete g_pClient;
    }
    
    if (g_pDataDefs)
    {
        NatNet_FreeDescriptions(g_pDataDefs);
        g_pDataDefs = NULL;
    }

    return ErrorCode_OK;
}

/**
 * DataHandler 在每当有动作捕捉数据帧可用时，由 NatNet 在单独的网络处理
 * 线程上调用。
 * 因此，在 100 动作捕捉 fps 下，此函数应该大约每 10ms 调用一次。
 * \brief NatNet 调用的 DataHandler
 * \param data 输入的动作捕捉数据帧
 * \param pUserData
 * \return 
 */
void NATNET_CALLCONV DataHandler(sFrameOfMocapData* data, void* pUserData)
{
    NatNetClient* pClient = (NatNetClient*)pUserData;
    PrintData(data, pClient);

    return;
}

/**
 * \brief 打印出当前 Motive 活动资产描述。
 * 
 * \param pDataDefs
 */
void PrintDataDescriptions(sDataDescriptions* pDataDefs)
{
    printf("检索到 %d 个数据描述:\n", pDataDefs->nDataDescriptions);
    for (int i = 0; i < pDataDefs->nDataDescriptions; i++)
    {
        printf("---------------------------------\n");
        printf("数据描述 # %d (类型=%d)\n", i, pDataDefs->arrDataDescriptions[i].type);
        if (pDataDefs->arrDataDescriptions[i].type == Descriptor_MarkerSet)
        {
            // 标记集
            sMarkerSetDescription* pMS = pDataDefs->arrDataDescriptions[i].Data.MarkerSetDescription;
            printf("标记集名称 : %s\n", pMS->szName);
            for (int i = 0; i < pMS->nMarkers; i++)
                printf("%s\n", pMS->szMarkerNames[i]);

        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_RigidBody)
        {
            // 刚体
            sRigidBodyDescription* pRB = pDataDefs->arrDataDescriptions[i].Data.RigidBodyDescription;
            printf("刚体名称 : %s\n", pRB->szName);
            printf("刚体 ID : %d\n", pRB->ID);
            printf("刚体父级 ID : %d\n", pRB->parentID);
            printf("父级偏移 : %3.2f,%3.2f,%3.2f\n", pRB->offsetx, pRB->offsety, pRB->offsetz);

            if (pRB->MarkerPositions != NULL && pRB->MarkerRequiredLabels != NULL)
            {
                for (int markerIdx = 0; markerIdx < pRB->nMarkers; ++markerIdx)
                {
                    const MarkerData& markerPosition = pRB->MarkerPositions[markerIdx];
                    const int markerRequiredLabel = pRB->MarkerRequiredLabels[markerIdx];

                    printf("\t标记 #%d:\n", markerIdx);
                    printf("\t\t位置: %.2f, %.2f, %.2f\n", markerPosition[0], markerPosition[1], markerPosition[2]);

                    if (markerRequiredLabel != 0)
                    {
                        printf("\t\t需要的活动标签: %d\n", markerRequiredLabel);
                    }
                }
            }
        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_Skeleton)
        {
            // 骨骼
            sSkeletonDescription* pSK = pDataDefs->arrDataDescriptions[i].Data.SkeletonDescription;
            printf("骨骼名称 : %s\n", pSK->szName);
            printf("骨骼 ID : %d\n", pSK->skeletonID);
            printf("刚体（骨骼）数量 : %d\n", pSK->nRigidBodies);
            for (int j = 0; j < pSK->nRigidBodies; j++)
            {
                sRigidBodyDescription* pRB = &pSK->RigidBodies[j];
                printf("  刚体名称 : %s\n", pRB->szName);
                printf("  刚体 ID : %d\n", pRB->ID);
                printf("  刚体父级 ID : %d\n", pRB->parentID);
                printf("  父级偏移 : %3.2f,%3.2f,%3.2f\n", pRB->offsetx, pRB->offsety, pRB->offsetz);
            }
        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_Asset)
        {
            // 训练标记集
            sAssetDescription* pAsset = pDataDefs->arrDataDescriptions[i].Data.AssetDescription;
            printf("训练标记集名称 : %s\n", pAsset->szName);
            printf("资产 ID : %d\n", pAsset->AssetID);

            // 训练标记集刚体（骨骼）数量
            printf("训练标记集刚体（骨骼）数量 : %d\n", pAsset->nRigidBodies);
            for (int j = 0; j < pAsset->nRigidBodies; j++)
            {
                sRigidBodyDescription* pRB = &pAsset->RigidBodies[j];
                printf("  刚体名称 : %s\n", pRB->szName);
                printf("  刚体 ID : %d\n", pRB->ID);
                printf("  刚体父级 ID : %d\n", pRB->parentID);
                printf("  父级偏移 : %3.2f,%3.2f,%3.2f\n", pRB->offsetx, pRB->offsety, pRB->offsetz);
            }

            // 训练标记集标记数量
            printf("训练标记集标记数量 : %d\n", pAsset->nMarkers);
            for (int j = 0; j < pAsset->nMarkers; j++)
            {
                sMarkerDescription marker = pAsset->Markers[j];
                int modelID, markerID;
                NatNet_DecodeID(marker.ID, &modelID, &markerID);
                printf("  标记名称 : %s\n", marker.szName);
                printf("  标记 ID   : %d\n", markerID);
            }
        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_ForcePlate)
        {
            // 力板
            sForcePlateDescription* pFP = pDataDefs->arrDataDescriptions[i].Data.ForcePlateDescription;
            printf("力板 ID : %d\n", pFP->ID);
            printf("力板序列号 : %s\n", pFP->strSerialNo);
            printf("力板宽度 : %3.2f\n", pFP->fWidth);
            printf("力板长度 : %3.2f\n", pFP->fLength);
            printf("力板电气中心偏移 (%3.3f, %3.3f, %3.3f)\n", pFP->fOriginX, pFP->fOriginY, pFP->fOriginZ);
            for (int iCorner = 0; iCorner < 4; iCorner++)
                printf("力板角 %d : (%3.4f, %3.4f, %3.4f)\n", iCorner, pFP->fCorners[iCorner][0], pFP->fCorners[iCorner][1], pFP->fCorners[iCorner][2]);
            printf("力板类型 : %d\n", pFP->iPlateType);
            printf("力板数据类型 : %d\n", pFP->iChannelDataType);
            printf("力板通道数量 : %d\n", pFP->nChannels);
            for (int iChannel = 0; iChannel < pFP->nChannels; iChannel++)
                printf("\t通道 %d : %s\n", iChannel, pFP->szChannelNames[iChannel]);
        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_Device)
        {
            // 外围设备
            sDeviceDescription* pDevice = pDataDefs->arrDataDescriptions[i].Data.DeviceDescription;
            printf("设备名称 : %s\n", pDevice->strName);
            printf("设备序列号 : %s\n", pDevice->strSerialNo);
            printf("设备 ID : %d\n", pDevice->ID);
            printf("设备通道数量 : %d\n", pDevice->nChannels);
            for (int iChannel = 0; iChannel < pDevice->nChannels; iChannel++)
                printf("\t通道 %d : %s\n", iChannel, pDevice->szChannelNames[iChannel]);
        }
        else if (pDataDefs->arrDataDescriptions[i].type == Descriptor_Camera)
        {
            // 相机
            sCameraDescription* pCamera = pDataDefs->arrDataDescriptions[i].Data.CameraDescription;
            printf("相机名称 : %s\n", pCamera->strName);
            printf("相机位置 (%3.2f, %3.2f, %3.2f)\n", pCamera->x, pCamera->y, pCamera->z);
            printf("相机方向 (%3.2f, %3.2f, %3.2f, %3.2f)\n", pCamera->qx, pCamera->qy, pCamera->qz, pCamera->qw);
        }
        else
        {
            // 未知
            printf("未知数据类型。\n");
        }
    }
}

/**
 * \brief 打印出单个动作捕捉数据帧。
 * 
 * \param data
 * \param pClient
 */
void PrintData(sFrameOfMocapData* data, NatNetClient* pClient)
{
    printf("\n=====================  New Packet Arrived  =============================\n");
    printf("FrameID : %d\n", data->iFrame);
    printf("Timestamp : %3.2lf\n", data->fTimestamp);
    
    // Rigid Bodies
    printf("------------------------\n");
    printf("Rigid Bodies [ Count = %d ]\n", data->nRigidBodies);
    for (int i = 0; i < data->nRigidBodies; i++)
    {
        // params
        bool bTrackingValid = data->RigidBodies[i].params & 0x01;
        int streamingID = data->RigidBodies[i].ID;
        printf("[ID=%d  Error=%3.4f  Tracked=%d]\n", streamingID, data->RigidBodies[i].MeanError, bTrackingValid);
        printf("\tx\ty\tz\tqx\tqy\tqz\tqw\n");
        printf("\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\n",
            data->RigidBodies[i].x,
            data->RigidBodies[i].y,
            data->RigidBodies[i].z,
            data->RigidBodies[i].qx,
            data->RigidBodies[i].qy,
            data->RigidBodies[i].qz,
            data->RigidBodies[i].qw);
    }

    // Skeletons
    printf("------------------------\n");
    printf("Skeletons [ Count = %d ]\n", data->nSkeletons);
    for (int i = 0; i < data->nSkeletons; i++)
    {
        sSkeletonData skData = data->Skeletons[i];
        printf("Skeleton [ID=%d  Bone count=%d]\n", skData.skeletonID, skData.nRigidBodies);
        for (int j = 0; j < skData.nRigidBodies; j++)
        {
            sRigidBodyData rbData = skData.RigidBodyData[j];
            printf("Bone %d\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\n",
                rbData.ID, rbData.x, rbData.y, rbData.z, rbData.qx, rbData.qy, rbData.qz, rbData.qw);
        }
    }

    // Trained Markerset Data (Motive 3.1 / NatNet 4.1 and later)
    printf("------------------------\n");
    printf("Assets [Count=%d]\n", data->nAssets);
    for (int i = 0; i < data->nAssets; i++)
    {
        sAssetData asset = data->Assets[i];
        printf("Trained Markerset [ID=%d  Bone count=%d   Marker count=%d]\n",
            asset.assetID, asset.nRigidBodies, asset.nMarkers);

        // Trained Markerset Rigid Bodies
        for (int j = 0; j < asset.nRigidBodies; j++)
        {
            // note : Trained markerset ids are of the form:
            // parent markerset ID  : high word (upper 16 bits of int)
            // rigid body id        : low word  (lower 16 bits of int)
            int assetID, rigidBodyID;
            sRigidBodyData rbData = asset.RigidBodyData[j];
            NatNet_DecodeID(rbData.ID, &assetID, &rigidBodyID);
            printf("Bone %d\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\t%3.2f\n",
                rigidBodyID, rbData.x, rbData.y, rbData.z, rbData.qx, rbData.qy, rbData.qz, rbData.qw);
        }

        // Trained Markerset markers
        for (int j = 0; j < asset.nMarkers; j++)
        {
            sMarker marker = asset.MarkerData[j];
            int assetID, markerID;
            NatNet_DecodeID(marker.ID, &assetID, &markerID);
            printf("Marker [AssetID=%d, MarkerID=%d] [size=%3.2f] [pos=%3.2f,%3.2f,%3.2f] [residual(mm)=%.4f]\n",
                assetID, markerID, marker.size, marker.x, marker.y, marker.z, marker.residual * 1000.0f);
        }
    }

    // Labeled markers - this includes all markers (Active, Passive, and 'unlabeled' (markers with no asset but a PointCloud ID)
    bool bUnlabeled;    // marker is 'unlabeled', but has a point cloud ID that matches Motive PointCloud ID (In Motive 3D View)
    bool bActiveMarker; // marker is an actively labeled LED marker
    printf("------------------------\n");
    printf("Markers [ Count = %d ]\n", data->nLabeledMarkers);
    for (int i = 0; i < data->nLabeledMarkers; i++)
    {
        bUnlabeled = ((data->LabeledMarkers[i].params & 0x10) != 0);
        bActiveMarker = ((data->LabeledMarkers[i].params & 0x20) != 0);
        sMarker marker = data->LabeledMarkers[i];
        int modelID, markerID;
        NatNet_DecodeID(marker.ID, &modelID, &markerID);
        char szMarkerType[512];
        if (bActiveMarker)
            strcpy_s(szMarkerType, "Active");
        else if (bUnlabeled)
            strcpy_s(szMarkerType, "Unlabeled");
        else
            strcpy_s(szMarkerType, "Labeled");
        printf("%s Marker [ModelID=%d, MarkerID=%d] [size=%3.2f] [pos=%3.2f,%3.2f,%3.2f]\n",
            szMarkerType, modelID, markerID, marker.size, marker.x, marker.y, marker.z);
    }

    // Force plates
    printf("------------------------\n");
    printf("Force Plates [ Count = %d ]\n", data->nForcePlates);
    for (int iPlate = 0; iPlate < data->nForcePlates; iPlate++)
    {
        printf("Force Plate %d\n", data->ForcePlates[iPlate].ID);
        for (int iChannel = 0; iChannel < data->ForcePlates[iPlate].nChannels; iChannel++)
        {
            printf("\tChannel %d:\t", iChannel);
            if (data->ForcePlates[iPlate].ChannelData[iChannel].nFrames == 0)
            {
                printf("\tEmpty Frame\n");
            }
            for (int iSample = 0; iSample < data->ForcePlates[iPlate].ChannelData[iChannel].nFrames; iSample++)
                printf("%3.2f\t", data->ForcePlates[iPlate].ChannelData[iChannel].Values[iSample]);
            printf("\n");
        }
    }

    // Peripheral Devices (e.g. NIDAQ, Glove, EMG)
    printf("------------------------\n");
    printf("Devices [ Count = %d ]\n", data->nDevices);
    for (int iDevice = 0; iDevice < data->nDevices; iDevice++)
    {
        printf("Device %d\n", data->Devices[iDevice].ID);
        for (int iChannel = 0; iChannel < data->Devices[iDevice].nChannels; iChannel++)
        {
            printf("\tChannel %d:\t", iChannel);
            if (data->Devices[iDevice].ChannelData[iChannel].nFrames == 0)
            {
                printf("\tEmpty Frame\n");
            }
            for (int iSample = 0; iSample < data->Devices[iDevice].ChannelData[iChannel].nFrames; iSample++)
                printf("%3.2f\t", data->Devices[iDevice].ChannelData[iChannel].Values[iSample]);
            printf("\n");
        }
    }
}
