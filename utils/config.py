"""
Configuration management for API services.
"""
from DefaultConfigs import default_configs


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
