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
        logging.FileHandler("accounting-backend.log", encoding="utf-8"),  # 記錄到檔案
        logging.StreamHandler(),  # 同時輸出到 console
    ],
)

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),  # 以 JSON 輸出
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

check_chrome_exists(force_redownload=False)

import time
import random

if __name__ == "__main__":
    logger.info('Started invoice manager')
    invoice_manager = InvoiceManager()
    while True:
        invoice_manager.fetch_once()
        sleep_time = random.randint(6000, 21600)
        logger.info(f"Fetch complete, sleeping for {sleep_time} seconds")
        time.sleep(sleep_time)