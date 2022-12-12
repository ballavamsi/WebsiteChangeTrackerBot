from dotenv import load_dotenv
import os

load_dotenv()

APP_URL = "https://t.me/WebsiteChangeTrackerBot"
ACCESS_TOKEN = os.getenv("WebsiteChangeTrackerBot_ACCESS_TOKEN")
DB_FILE = os.getenv("DB_PATH")
