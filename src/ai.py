from openai import OpenAI

categorize_model = "gpt-5-mini-2025-08-07"
categorize_prompt = """
Give the categories: Dining, Groceries, Shopping, Transit, Entertainment, Bills & Fees, Gifts, Beauty, Work, Travel
Which category should the following record be in? Reply only the raw category name, no other context allowed.
"""

describe_model = "gpt-4o-2024-08-06"
describe_character = "路邊的可愛高中妹妹"
describe_prompt = f"""
下面是一張發票明細，想像你是{describe_character}，請用{describe_character}的語氣並以一句話來評論這張發票。如果有需要，可以適當加上顏文字
"""

import os
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

import structlog
logger = structlog.get_logger()

if OPENAI_API_KEY and OPENAI_ENDPOINT:
    openai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT
    )

else:
    openai = None

def ai(model: str, prompt: str, invoice_item: str):

    if not openai:
        logger.warning('OpenAI API Key is not provided, AI function will not proceed')
        return

    response = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt + invoice_item}
        ]
    )
    return response.choices[0].message.content

def ai_categorize(invoice_item: str):
    return ai(categorize_model, categorize_prompt, invoice_item)

def ai_description(invoice: str):
    return ai(describe_model, describe_prompt, invoice)


