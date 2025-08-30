# Настройки бота
from dotenv import load_dotenv
import os
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = '@probvpn123'
ADMIN_ID = 2057750889
WELCOME_GIF_URL = 'https://media4.giphy.com/media/v1.Y2lkPTZjMDliOTUybmxhemtsZzJub21hdnJ4bmkyN2ZrYWRobnY5cm4xcjN5aTNzbDZsYiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/C2GtNxNdOfprXhUJGR/giphy.gif'
ADMIN_IDS = [2057750889]
# Настройки ЮKассы 3.6.0
YOOKASSA_SHOP_ID = '1137264'
YOOKASSA_SECRET_KEY = 'test_b6A8gP_TwQCAc8CZpHQrgsyxIP0xrmy3GYqSvfUiaEE'
YOOKASSA_RETURN_URL = 'https://t.me/SHARDPROB_bot'

# Настройки VPN
VPN_SERVER_URL = 'http://146.103.102.21:8080'
VPN_AUTH_KEY = '18181818'

# Telegram Stars
STARS_PROVIDER_TOKEN = ''

# Цены (в копейках)
PRICES = {
    '1': 14900,
    '3': 39900,
    '6': 69900,
    '12': 99900
}

# Путь к единой базе данных (все таблицы в одном файле)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'users.db')

# Базовый URL мини-приложения (укажите свой домен/хост)
# Пример: 'https://mini.yourdomain.com'
MINIAPP_BASE_URL = 'https://example.com'