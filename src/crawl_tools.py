import os
import time
import pytz
import ddddocr
import requests
import structlog
from typing import Optional, List, Dict, Tuple, Callable
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.chrome import setup_chrome

INVOICE_PHONE = os.getenv("EINVOICE_PHONE", None)
INVOICE_PASSWORD = os.getenv("EINVOICE_PASSWORD", None)

if INVOICE_PHONE is None or INVOICE_PASSWORD is None:
    raise RuntimeError("EINVOICE_PHONE and EINVOICE_PASSWORD environment variables must be set")

logger = structlog.get_logger()
ocr = ddddocr.DdddOcr(show_ad=False)

def login_and_generate_session() -> Optional[requests.Session]:
    logger.info("Starting login process")
    chrome_driver = setup_chrome()
    chrome_driver.get("https://www.einvoice.nat.gov.tw/accounts/login/mw")
    WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "code_num"))
    )
    chrome_driver.find_element(By.ID, "mobile_phone").send_keys(INVOICE_PHONE)
    chrome_driver.find_element(By.ID, "password").send_keys(INVOICE_PASSWORD)
    code_num_img = chrome_driver.find_element(By.CLASS_NAME, "code_num").find_element(By.TAG_NAME, "img")
    code_num_img.screenshot("code_num.png")
    with open("code_num.png", "rb") as f:
        code_num = ocr.classification(f.read())

    chrome_driver.find_element(By.ID, "captcha").send_keys(code_num)
    chrome_driver.find_element(By.ID, "submitBtn").click()

    time.sleep(3)
    attempt = 0
    html = chrome_driver.page_source
    while "驗證失敗" in html:
        chrome_driver.refresh()
        WebDriverWait(chrome_driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "code_num"))
        )
        chrome_driver.find_element(By.ID, "mobile_phone").send_keys(INVOICE_PHONE)
        chrome_driver.find_element(By.ID, "password").send_keys(INVOICE_PASSWORD)
        logger.error("Captcha verification failed, retrying", attempt=attempt + 1)
        code_num_img = chrome_driver.find_element(By.CLASS_NAME, "code_num").find_element(By.TAG_NAME, "img")
        code_num_img.screenshot("code_num.png")
        with open("code_num.png", "rb") as f:
            code_num = ocr.classification(f.read())

        chrome_driver.find_element(By.ID, "captcha").send_keys(code_num)
        chrome_driver.find_element(By.ID, "submitBtn").click()
        attempt += 1
        if attempt >= 5:
            raise RuntimeError("Captcha verification failed after multiple attempts")
        time.sleep(10)
    
    logger.info("Login successful, transferring cookies&token to requests session")

    chrome_driver.get("https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search")
    cookies = chrome_driver.get_cookies()

    logger.debug('Cookies retrieved', cookies=cookies)
    token = chrome_driver.execute_script("return window.localStorage.getItem('token');")
    if token is None:
        token = chrome_driver.execute_script("return window.sessionStorage.getItem('token');")

    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'], secure=cookie['secure'], rest={'httpOnly': cookie.get('httpOnly', None), 'sameSite': cookie.get('sameSite', 'Lax'), 'expiry': cookie.get('expiry', None)})

    headers = {
        'authorization': f'Bearer {token}',
        'content-type': 'application/json',
        'origin': 'https://www.einvoice.nat.gov.tw',
        'referer': 'https://www.einvoice.nat.gov.tw/portal/btc/mobile/btc502w/search',
        'user-agent': chrome_driver.execute_script("return navigator.userAgent;"),
    }

    session.headers.update(headers)
    chrome_driver.quit()

    logger.info("Session setup complete")

    return session

