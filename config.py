import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_DB_URI = os.environ.get("MONGO_DB_URI")
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID"))
FILES_CHANNEL_ID = int(os.environ.get("FILES_CHANNEL_ID"))

# Parse comma separated admin ids from env, example: 123,4567890
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
