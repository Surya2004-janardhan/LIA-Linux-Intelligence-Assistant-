import yaml
import os
from core.logger import logger

class Config:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.settings = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}, using defaults.")
            return {}
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f) or {}

    def get(self, key, default=None):
        """Gets a nested config value using dot notation: 'llm.model'"""
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key, value):
        """Sets a nested config value using dot notation and saves to disk."""
        keys = key.split('.')
        d = self.settings
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    def save(self):
        """Writes current settings back to config.yaml."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(self.settings, f, default_flow_style=False)
            logger.info("Configuration saved to disk.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def reload(self):
        """Reloads config from disk."""
        self.settings = self.load_config()

# Singleton instance
config = Config()
