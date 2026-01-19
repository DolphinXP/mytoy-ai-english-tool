
# Default API configurations
default_configs = {
    'deepseek': {
        'endpoint': "https://integrate.api.nvidia.com/v1",
        'key': "YOUR_API_KEY_HERE",
        'model': "moonshotai/kimi-k2-instruct-0905",
        # None, "http://127.0.0.1:18080", "http://127.0.0.1:1080"
        'proxy': "http://127.0.0.1:18080",
        'timeout': 60.0,  # Increased timeout
        'verify_ssl': True
    },
}
