"""
配置加载工具
加载和管理实验配置
"""

import json
from pathlib import Path
import logging


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_file='Config/experiment_config.json'):
        self.logger = logging.getLogger('ConfigLoader')
        self.config_file = Path(config_file)
        self.config = {}
    
    def load_config(self):
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                print(f"⚠️  配置文件不存在: {self.config_file}")
                return self._create_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            
            print(f"✅ 已加载配置: {self.config_file}")
            return self.config
            
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            self.logger.error(f"加载配置错误: {e}")
            return None
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            'room_size': [12.0, 12.0],
            'window_size': [600, 600],
            'num_trials': 20,
            'num_hidden_targets': 3,
            'target_radius': 0.4,
            'wallmarker_threshold': 1.0,
            'trial_interval': 1.0,
            'frame_rate': 60
        }
        return self.config
    
    def save_config(self):
        """保存配置"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 配置已保存: {self.config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            self.logger.error(f"保存配置错误: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)

