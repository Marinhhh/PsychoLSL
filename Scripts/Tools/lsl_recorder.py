"""
LSL数据录制器 (V3.0版)
支持CLI（子进程模式）和GUI（交互模式）双模式
持续拉取LSL流并保存为XDF（同步）和CSV（审计）格式
"""

import sys
import time
import argparse
import threading
import json
import atexit
import signal
from pathlib import Path
from datetime import datetime

# 添加Scripts目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入LSL相关模块
try:
    import pylsl
    from pylsl import StreamInlet, resolve_streams
    print("✅ pylsl已导入")
except ImportError:
    print("❌ 未找到pylsl模块，请安装: pip install pylsl")
    sys.exit(1)

try:
    import pyxdf
    print("✅ pyxdf已导入")
except ImportError:
    print("⚠️  未找到pyxdf模块，XDF功能将不可用: pip install pyxdf")
    pyxdf = None

import csv
import numpy as np


class LSLRecorderCore:
    """LSL录制器核心功能"""
    
    def __init__(self):
        self.streams = []
        self.inlets = []
        self.is_recording = False
        self.record_thread = None
        self.data_buffers = {}
        self.start_time = None
        self.sample_counts = {}
        
        # 录制配置
        self.selected_streams = []
        self.output_dir = None
        self.filename_prefix = "LSL_Recording"
        self.start_time_str = None  # 固定的开始时间字符串（用于文件名）
        
        # V3.0支持参数
        self.dyad_id = None
        self.session_id = None
        self.sub_id = None
        
        # 统计信息
        self.total_samples = 0
        self.recording_duration = 0
        
        # 自动保存配置（V3.3.1新增）
        self.auto_save_interval = 30.0  # 每30秒自动保存一次
        self.last_save_time = None
        self.save_counter = 0
        
        # 注册退出处理器（确保数据保存）
        atexit.register(self._emergency_save)
    
    def discover_streams(self, timeout=3.0):
        """发现所有LSL数据流"""
        try:
            print(f"🔍 扫描LSL数据流 (等待{timeout}秒)...")
            streams = resolve_streams(wait_time=timeout)
            self.streams = streams
            
            if not streams:
                print("⚠️  未发现任何LSL数据流")
                return []
            
            print(f"✅ 发现 {len(streams)} 个数据流:")
            for idx, stream in enumerate(streams):
                info = {
                    'name': stream.name(),
                    'type': stream.type(),
                    'channel_count': stream.channel_count(),
                    'nominal_srate': stream.nominal_srate(),
                    'source_id': stream.source_id()
                }
                print(f"  [{idx+1}] {info['name']} | Type: {info['type']} | "
                      f"Channels: {info['channel_count']} | Rate: {info['nominal_srate']}Hz")
            
            return streams
            
        except Exception as e:
            print(f"❌ 发现数据流错误: {e}")
            return []
    
    def select_streams(self, stream_indices=None):
        """选择要录制的数据流"""
        if stream_indices is None:
            # 默认选择所有流
            self.selected_streams = self.streams.copy()
        else:
            self.selected_streams = []
            for idx in stream_indices:
                if 0 <= idx < len(self.streams):
                    self.selected_streams.append(self.streams[idx])
        
        print(f"📋 已选择 {len(self.selected_streams)} 个数据流进行录制")
        return len(self.selected_streams) > 0
    
    def setup_recording(self, output_dir=None, filename_prefix="LSL_Recording", dyad_id=None, session_id=None, sub_id=None):
        """设置录制参数（支持V3.0路径格式）"""
        if output_dir and dyad_id and session_id:
            # V3.0路径格式：Data/Lsl/{dyad_id}/{session}/
            self.output_dir = Path(output_dir) / 'Lsl' / f'D{dyad_id:03d}' / f'S{session_id}'
            self.dyad_id = dyad_id
            self.session_id = session_id
            self.sub_id = sub_id or f"{dyad_id:03d}"
        elif output_dir:
            # 传统路径格式
            self.output_dir = Path(output_dir)
            self.dyad_id = None
            self.session_id = None
            self.sub_id = None
        else:
            print("❌ 需要提供output_dir参数")
            return False
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.filename_prefix = filename_prefix
        
        print(f"📁 录制目录: {self.output_dir}")
        print(f"📄 文件前缀: {self.filename_prefix}")
        if self.sub_id:
            print(f"🆔 被试ID: {self.sub_id}")
        
        return True
    
    def start_recording(self):
        """开始录制"""
        if self.is_recording:
            print("⚠️  已在录制中")
            return False
        
        if not self.selected_streams:
            print("❌ 未选择录制流")
            return False
        
        if not self.output_dir:
            print("❌ 未设置录制目录")
            return False
        
        try:
            print(f"\n🎬 开始录制 {len(self.selected_streams)} 个数据流...")
            
            self.is_recording = True
            self.start_time = time.time()
            self.start_time_str = datetime.now().strftime("%Y%m%d-%H%M%S")  # 固定的时间戳字符串
            self.total_samples = 0
            self.sample_counts = {}
            self.data_buffers = {}
            
            # 启动录制线程（V3.3.1：改为非daemon，确保数据保存）
            self.record_thread = threading.Thread(target=self._record_worker, daemon=False)
            self.record_thread.start()
            
            # 初始化自动保存
            self.last_save_time = time.time()
            
            print("✅ 录制已启动")
            return True
            
        except Exception as e:
            print(f"❌ 开始录制失败: {e}")
            self.is_recording = False
            return False
    
    def stop_recording(self):
        """停止录制"""
        if not self.is_recording:
            print("⚠️  未在录制")
            return False
        
        print("\n⏹️  正在停止录制...")
        self.is_recording = False
        
        if self.record_thread:
            self.record_thread.join(timeout=5.0)
        
        # 计算录制时长
        if self.start_time:
            self.recording_duration = time.time() - self.start_time
        
        # 最终保存（保存剩余的buffer数据）
        if self.data_buffers and any(len(data) > 0 for data in self.data_buffers.values()):
            self._save_data()
        else:
            print("ℹ️  所有数据已通过自动保存写入")
        
        print("✅ 录制已停止")
        self._print_recording_summary()
        
        return True
    
    def _record_worker(self):
        """录制工作线程"""
        try:
            # 创建输入流
            self.inlets = []
            for stream in self.selected_streams:
                try:
                    inlet = StreamInlet(stream)
                    self.inlets.append(inlet)
                    stream_name = stream.name()
                    self.data_buffers[stream_name] = []
                    self.sample_counts[stream_name] = 0
                    print(f"  ✅ 已连接: {stream_name}")
                except Exception as e:
                    print(f"  ❌ 连接失败 {stream.name()}: {e}")
            
            if not self.inlets:
                print("❌ 没有可用的输入流")
                return
            
            print(f"📡 开始接收数据...")
            
            # 录制循环（V3.3.1：添加定期自动保存）
            while self.is_recording:
                for inlet in self.inlets:
                    try:
                        sample, timestamp = inlet.pull_sample(timeout=0.001)
                        if sample:
                            stream_name = inlet.info().name()
                            self.data_buffers[stream_name].append({
                                'timestamp': timestamp,
                                'sample': sample
                            })
                            self.sample_counts[stream_name] += 1
                            self.total_samples += 1
                    except Exception as e:
                        # 静默处理接收错误
                        pass
                
                # 定期自动保存（每30秒）
                if self.last_save_time and (time.time() - self.last_save_time >= self.auto_save_interval):
                    try:
                        self._save_data_incremental()
                        self.last_save_time = time.time()
                    except Exception as e:
                        print(f"⚠️  自动保存失败: {e}")
                
                time.sleep(0.001)  # 小延迟避免CPU占用过高
            
        except Exception as e:
            print(f"❌ 录制线程错误: {e}")
        finally:
            # 清理输入流
            for inlet in self.inlets:
                try:
                    inlet.close_stream()
                except:
                    pass
    
    def _save_data(self):
        """保存录制的数据（停止时的最终保存）"""
        if not self.data_buffers:
            print("⚠️  没有数据可保存")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        try:
            print("\n💾 保存数据...")
            
            # 保存为CSV格式（审计用）
            self._save_csv(timestamp, mode='final')
            
            # 保存为XDF格式（同步用）
            if pyxdf:
                self._save_xdf(timestamp)
            else:
                print("⚠️  pyxdf不可用，跳过XDF保存")
            
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")
    
    def _save_data_incremental(self):
        """增量保存数据（定期自动保存，追加模式）"""
        if not self.data_buffers:
            return
        
        try:
            self.save_counter += 1
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # 追加模式保存CSV
            self._save_csv(timestamp, mode='incremental')
            
            # 清空buffer（避免重复写入，已保存的数据不需要保留）
            saved_count = sum(len(data) for data in self.data_buffers.values())
            self.data_buffers = {stream_name: [] for stream_name in self.data_buffers.keys()}
            
            print(f"  💾 自动保存#{self.save_counter}: {saved_count}样本已保存，buffer已清空")
            
        except Exception as e:
            print(f"⚠️  增量保存失败: {e}")
    
    def _emergency_save(self):
        """紧急保存（程序意外退出时调用）"""
        if self.is_recording and self.data_buffers:
            try:
                print("\n⚠️  检测到程序退出，执行紧急保存...")
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                self._save_csv(timestamp, mode='emergency')
                print(f"✅ 紧急保存完成：{self.total_samples}样本已保存")
            except Exception as e:
                print(f"❌ 紧急保存失败: {e}")
    
    def _save_csv(self, timestamp, mode='final'):
        """保存为CSV格式（支持增量保存和紧急保存）
        
        Args:
            timestamp: 时间戳字符串
            mode: 'final'=最终保存, 'incremental'=增量保存, 'emergency'=紧急保存
        """
        try:
            for stream_name, data in self.data_buffers.items():
                if not data:
                    continue
                
                # V3.0命名格式：{Sub_id}_{流名称}_{时间戳}.csv
                if self.sub_id:
                    csv_filename = f"{self.sub_id}_{stream_name}_{self.start_time_str}.csv"
                else:
                    # 兼容传统格式（使用开始时间作为文件名，而不是每次保存的时间）
                    csv_filename = f"{self.filename_prefix}_{stream_name}_{self.start_time_str}.csv"
                
                csv_file = self.output_dir / csv_filename
                
                # 判断是否需要写入表头（文件不存在或首次保存）
                file_exists = csv_file.exists()
                
                # 追加模式（incremental）或覆盖模式（final/emergency）
                file_mode = 'a' if (mode == 'incremental' and file_exists) else 'w'
                
                with open(csv_file, file_mode, newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    # 写入表头（仅在新文件时）
                    if not file_exists or file_mode == 'w':
                        if data:
                            sample_size = len(data[0]['sample'])
                            header = ['Timestamp'] + [f'Ch_{i+1}' for i in range(sample_size)]
                            writer.writerow(header)
                    
                    # 写入数据
                    for entry in data:
                        row = [entry['timestamp']] + list(entry['sample'])
                        writer.writerow(row)
                
                # 模式标识
                mode_label = {
                    'final': '最终保存',
                    'incremental': '增量保存',
                    'emergency': '紧急保存'
                }.get(mode, '保存')
                
                if mode == 'final' or mode == 'emergency':
                    print(f"  📄 {mode_label}: {csv_filename} ({len(data)} 样本)")
                
        except Exception as e:
            print(f"❌ CSV保存失败: {e}")
    
    def _save_xdf(self, timestamp):
        """保存为XDF格式（支持V3.0命名格式）"""
        try:
            # 为每个流创建单独的XDF文件
            for stream_name, data in self.data_buffers.items():
                if not data:
                    continue
                
                # V3.0命名格式：{Sub_id}_{流名称}_{时间戳}.xdf
                if self.sub_id:
                    xdf_filename = f"{self.sub_id}_{stream_name}_{timestamp}.xdf"
                else:
                    # 兼容传统格式
                    xdf_filename = f"{self.filename_prefix}_{stream_name}_{timestamp}.xdf"
                
                xdf_file = self.output_dir / xdf_filename
                
                # 这里简化实现，实际中需要更复杂的XDF构建
                # 由于pyxdf主要用于读取，写入功能有限，这里只做占位
                print(f"  📄 XDF保存功能开发中: {xdf_filename}")
            
        except Exception as e:
            print(f"❌ XDF保存失败: {e}")
    
    def _print_recording_summary(self):
        """打印录制摘要"""
        print(f"\n📊 录制摘要:")
        print(f"   录制时长: {self.recording_duration:.1f} 秒")
        print(f"   总样本数: {self.total_samples}")
        
        if self.recording_duration > 0:
            avg_rate = self.total_samples / self.recording_duration
            print(f"   平均采样率: {avg_rate:.1f} Hz")
        
        print(f"   各流样本数:")
        for stream_name, count in self.sample_counts.items():
            rate = count / self.recording_duration if self.recording_duration > 0 else 0
            print(f"     {stream_name}: {count} ({rate:.1f} Hz)")
    
    def get_recording_status(self):
        """获取录制状态"""
        return {
            'is_recording': self.is_recording,
            'duration': time.time() - self.start_time if self.start_time else 0,
            'total_samples': self.total_samples,
            'sample_counts': self.sample_counts.copy(),
            'stream_count': len(self.selected_streams)
        }


# ========== CLI模式 ==========

def run_cli_mode(args):
    """运行CLI模式（子进程模式）"""
    print("\n" + "=" * 60)
    print("LSL录制器 - CLI模式")
    print("=" * 60)
    
    recorder = LSLRecorderCore()
    
    # 设置信号处理器（确保Ctrl+C时保存数据）
    def signal_handler(sig, frame):
        print("\n⚠️  收到中断信号，正在保存数据...")
        if recorder.is_recording:
            recorder.stop_recording()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 发现数据流
        streams = recorder.discover_streams(timeout=args.scan_timeout)
        if not streams:
            print("❌ 未发现数据流，退出")
            return False
        
        # 选择数据流
        if args.streams:
            # 指定流索引
            stream_indices = [int(i) - 1 for i in args.streams.split(',')]
            recorder.select_streams(stream_indices)
        else:
            # 选择所有流
            recorder.select_streams()
        
        # 设置录制
        output_dir = args.output_dir or f"Data/LSL/{datetime.now().strftime('%Y%m%d')}"
        filename_prefix = args.prefix or "LSL_Recording"
        recorder.setup_recording(output_dir, filename_prefix)
        
        # 开始录制
        if not recorder.start_recording():
            return False
        
        # 录制循环
        if args.duration:
            print(f"⏱️  将录制 {args.duration} 秒...")
            time.sleep(args.duration)
            recorder.stop_recording()
        else:
            print("⏱️  持续录制中，按 Ctrl+C 停止...")
            try:
                while True:
                    time.sleep(1)
                    if args.verbose:
                        status = recorder.get_recording_status()
                        print(f"\r录制中... {status['duration']:.1f}s, {status['total_samples']} 样本", end='')
            except KeyboardInterrupt:
                print("\n⚠️  用户中断录制")
                recorder.stop_recording()
        
        return True
        
    except Exception as e:
        print(f"❌ CLI模式错误: {e}")
        return False


# ========== GUI模式 ==========

def run_gui_mode():
    """运行GUI模式"""
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QGroupBox, QLabel, QPushButton, QCheckBox, QLineEdit,
            QFileDialog, QTextEdit, QTableWidget, QTableWidgetItem,
            QHeaderView, QMessageBox, QSpinBox, QProgressBar
        )
        from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
        from PyQt5.QtGui import QFont, QColor
        
        print("✅ PyQt5已导入")
    except ImportError:
        print("❌ 未找到PyQt5模块，GUI模式不可用")
        print("   请安装: pip install PyQt5")
        return False
    
    class LSLRecorderGUI(QMainWindow):
        """LSL录制器GUI主窗口"""
        
        def __init__(self):
            super().__init__()
            self.recorder = LSLRecorderCore()
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_status)
            
            self.init_ui()
            self.discover_streams()
        
        def init_ui(self):
            """初始化用户界面"""
            self.setWindowTitle('LSL数据录制器 V3.0')
            self.setGeometry(100, 100, 1200, 800)  # 增大窗口：1200x800像素
            
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            
            # 数据流选择区域
            streams_group = QGroupBox("数据流选择")
            streams_layout = QVBoxLayout()
            
            self.streams_table = QTableWidget()
            self.streams_table.setColumnCount(5)
            self.streams_table.setHorizontalHeaderLabels(['选择', '名称', '类型', '通道数', '采样率'])
            streams_layout.addWidget(self.streams_table)
            
            refresh_btn = QPushButton("刷新数据流")
            refresh_btn.clicked.connect(self.discover_streams)
            streams_layout.addWidget(refresh_btn)
            
            streams_group.setLayout(streams_layout)
            layout.addWidget(streams_group)
            
            # 录制配置区域
            config_group = QGroupBox("录制配置")
            config_layout = QVBoxLayout()
            
            # 输出目录
            dir_layout = QHBoxLayout()
            dir_layout.addWidget(QLabel("输出目录:"))
            self.dir_edit = QLineEdit(f"Data/LSL/{datetime.now().strftime('%Y%m%d')}")
            dir_layout.addWidget(self.dir_edit)
            
            dir_btn = QPushButton("浏览")
            dir_btn.clicked.connect(self.select_output_dir)
            dir_layout.addWidget(dir_btn)
            config_layout.addLayout(dir_layout)
            
            # 文件前缀
            prefix_layout = QHBoxLayout()
            prefix_layout.addWidget(QLabel("文件前缀:"))
            self.prefix_edit = QLineEdit("LSL_Recording")
            prefix_layout.addWidget(self.prefix_edit)
            config_layout.addLayout(prefix_layout)
            
            config_group.setLayout(config_layout)
            layout.addWidget(config_group)
            
            # 控制按钮区域
            control_layout = QHBoxLayout()
            
            self.start_btn = QPushButton("开始录制")
            self.start_btn.clicked.connect(self.start_recording)
            control_layout.addWidget(self.start_btn)
            
            self.stop_btn = QPushButton("停止录制")
            self.stop_btn.clicked.connect(self.stop_recording)
            self.stop_btn.setEnabled(False)
            control_layout.addWidget(self.stop_btn)
            
            layout.addLayout(control_layout)
            
            # 状态显示区域
            status_group = QGroupBox("录制状态")
            status_layout = QVBoxLayout()
            
            self.status_label = QLabel("就绪")
            status_layout.addWidget(self.status_label)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            status_layout.addWidget(self.progress_bar)
            
            status_group.setLayout(status_layout)
            layout.addWidget(status_group)
            
            # 日志区域
            log_group = QGroupBox("日志")
            log_layout = QVBoxLayout()
            
            self.log_text = QTextEdit()
            self.log_text.setMaximumHeight(150)
            log_layout.addWidget(self.log_text)
            
            log_group.setLayout(log_layout)
            layout.addWidget(log_group)
        
        def discover_streams(self):
            """发现数据流"""
            self.log("🔍 正在扫描LSL数据流...")
            streams = self.recorder.discover_streams()
            
            self.streams_table.setRowCount(len(streams))
            
            for i, stream in enumerate(streams):
                stream_name = stream.name()
                
                # 选择复选框（默认只选中位置流，不选Marker流）
                checkbox = QCheckBox()
                # Navigation_Markers默认不选中（因为已在Markers.csv记录）
                should_check = stream_name != 'Navigation_Markers'
                checkbox.setChecked(should_check)
                self.streams_table.setCellWidget(i, 0, checkbox)
                
                # 流信息
                self.streams_table.setItem(i, 1, QTableWidgetItem(stream_name))
                self.streams_table.setItem(i, 2, QTableWidgetItem(stream.type()))
                self.streams_table.setItem(i, 3, QTableWidgetItem(str(stream.channel_count())))
                self.streams_table.setItem(i, 4, QTableWidgetItem(f"{stream.nominal_srate():.1f}"))
            
            self.log(f"✅ 发现 {len(streams)} 个数据流")
        
        def select_output_dir(self):
            """选择输出目录"""
            dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
            if dir_path:
                self.dir_edit.setText(dir_path)
        
        def start_recording(self):
            """开始录制"""
            try:
                # 获取选中的流
                selected_indices = []
                for i in range(self.streams_table.rowCount()):
                    checkbox = self.streams_table.cellWidget(i, 0)
                    if checkbox.isChecked():
                        selected_indices.append(i)
                
                if not selected_indices:
                    QMessageBox.warning(self, "警告", "请至少选择一个数据流")
                    return
                
                # 配置录制器
                self.recorder.select_streams(selected_indices)
                self.recorder.setup_recording(
                    self.dir_edit.text(),
                    self.prefix_edit.text()
                )
                
                # 开始录制
                if self.recorder.start_recording():
                    self.start_btn.setEnabled(False)
                    self.stop_btn.setEnabled(True)
                    self.progress_bar.setVisible(True)
                    self.update_timer.start(1000)  # 每秒更新
                    self.log("🎬 录制已开始")
                else:
                    QMessageBox.critical(self, "错误", "录制启动失败")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"录制启动失败: {e}")
        
        def stop_recording(self):
            """停止录制"""
            try:
                self.recorder.stop_recording()
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.progress_bar.setVisible(False)
                self.update_timer.stop()
                self.log("⏹️  录制已停止")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"录制停止失败: {e}")
        
        def update_status(self):
            """更新状态显示"""
            if self.recorder.is_recording:
                status = self.recorder.get_recording_status()
                self.status_label.setText(
                    f"录制中... {status['duration']:.1f}s, "
                    f"{status['total_samples']} 样本"
                )
        
        def log(self, message):
            """添加日志"""
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
    
    # 启动GUI应用
    app = QApplication(sys.argv)
    window = LSLRecorderGUI()
    window.show()
    
    try:
        app.exec_()
        return True
    except Exception as e:
        print(f"❌ GUI运行错误: {e}")
        return False


# ========== 主函数 ==========

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='LSL数据录制器 V3.0')
    parser.add_argument('--cli', action='store_true', help='运行CLI模式')
    parser.add_argument('--gui', action='store_true', help='运行GUI模式')
    parser.add_argument('--output-dir', '-o', help='输出目录')
    parser.add_argument('--prefix', '-p', help='文件名前缀')
    parser.add_argument('--duration', '-d', type=float, help='录制时长（秒）')
    parser.add_argument('--streams', '-s', help='指定录制的流（逗号分隔的索引）')
    parser.add_argument('--scan-timeout', type=float, default=3.0, help='扫描超时时间')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 如果没有指定模式，根据参数自动判断
    if not args.cli and not args.gui:
        if len(sys.argv) == 1:
            # 没有参数，启动GUI
            args.gui = True
        else:
            # 有参数，启动CLI
            args.cli = True
    
    try:
        if args.cli:
            success = run_cli_mode(args)
        elif args.gui:
            success = run_gui_mode()
        else:
            print("❌ 未指定运行模式")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  程序被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 程序错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()