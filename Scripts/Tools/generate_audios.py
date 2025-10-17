"""
文本转语音工具
使用pyttsx3批量生成实验音频文件
支持预定义文本和自定义文本
"""

import pyttsx3
from pathlib import Path
import logging
import sys
import threading
import time

# ========== 路径配置常量 ==========
# 可在此处修改音频保存路径
AUDIO_BASE_DIR = '../../Assets/Audios'  # 相对于Scripts/Tools/目录


class TextToAudioConverter:
    """文本转语音转换器"""
    
    def __init__(self, rate=150, volume=0.9, voice_index=0):
        """
        初始化TTS引擎
        
        Args:
            rate: 语速(words/min)，建议140-160
            volume: 音量(0.0-1.0)
            voice_index: 语音索引，0=默认，可通过list_voices()查看
        """
        self.logger = logging.getLogger('TextToAudio')
        
        # 初始化pyttsx3引擎
        self.engine = pyttsx3.init()
        
        # 设置语音参数
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)
        
        # 选择语音
        voices = self.engine.getProperty('voices')
        if voice_index < len(voices):
            self.engine.setProperty('voice', voices[voice_index].id)
            self.logger.info(f"使用语音: {voices[voice_index].name}")
        
        self.logger.info(f"TTS引擎初始化完成 (语速={rate}, 音量={volume})")
    
    def list_voices(self):
        """列出所有可用的语音"""
        voices = self.engine.getProperty('voices')
        
        print("可用语音:")
        for idx, voice in enumerate(voices):
            print(f"  [{idx}] {voice.name} ({voice.id})")
            print(f"      语言: {voice.languages}")
        
        return voices
    
    def text_to_audio(self, text, output_path, show_progress=True, timeout=10):
        """
        将文本转换为音频文件
        
        Args:
            text: 要转换的文本
            output_path: 输出wav文件路径
            show_progress: 是否显示进度
            timeout: 超时时间(秒)
        
        Returns:
            bool: 是否成功
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if show_progress:
                print(f"生成: {output_path.name} <- \"{text}\"")
            
            # 保存为wav文件
            self.engine.save_to_file(text, str(output_path))
            
            # 使用线程和超时机制防止卡住
            success = False
            def run_engine():
                nonlocal success
                try:
                    self.engine.runAndWait()
                    success = True
                except Exception:
                    pass
            
            thread = threading.Thread(target=run_engine)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                self.logger.warning(f"TTS超时 ({timeout}s)，跳过: {text}")
                if show_progress:
                    print(f"  ⚠️  超时跳过")
                return False
            
            if output_path.exists() and success:
                if show_progress:
                    file_size = output_path.stat().st_size / 1024
                    print(f"  ✅ 成功 ({file_size:.1f} KB)")
                return True
            else:
                self.logger.error(f"文件生成失败: {output_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"转换失败 '{text}' -> {output_path}: {e}")
            return False
    
    def batch_generate_predefined(self, base_dir=None):
        """
        批量生成预定义的实验音频
        
        Args:
            base_dir: 音频基础目录
        
        Returns:
            dict: 生成统计 {'success': int, 'failed': int}
        """
        if base_dir is None:
            # 使用脚本所在目录的相对路径
            script_dir = Path(__file__).parent
            base_path = script_dir / AUDIO_BASE_DIR
        else:
            base_path = Path(base_dir)
            
        stats = {'success': 0, 'failed': 0}
        
        print(f"📁 音频保存路径: {base_path.absolute()}")
        
        print("=" * 60)
        print("批量生成实验音频文件")
        print("=" * 60)
        
        # 1. 墙面标记 - 前往
        print("\n[1/5] 生成墙面标记音频（前往）...")
        wallmarker_go_dir = base_path / 'WallMarker_go'
        
        for wall in ['A', 'B', 'C', 'D']:
            for num in range(1, 6):
                marker_id = f"{wall}{num}"
                text = f"请前往{marker_id}"
                output_file = wallmarker_go_dir / f"{marker_id}.wav"
                
                if self.text_to_audio(text, output_file):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        # 2. 墙面标记 - 到达
        print("\n[2/5] 生成墙面标记音频（到达）...")
        wallmarker_arrive_dir = base_path / 'WallMarker_arrive'
        
        for wall in ['A', 'B', 'C', 'D']:
            for num in range(1, 6):
                marker_id = f"{wall}{num}"
                text = f"成功到达{marker_id}"
                output_file = wallmarker_arrive_dir / f"{wall}_{num}.wav"
                
                if self.text_to_audio(text, output_file):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
        
        # 3. 隐藏目标 - 前往
        print("\n[3/5] 生成隐藏目标音频（前往）...")
        target_go_dir = base_path / 'Target_go'
        
        for num in range(1, 4):
            target_id = f"T{num}"
            text = f"请探索寻找{target_id}"
            output_file = target_go_dir / f"{target_id}.wav"
            
            if self.text_to_audio(text, output_file):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        # 4. 隐藏目标 - 到达
        print("\n[4/5] 生成隐藏目标音频（到达）...")
        target_arrive_dir = base_path / 'Target_arrive'
        
        for num in range(1, 4):
            target_id = f"T{num}"
            text = f"找到了{target_id}"
            output_file = target_arrive_dir / f"T_{num}.wav"
            
            if self.text_to_audio(text, output_file):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        # 5. 通用提示
        print("\n[5/5] 生成通用提示音频...")
        common_dir = base_path / 'Common'
        
        common_texts = {
            'Resume.wav': '请继续',
            'Switch.wav': '请交换',
            'Begin.wav': '实验开始',
            'End.wav': '实验结束',
        }
        
        for filename, text in common_texts.items():
            output_file = common_dir / filename
            
            if self.text_to_audio(text, output_file):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        # 打印统计
        print("\n" + "=" * 60)
        print("生成完成")
        print("=" * 60)
        print(f"✅ 成功: {stats['success']} 个文件")
        print(f"❌ 失败: {stats['failed']} 个文件")
        print(f"📁 输出目录: {base_path.absolute()}")
        print("=" * 60)
        
        return stats
    
    def generate_custom_audio(self, text, output_path):
        """
        生成自定义文本的音频
        
        Args:
            text: 文本内容
            output_path: 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        return self.text_to_audio(text, output_path)
    
    def generate_custom_batch(self, text_dict, output_dir):
        """
        批量生成自定义文本音频
        
        Args:
            text_dict: {filename: text} 字典
            output_dir: 输出目录
        
        Returns:
            dict: 统计信息
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        stats = {'success': 0, 'failed': 0}
        
        print(f"\n批量生成自定义音频到: {output_path}")
        print("-" * 60)
        
        for filename, text in text_dict.items():
            # 确保文件名以.wav结尾
            if not filename.endswith('.wav'):
                filename += '.wav'
            
            output_file = output_path / filename
            
            if self.text_to_audio(text, output_file):
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        print("-" * 60)
        print(f"完成: 成功 {stats['success']}, 失败 {stats['failed']}")
        
        return stats
    
    def cleanup(self):
        """清理资源"""
        try:
            self.engine.stop()
        except:
            pass


def main():
    """主函数 - 交互式命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description='文本转语音工具')
    parser.add_argument('--mode', choices=['predefined', 'custom', 'list-voices', 'interactive'],
                       default='interactive', help='运行模式')
    parser.add_argument('--text', type=str, help='要转换的文本（custom模式）')
    parser.add_argument('--output', type=str, help='输出文件路径（custom模式）')
    parser.add_argument('--rate', type=int, default=150, help='语速（words/min）')
    parser.add_argument('--volume', type=float, default=0.9, help='音量（0.0-1.0）')
    parser.add_argument('--voice', type=int, default=0, help='语音索引')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化转换器
    converter = TextToAudioConverter(rate=args.rate, volume=args.volume, voice_index=args.voice)
    
    if args.mode == 'list-voices':
        # 列出可用语音
        converter.list_voices()
    
    elif args.mode == 'predefined':
        # 生成预定义音频
        converter.batch_generate_predefined()
    
    elif args.mode == 'custom':
        # 生成自定义音频
        if not args.text or not args.output:
            print("错误: custom模式需要--text和--output参数")
            return
        
        converter.generate_custom_audio(args.text, args.output)
    
    elif args.mode == 'interactive':
        # 交互式模式
        print("\n" + "=" * 60)
        print("文本转语音工具 - 交互式模式")
        print("=" * 60)
        print("\n请选择操作:")
        print("  1. 生成所有预定义实验音频")
        print("  2. 生成自定义文本音频")
        print("  3. 查看可用语音")
        print("  0. 退出")
        
        while True:
            choice = input("\n请输入选项 [0-3]: ").strip()
            
            if choice == '0':
                print("退出程序")
                break
            
            elif choice == '1':
                converter.batch_generate_predefined()
                break
            
            elif choice == '2':
                text = input("\n请输入文本内容: ").strip()
                if not text:
                    print("文本不能为空")
                    continue
                
                output = input("请输入输出文件名（如: test.wav）: ").strip()
                if not output:
                    print("文件名不能为空")
                    continue
                
                # 默认保存到Audios/Custom目录
                output_path = Path('Audios/Custom') / output
                
                converter.generate_custom_audio(text, output_path)
                break
            
            elif choice == '3':
                converter.list_voices()
            
            else:
                print("无效选项，请重新输入")
    
    converter.cleanup()


if __name__ == '__main__':
    main()

