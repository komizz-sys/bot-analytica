import os
from dotenv import load_dotenv

load_dotenv()

# Токен ЭТОГО бота — новый, отдельный, создаётся через @BotFather.
# Не путать с токеном основного магазина!
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ID админов через запятую: ADMIN_IDS=111111,222222
# Только эти люди смогут пользоваться ботом-аналитиком.
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

# Публичный URL магазина (сервис "worker" в Railway-проекте tg_shop_bot),
# по которому доступен внутренний API статистики. Например:
# https://tg-shop-bot-production.up.railway.app
# ВАЖНО: для сервиса "worker" в Railway нужно один раз включить публичный
# домен (Settings -> Networking -> Generate Domain), иначе снаружи к нему
# не достучаться.
SHOP_API_URL = os.getenv("SHOP_API_URL", "").rstrip("/")

# Тот же секрет, что в ANALYTICS_API_SECRET у основного бота-магазина —
# без совпадения магазин не отдаст данные (ответит 403).
SHOP_API_SECRET = os.getenv("SHOP_API_SECRET", "")

# Локальная база ЭТОГО бота — тут хранятся только вручную занесённые расходы
# (закупка звёзд/подарков через Fragment/MarketApp), доход считается не отсюда,
# а через SHOP_API_URL выше.
DB_PATH = os.getenv("DB_PATH", "data/analytics.db")
