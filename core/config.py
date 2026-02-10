import yaml
import os

class Config:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.settings = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            # Fallback or default logic could go here
            return {}
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key, default=None):
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

# Singleton instance
config = Config()
