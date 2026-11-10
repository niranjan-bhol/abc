import os
import pyotp
import requests
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TOTP_KEY = os.getenv("TOTP_KEY")
MOBILE_NO = os.getenv("MOBILE_NO")
PIN = os.getenv("PIN")

ACCESS_TOKEN_FILE = "access_token.txt"
BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_DIR = BASE_DIR / "data" / "auth"
TOKEN_PATH = TOKEN_DIR / ACCESS_TOKEN_FILE

REDIRECT_URL = "http://127.0.0.1:5000/"

AUTH_URL = (
    "https://api.upstox.com/v2/login/authorization/dialog?" +
    urlencode({
        "response_type": "code",
        "client_id": API_KEY,
        "redirect_uri": REDIRECT_URL,
    })
)

def get_access_token(code):
    response = requests.post(
        "https://api.upstox.com/v2/login/authorization/token",
        headers={
            "accept": "application/json",
            "Api-Version": "2.0",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "code": code,
            "client_id": API_KEY,
            "client_secret": API_SECRET,
            "redirect_uri": REDIRECT_URL,
            "grant_type": "authorization_code",
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["access_token"]

def save_access_token(token):
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_PATH, "w") as f:
        f.write(token)

def login():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        page = browser.new_page()
        page.set_default_timeout(30000)
        
        try:
            with page.expect_request(f"*{REDIRECT_URL}?code*") as req:
                page.goto(AUTH_URL)
                page.locator("#mobileNum").fill(MOBILE_NO)
                page.get_by_role("button", name="Get OTP").click()
                page.locator("#otpNum").fill(pyotp.TOTP(TOTP_KEY).now())
                page.get_by_role("button", name="Continue").click()
                page.get_by_label("Enter 6-digit PIN").fill(PIN)
                page.get_by_role("button", name="Continue").click()
                page.wait_for_load_state()
            
            code = parse_qs(urlparse(req.value.url).query)["code"][0]
        
        finally:
            browser.close()
    
    token = get_access_token(code)
    save_access_token(token)
    return token

def main():
    try:
        login()
        relative_path = Path("/") / TOKEN_PATH.relative_to(BASE_DIR.parent)
        print(f"Access token fetched and stored successfully at {relative_path}")
    except Exception as e:
        print(f"Error | {e}")

if __name__ == "__main__":
    main()
