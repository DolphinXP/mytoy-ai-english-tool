"""
Configuration management for Quick Translation app.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Application configuration manager."""

    # Application info
    APP_NAME = "Quick Translation"
    APP_VERSION = "1.0.0"

    # Paths
    BASE_DIR = Path(__file__).parent
    CONFIG_FILE = BASE_DIR / "config.json"
    HISTORY_FILE = BASE_DIR / "history.json"

    # Default configuration
    DEFAULT_CONFIG = {
        "current_service": "deepseek",
        "services": {
            "deepseek": {
                "endpoint": "https://api.xiaomimimo.com/v1",
                "key": "YOUR_API_KEY_HERE",
                "model": "mimo-v2-flash",
                "timeout": 60.0,
                "verify_ssl": True
            },
            "ollama": {
                "endpoint": "http://10.110.31.157:11434/v1",
                "key": "ollama",
                "model": "qwen3.5:9b",
                "timeout": 120.0,
                "verify_ssl": False
            }
        },
        "hotkey": "<ctrl>+<alt>+q",
        "ui": {
            "theme": "dark",
            "opacity": 0.90,
            "animation_duration": 300
        },
        "tts": {
            "enabled": True,
            "rate": 150,
            "volume": 0.8
        },
        "history": {
            "max_items": 20,
            "auto_save": True
        }
    }

    def __init__(self):
        """Initialize configuration."""
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading config: {e}")
                self._config = self.DEFAULT_CONFIG.copy()
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key."""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()

    def get_api_config(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get API configuration for a service."""
        if service_name is None:
            service_name = self.get('current_service', 'deepseek')
        return self.get(f'services.{service_name}', self.DEFAULT_CONFIG['services']['deepseek'])

    def get_hotkey(self) -> str:
        """Get current hotkey combination."""
        return self.get('hotkey', '<ctrl>+<alt>+q')

    def set_hotkey(self, hotkey: str) -> None:
        """Set hotkey combination."""
        self.set('hotkey', hotkey)

    def get_current_service(self) -> str:
        """Get current AI service name."""
        return self.get('current_service', 'deepseek')

    def set_current_service(self, service_name: str) -> None:
        """Set current AI service."""
        self.set('current_service', service_name)

    def get_ui_opacity(self) -> float:
        """Get UI opacity value."""
        return self.get('ui.opacity', 0.90)

    def set_ui_opacity(self, opacity: float) -> None:
        """Set UI opacity value."""
        self.set('ui.opacity', opacity)

    def get_tts_enabled(self) -> bool:
        """Check if TTS is enabled."""
        return self.get('tts.enabled', True)

    def set_tts_enabled(self, enabled: bool) -> None:
        """Enable or disable TTS."""
        self.set('tts.enabled', enabled)

    def get_tts_rate(self) -> int:
        """Get TTS speech rate."""
        return self.get('tts.rate', 150)

    def set_tts_rate(self, rate: int) -> None:
        """Set TTS speech rate."""
        self.set('tts.rate', rate)

    def get_history_max_items(self) -> int:
        """Get maximum history items."""
        return self.get('history.max_items', 20)

    def set_history_max_items(self, max_items: int) -> None:
        """Set maximum history items."""
        self.set('history.max_items', max_items)


# Global configuration instance
config = Config()
