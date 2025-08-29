from dataclasses import InitVar, dataclass, field, asdict
import json
import urllib
from datetime import datetime

@dataclass
class InvoiceItem:
    ai_category: str
    item_name: str
    quantity: int
    unit_price: float
    total_price: float

@dataclass
class Invoice:
    invoice_number: str
    total_amount: float
    seller_name: str
    invoice_datetime: str
    ai_description: str
    items: list[InvoiceItem] = field(default_factory=list)

    mongo_db: InitVar = None

    def __post_init__(self, mongo_db):
        if mongo_db is not None:
            self.is_in_mongo = mongo_db.invoice_collection.find_one({"invoice_number": self.invoice_number}) is not None
            if not self.is_in_mongo: self.to_mongo(mongo_db)

    def to_dict(self):
        return asdict(self)
    
    def to_mongo(self, mongo_db):
        if not self.is_in_mongo:
            mongo_db.insert_one(self.to_dict())
            self.is_in_mongo = True

    def to_cashew_url(self) -> str:

        data = {
            'transactions':[
                {
                "date": f"{self.invoice_datetime}",
                "amount": f"{-item.total_price}",
                "title": f"{item.item_name}",
                "category": f"{item.ai_category}",
                "notes": f"發票號碼: {self.invoice_number}\n賣家: {self.seller_name}\n",
                } for item in self.items
            ]
        }
        
        base_url = "https://cashewapp.web.app/addTransaction"
        json_str = json.dumps(data, ensure_ascii=False)
        once = urllib.parse.quote(json_str, safe='')
        encoded = urllib.parse.quote(once, safe='')

        return f"{base_url}?JSON={encoded}"
    