def get_JWT_with_time_range(session: requests.Session, start_time: datetime, end_time: datetime, relogin_func: Callable) -> Tuple[requests.Session, str]:
    logger.info("Fetching JWT token for invoice data", start_time=start_time, end_time=end_time)

    if start_time.tzinfo is None:
        taiwan_tz = pytz.timezone('Asia/Taipei')
        start_time = taiwan_tz.localize(start_time).astimezone(pytz.UTC)
    
    if end_time.tzinfo is None:
        taiwan_tz = pytz.timezone('Asia/Taipei')
        end_time = taiwan_tz.localize(end_time).astimezone(pytz.UTC)
    
    payload = {
        "cardCode": "",
        "carrierId2": "",
        "searchStartDate": start_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "searchEndDate": end_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "invoiceStatus": "0",
        "isSearchAll": "true"
    }
    attempt = 0
    while True:
        ok = False
        resp = session.options("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/btc502w/getSearchCarrierInvoiceListJWT", json=payload)
        if resp.status_code == 200:
            ok = True
        if resp.status_code in (401, 403):
            logger.warning("Auth error on OPTIONS, will try relogin if allowed", status_code=resp.status_code)
        time.sleep(1.5)

        if not ok:
            if resp.status_code in (401, 403) and relogin_func and attempt < 10:
                attempt += 1
                logger.info("Re-login and retry get_JWT_with_time_range", attempt=attempt)
                session = relogin_func()
                continue
            elif resp.status_code in (401, 403):
                raise RuntimeError(f"Auth failed on OPTIONS and relogin not available or exceeded.", status_code=resp.status_code, response=resp.text)
            else:
                raise RuntimeError(f"Failed to fetch JWT token [options] after retries", status_code=resp.status_code, response=resp.text)

        resp = session.post("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/btc502w/getSearchCarrierInvoiceListJWT", json=payload)
        if resp.status_code == 200:
            jwt_token = resp.text.strip()
            if not jwt_token:
                raise RuntimeError("Empty JWT token returned")
            return session, jwt_token


def get_invoice_list(session: requests.Session, jwt_token: str, size: int = 100) -> List[Dict]:
    logger.info("Fetching invoice list", size=size)
    payload = {'token': jwt_token}

    resp = session.options("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/btc502w/searchCarrierInvoice", json=payload, params={'size': size})
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch invoice list [options], status code: {resp.status_code}, response: {resp.text}")

    resp = session.post("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/btc502w/searchCarrierInvoice", json=payload, params={'size': size})
    if resp.status_code > 400:
        raise RuntimeError(f"Failed to fetch invoice list [post], status code: {resp.status_code}, response: {resp.text}")

    if resp.status_code == 204:
        return []
    resp = resp.json()
    result_list = []

    if resp.get('totalPages', 1) > 1:
        for page in range(2, resp['totalPages'] + 1):
            logger.info("Fetching additional invoice list page", page=page)
            payload = {'token': jwt_token}
            resp_page = session.post("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/btc502w/searchCarrierInvoice", json=payload, params={'size': size, 'page': page})
            if resp_page.status_code != 200:
                raise RuntimeError(f"Failed to fetch invoice list page {page} [post], status code: {resp_page.status_code}, response: {resp_page.text}")
            resp_page = resp_page.json()
            result_list.extend(resp_page.get('content', []))

            time.sleep(3) # avoid hitting rate limits
    else:
        result_list.extend(resp.get('content', []))
    logger.info("Invoice list fetching complete", total_invoices=len(result_list))
    return result_list


def get_invoice_datetime(session: requests.Session, invoice_token: str) -> datetime:
    logger.info("Fetching invoice time")
    payload = invoice_token

    resp = session.post("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/common/getCarrierInvoiceData", json=payload)

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch invoice time [post], status code: {resp.status_code}, response: {resp.text}")
    
    invoice_date = resp.json()['invoiceDate']
    invoice_time = resp.json()['invoiceTime']

    result = datetime.strptime(f"{invoice_date} {invoice_time}", "%Y%m%d %H:%M:%S")

    return result

def get_invoice_detail(session: requests.Session, invoice_token: str) -> List[dict]:
    logger.info("Fetching invoice detail")
    payload = invoice_token

    resp = session.post("https://service-mc.einvoice.nat.gov.tw/btc/cloud/api/common/getCarrierInvoiceDetail", json=payload, params={'size': 100})

    if resp.status_code != 200:
        raise RuntimeError(f"Failed to fetch invoice detail [post], status code: {resp.status_code}, response: {resp.text}")

    return resp.json()['content']