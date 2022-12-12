from dotenv import load_dotenv
from datetime import timedelta
import os

load_dotenv()

DEFAULT_JOBS_RUN_TIME = timedelta(
                         minutes=os.getenv("DEFAULT_JOBS_RUN_TIME", 60))
ADMIN_USERS = [os.getenv("ADMIN_USER", "0")]
