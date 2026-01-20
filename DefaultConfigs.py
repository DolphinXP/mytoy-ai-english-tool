
# Default API configurations
default_configs = {
    'deepseek': {
        'endpoint': "https://api.xiaomimimo.com/v1",
        'key': "YOUR_API_KEY_HERE",
        'model': "mimo-v2-flash",
        # None, "http://127.0.0.1:18080", "http://127.0.0.1:1080"
        'proxy': None,
        'timeout': 60.0,  # Increased timeout
        'verify_ssl': True
    },
}
