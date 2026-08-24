import os

from dotenv import load_dotenv

load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

OWNER_IDS = {
    int(user_id.strip())
    for user_id in os.getenv("OWNER_IDS", "").split(",")
    if user_id.strip().isdigit()
}


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured.")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not configured.")