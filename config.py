# Настроить ленту RSS можно на https://freelance.ru/rss/index
RSS_URL = ""

# В секундах
POLL_INTERVAL = 60

BOT_TOKEN = ""

TARGET_CHAT_ID = ""

# Valid values are `json` and `console`.
# `json` - print log entries as json objects, one per line.
# `console` - pretty-print log entries for easy reading.
LOGS_RENDERER = 'console'

# Заблокированные слова.
BLOCKED_KEYWORDS = []

# Ограничение на количество символов в описании сообщения.
LIMIT_DESCRIPTION = None

try:
    from config_local import *
except ImportError:
    print("Local config not found")
