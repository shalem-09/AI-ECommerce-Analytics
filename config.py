import os
from pathlib import Path

from sqlalchemy.engine import URL
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "ecommerce_analytics"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "use_mysql": os.getenv("USE_MYSQL", "true").lower() == "true",
}

AI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
}


def get_db_url():
    if not DB_CONFIG["use_mysql"]:
        return None
    if not DB_CONFIG["user"] or not DB_CONFIG["database"]:
        return None
    return URL.create(
        "mysql+pymysql",
        username=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
    )
