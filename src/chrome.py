CHROME_JSON_URL = 'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'
import os
import shutil
import zipfile
import requests
import structlog
from tqdm import tqdm
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

logger = structlog.get_logger()

def download_with_progress(url, filename):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total = int(response.headers.get('content-length', 0))
    with open(filename, 'wb') as file, tqdm(
        desc=filename,
        total=total,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)

def check_chrome_exists(force_redownload: bool = False) -> None:
    logger.info("Checking Chrome installation")
    if Path('chrome-headless-shell-linux64').exists() and Path('chromedriver-linux64').exists():
        logger.info("Chrome and ChromeDriver are already installed.")
        if not force_redownload:
            return
        else:
            shutil.rmtree('chrome-headless-shell-linux64', ignore_errors=True)
            shutil.rmtree('chromedriver-linux64', ignore_errors=True)
            logger.info("Forcing re-download of Chrome and ChromeDriver.")

    logger.info("Downloading Chrome and ChromeDriver")

    with requests.get(CHROME_JSON_URL) as r:
        r.raise_for_status()
        chrome_data = r.json()

    # chrome_version = chrome_data['channels']['Stable']['version']
    for platform_info in chrome_data['channels']['Stable']['downloads']['chrome-headless-shell']:
        if platform_info['platform'] == 'linux64':
            chrome_download_url = platform_info['url']
            break

    for platform_info in chrome_data['channels']['Stable']['downloads']['chromedriver']:
        if platform_info['platform'] == 'linux64':
            chromedriver_download_url = platform_info['url']
            break

    chrome_zip = 'chrome-headless-shell.zip'
    download_with_progress(chrome_download_url, chrome_zip)

    chromedriver_zip = 'chromedriver.zip'
    download_with_progress(chromedriver_download_url, chromedriver_zip)

    with zipfile.ZipFile(chrome_zip, 'r') as zip_ref:
        zip_ref.extractall(os.getcwd())

    with zipfile.ZipFile(chromedriver_zip, 'r') as zip_ref:
        zip_ref.extractall(os.getcwd())

    Path(chrome_zip).unlink(missing_ok=True)
    Path(chromedriver_zip).unlink(missing_ok=True)

def setup_chrome() -> webdriver.Chrome:
    chrome_binary_path = os.path.join(os.getcwd(), 'chrome-headless-shell-linux64', 'chrome-headless-shell')
    chromedriver_path = os.path.join(os.getcwd(), 'chromedriver-linux64', 'chromedriver')
    if not os.path.exists(chrome_binary_path):
        raise FileNotFoundError(f"Chrome binary not found at: {chrome_binary_path}")
    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(f"ChromeDriver not found at: {chromedriver_path}")
    os.chmod(chrome_binary_path, 0o755)
    os.chmod(chromedriver_path, 0o755)
    chrome_options = Options()
    chrome_options.binary_location = chrome_binary_path
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins')
    chrome_options.add_argument('--window-size=1080,2160')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

