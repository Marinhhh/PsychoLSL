"""
音频播放管理器
预加载所有音频文件，提供快速播放接口
"""

import pygame
from pathlib import Path
import logging
import sys

# ========== 路径配置常量 ==========
# 可在此处修改音频加载路径
AUDIO_BASE_DIR = '../../Assets/Audios'  # 相对于Scripts/Core/目录


class AudioManager:
    """音频播放管理器"""
    
    def __init__(self, audio_base_dir=None):
        self.logger = logging.getLogger('AudioManager')
        if audio_base_dir is None:
            # 使用脚本所在目录的相对路径
            script_dir = Path(__file__).parent
            self.audio_base_dir = script_dir / AUDIO_BASE_DIR
        else:
            self.audio_base_dir = Path(audio_base_dir)
            
        self.logger.info(f"音频基础路径: {self.audio_base_dir.absolute()}")
        
        # 初始化pygame mixer
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # 音频字典
        self.audios = {
            'wallmarker_go': {},      # A1.wav ~ D5.wav
            'wallmarker_arrive': {},  # A_1.wav ~ D_5.wav
            'target_go': {},          # T1.wav ~ T3.wav
            'target_arrive': {},      # T_1.wav ~ T_3.wav
            'common': {}              # Resume.wav, Switch.wav, etc.
        }
        
        self.current_sound = None
    
    def load_all_audios(self):
        """预加载所有音频文件"""
        print("🔊 正在加载音频文件...")
        
        loaded_count = 0
        
        # 加载墙面标记音频
        wallmarker_go_dir = self.audio_base_dir / 'WallMarker_go'
        if wallmarker_go_dir.exists():
            for wall in ['A', 'B', 'C', 'D']:
                for num in range(1, 6):
                    marker_id = f"{wall}{num}"
                    audio_file = wallmarker_go_dir / f"{marker_id}.wav"
                    if audio_file.exists():
                        try:
                            self.audios['wallmarker_go'][marker_id] = pygame.mixer.Sound(str(audio_file))
                            loaded_count += 1
                        except Exception as e:
                            self.logger.warning(f"加载音频失败 {audio_file}: {e}")
        
        # 加载到达墙面标记音频
        wallmarker_arrive_dir = self.audio_base_dir / 'WallMarker_arrive'
        if wallmarker_arrive_dir.exists():
            for wall in ['A', 'B', 'C', 'D']:
                for num in range(1, 6):
                    marker_id = f"{wall}{num}"
                    audio_file = wallmarker_arrive_dir / f"{wall}_{num}.wav"
                    if audio_file.exists():
                        try:
                            self.audios['wallmarker_arrive'][marker_id] = pygame.mixer.Sound(str(audio_file))
                            loaded_count += 1
                        except Exception as e:
                            self.logger.warning(f"加载音频失败 {audio_file}: {e}")
        
        # 加载隐藏目标音频
        target_go_dir = self.audio_base_dir / 'Target_go'
        if target_go_dir.exists():
            for num in range(1, 4):
                target_id = f"P{num}"
                audio_file = target_go_dir / f"T{num}.wav"
                if audio_file.exists():
                    try:
                        self.audios['target_go'][target_id] = pygame.mixer.Sound(str(audio_file))
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"加载音频失败 {audio_file}: {e}")
        
        # 加载到达隐藏目标音频
        target_arrive_dir = self.audio_base_dir / 'Target_arrive'
        if target_arrive_dir.exists():
            for num in range(1, 4):
                target_id = f"P{num}"
                audio_file = target_arrive_dir / f"T_{num}.wav"
                if audio_file.exists():
                    try:
                        self.audios['target_arrive'][target_id] = pygame.mixer.Sound(str(audio_file))
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"加载音频失败 {audio_file}: {e}")
        
        # 加载通用音频
        common_dir = self.audio_base_dir / 'Common'
        if common_dir.exists():
            common_files = ['Resume.wav', 'Switch.wav', 'Begin.wav', 'End.wav']
            for filename in common_files:
                audio_file = common_dir / filename
                if audio_file.exists():
                    try:
                        audio_name = filename.replace('.wav', '').lower()
                        self.audios['common'][audio_name] = pygame.mixer.Sound(str(audio_file))
                        loaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"加载音频失败 {audio_file}: {e}")
        
        if loaded_count > 0:
            print(f"✅ 已加载 {loaded_count} 个音频文件")
        else:
            print("⚠️  未找到音频文件，将使用静默模式")
        
        return loaded_count
    
    def play_wallmarker_go(self, marker_id):
        """播放"前往墙面标记"音频"""
        if marker_id in self.audios['wallmarker_go']:
            self.stop_all()
            self.current_sound = self.audios['wallmarker_go'][marker_id]
            self.current_sound.play()
            return True
        else:
            print(f"⚠️  音频不存在: WallMarker_go/{marker_id}.wav")
            return False
    
    def play_wallmarker_arrive(self, marker_id):
        """播放"到达墙面标记"音频"""
        if marker_id in self.audios['wallmarker_arrive']:
            self.stop_all()
            self.current_sound = self.audios['wallmarker_arrive'][marker_id]
            self.current_sound.play()
            return True
        else:
            print(f"⚠️  音频不存在: WallMarker_arrive/{marker_id}.wav")
            return False
    
    def play_target_go(self, target_id):
        """播放"寻找隐藏目标"音频"""
        if target_id in self.audios['target_go']:
            self.stop_all()
            self.current_sound = self.audios['target_go'][target_id]
            self.current_sound.play()
            return True
        else:
            print(f"⚠️  音频不存在: Target_go/{target_id}.wav")
            return False
    
    def play_target_arrive(self, target_id):
        """播放"找到隐藏目标"音频"""
        if target_id in self.audios['target_arrive']:
            self.stop_all()
            self.current_sound = self.audios['target_arrive'][target_id]
            self.current_sound.play()
            return True
        else:
            print(f"⚠️  音频不存在: Target_arrive/{target_id}.wav")
            return False
    
    def play_common(self, audio_type):
        """
        播放通用音频
        audio_type: 'resume', 'switch', 'begin', 'end'
        """
        audio_type = audio_type.lower()
        if audio_type in self.audios['common']:
            self.stop_all()
            self.current_sound = self.audios['common'][audio_type]
            self.current_sound.play()
            return True
        else:
            print(f"⚠️  音频不存在: Common/{audio_type}.wav")
            return False
    
    def stop_all(self):
        """停止所有音频"""
        pygame.mixer.stop()
        self.current_sound = None
    
    def is_playing(self):
        """检查是否正在播放"""
        return pygame.mixer.get_busy()
    
    def wait_finish(self, timeout=5.0):
        """等待当前音频播放完成"""
        import time
        start_time = time.time()
        while self.is_playing():
            if time.time() - start_time > timeout:
                break
            time.sleep(0.01)
    
    def cleanup(self):
        """清理资源"""
        self.stop_all()
        pygame.mixer.quit()

