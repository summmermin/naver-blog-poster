import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
CHROME_PROFILE_DIR = BASE_DIR / "chrome_profile"
DB_PATH = BASE_DIR / "blog_posts.db"

NAVER_ID = os.getenv("NAVER_ID", "")
NAVER_PW = os.getenv("NAVER_PW", "")
BLOG_ID = os.getenv("BLOG_ID", NAVER_ID)

SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "11"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))
