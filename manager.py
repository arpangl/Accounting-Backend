import asyncio
import json
import structlog
from datetime import datetime
import time
import pymongo
from src.ai import ai_categorize, ai_description
from src.einvoice import Invoice, InvoiceItem

from src.crawl_tools import (
    login_and_generate_session,
    get_JWT_with_time_range,
    get_invoice_list,
    get_invoice_detail,
    get_invoice_datetime
)
from src.telegram_bot import send_invoice_msg

logger = structlog.get_logger()

class InvoiceManager:
    def __init__(self):
        self.invoice_list = []
        self.client = pymongo.MongoClient("mongodb://192.168.0.103:27017/")
        self.db = self.client["invoice"]["lambert"]


    def check_is_in_db(self, invoice_number: str) -> bool:
        return self.db.find_one({"invoice_number": invoice_number}) is not None

    def fetch_once(self):
        session = login_and_generate_session()
        time.sleep(3)
        session, jwt_token = get_JWT_with_time_range(session, datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0), datetime.now().replace(minute=0, second=0, microsecond=0), login_and_generate_session)
        invoice_list = get_invoice_list(session, jwt_token, size=100)

        for invoice in invoice_list:
            if not self.check_is_in_db(invoice['invoiceNumber']):
                items = []
                logger.info('Got invoice', invoice=invoice['invoiceNumber'], price=invoice['totalAmount'], seller=invoice['sellerName'], invoiceDate=invoice['invoiceDate'])
                invoice_token = invoice['token']
                invoice['items'] = get_invoice_detail(session, invoice_token)
                invoice['datetime'] = get_invoice_datetime(session, invoice_token).strftime("%Y-%m-%d %H:%M:%S")
                for item in invoice['items']:
                    if item['amount'] != '0':
                        items.append(
                            InvoiceItem(
                                ai_category=ai_categorize(json.dumps(item)),
                                item_name=item['item'],
                                quantity=int(item['quantity']),
                                unit_price=int(item['unitPrice'].replace(',', '')),
                                total_price=int(item['amount'].replace(',', ''))
                            )
                        )
                inv = Invoice(
                    invoice_number=invoice['invoiceNumber'],
                    seller_name=invoice['sellerName'],
                    ai_description=ai_description(json.dumps(invoice)),
                    invoice_datetime=invoice['datetime'],
                    total_amount=invoice['totalAmount'],
                    items=items,
                    mongo_db=self.db,
                )
                logger.info('Invoice saved to MongoDB', invoice=inv)
                asyncio.run(send_invoice_msg(inv))