import os
import structlog
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from src.einvoice import Invoice

BOT_TOKEN = os.getenv("TELEGRAM_BOT_API")
USER_ID = os.getenv("TELEGRAM_CHAT_ID")

logger = structlog.get_logger()

async def send_invoice_msg(invoice: Invoice):
    bot = Bot(BOT_TOKEN)

    invoice_cashew_url = invoice.to_cashew_url()

    logger.info('Sending invoice message to Telegram', invoice=invoice.invoice_number, url=invoice_cashew_url)

    keyboard = [
        [InlineKeyboardButton("新增到 Cashew", url=invoice_cashew_url)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text_msg = f"你有新發票進來了哦～～～\n{invoice.ai_description}\n\n發票號碼: {invoice.invoice_number}\n賣家: {invoice.seller_name}\n總金額: {invoice.total_amount} 元\n開立時間: {invoice.invoice_datetime}\n\n詳細內容:\n" + "\n".join([f"- {item.item_name} x{item.quantity} @ {item.unit_price} 元 = {item.total_price} 元 ({item.ai_category})" for item in invoice.items])
    await bot.send_message(
        chat_id=USER_ID,
        text=text_msg,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )