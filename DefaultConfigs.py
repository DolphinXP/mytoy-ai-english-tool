
# Default API configurations
default_configs = {
    'deepseek': {
        'endpoint': "https://api.deepseek.com",
        'key': "YOUR_API_KEY_HERE",
        'model': "deepseek-chat",
        # None, "http://127.0.0.1:18080", "http://127.0.0.1:1080"
        'proxy': None,
        'timeout': 60.0,  # Increased timeout
        'verify_ssl': True
    },
}

# default_configs = {
#     'deepseek': {
#         'endpoint': "https://open.bigmodel.cn/api/paas/v4",
#         'key': "YOUR_API_KEY_HERE",
#         'model': "glm-4.7-flash",
#         # None, "http://127.0.0.1:18080", "http://127.0.0.1:1080"
#         'proxy': None,
#         'timeout': 60.0,  # Increased timeout
#         'verify_ssl': True
#     },
# }
