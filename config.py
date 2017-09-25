# Настроить ленту RSS можно на https://freelance.ru/rss/index
RSS_URL = ""

# В секундах
POLL_INTERVAL = 60

BOT_TOKEN = ""

TARGET_CHAT_ID = ""

try:
    from config_local import *
except ImportError:
    print("Local config not found")
