import os
from dotenv import load_dotenv

load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", 0))
DB_URL = os.getenv("DB_URL")

if DB_URL and DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip().isdigit()]