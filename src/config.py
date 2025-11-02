from dotenv import load_dotenv  # type: ignore
import os
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL")
REQUESTS_TIMEOUT = int(os.getenv("REQUESTS_TIMEOUT", "15"))
REQUESTS_SLEEP_BETWEEN = float(os.getenv("REQUESTS_SLEEP_BETWEEN", "1.2"))
USER_AGENT = os.getenv("USER_AGENT", "demand-forecast-bot/1.0")