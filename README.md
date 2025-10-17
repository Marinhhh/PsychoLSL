# PsychoLSL
1.用NatNetSDK接收从Optitrack(Motive)流出的帧数据包

2.基于NatNet中的Motive帧数据，在Psychopy中搭建交互式的实验场景

3.将NatNet接收到的Motive帧数据广播为LSL格式的数据流

4.使用python的pylsl库，接收LSL格式的Motive帧数据

5.通过LSL对齐Optitrack和Psychopy的时间戳，使用LSL的内部时钟`pylsl.local_clock()`

6.后续可以将其他的设备接入LSL，使用LSL的内部时钟对齐多模态数据的时间戳
