from __future__ import annotations
import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
SUPER_ADMIN_ID=int(os.getenv('SUPER_ADMIN_ID','0').strip() or 0)
DB_PATH=os.getenv('DB_PATH','data/app.db').strip()
PAYMENT_CARD=os.getenv('PAYMENT_CARD','8600 0000 0000 0000').strip()
PAYMENT_CARD_HOLDER=os.getenv('PAYMENT_CARD_HOLDER','ISLOM SABIROV').strip()
PAYMENT_PAYME_LINK=os.getenv('PAYMENT_PAYME_LINK','').strip()
PAYMENT_VISA_INFO=os.getenv('PAYMENT_VISA_INFO','Visa karta orqali to‘lov uchun adminga yozing').strip()
