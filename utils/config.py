"""
Configuration management for API services.
"""

# Default API configurations
default_configs = {
    'deepseek': {
        'endpoint': "https://api.xiaomimimo.com/v1",
        'key': "YOUR_API_KEY_HERE",
        'model': "mimo-v2-flash",
        'proxy': None,
        'timeout': 60.0,
        'verify_ssl': True
    },
    'ollama_translate': {
        'endpoint': "http://10.110.31.157:11434/v1",
        'key': "ollama",
        'model': "qwen3.5:9b",
        'proxy': None,
        'timeout': 120.0,
        'verify_ssl': False
    },
}


def get_api_config(config_name='deepseek'):
    """
    Get API configuration by name.

    Args:
        config_name: Name of the configuration (default: 'deepseek')

    Returns:
        Dictionary containing API configuration
    """
    return default_configs.get(config_name, default_configs['deepseek'])


def get_api_endpoint(config_name='deepseek'):
    """Get API endpoint URL."""
    config = get_api_config(config_name)
    return config.get('endpoint', '')


def get_api_key(config_name='deepseek'):
    """Get API key."""
    config = get_api_config(config_name)
    return config.get('key', '')


def get_api_model(config_name='deepseek'):
    """Get API model name."""
    config = get_api_config(config_name)
    return config.get('model', '')


def get_api_proxy(config_name='deepseek'):
    """Get API proxy URL."""
    config = get_api_config(config_name)
    return config.get('proxy', None)


def get_api_timeout(config_name='deepseek'):
    """Get API timeout in seconds."""
    config = get_api_config(config_name)
    return config.get('timeout', 60.0)


def get_api_verify_ssl(config_name='deepseek'):
    """Get SSL verification setting."""
    config = get_api_config(config_name)
    return config.get('verify_ssl', True)
