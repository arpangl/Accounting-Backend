from dotenv import load_dotenv
load_dotenv()

import logging
import structlog
from manager import InvoiceManager
from src.chrome import check_chrome_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("einvoice-accounting-backend.log", encoding="utf-8"),
        logging.StreamHandler(),  # 同時輸出到 console
    ],
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

check_chrome_exists(force_redownload=False)

import time
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from threading import Thread

def run_at_first_day_of_month():
    while True:
        sleep_seconds = ((datetime.now().replace(day=1) + relativedelta(months=1)).replace(hour=8, minute=0, second=0, microsecond=0) - datetime.now()).total_seconds()
        logger.info(f"Sleeping until the first day of next month: (about {sleep_seconds} seconds)")
        time.sleep(sleep_seconds + 10)  # wait a bit more to ensure it's the next month
        logger.info("It's the first day of the month, fetching last month's invoices")
        invoice_manager.fetch_last_month()


if __name__ == "__main__":
    logger.info('Started invoice manager')
    invoice_manager = InvoiceManager()
    thread = Thread(target=run_at_first_day_of_month, daemon=True)
    thread.start()
    
    while True:
        invoice_manager.fetch_once()
        sleep_time = random.randint(6000, 21600)
        logger.info(f"Fetch complete, sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)