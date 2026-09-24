"""設定讀取與驗證。憑證一律由環境變數提供，倉庫只放 .env.example。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# --- 資料來源（只取公開分頁，會員頁不碰）---
LAZYRS_BASE_URL = os.environ.get("LAZYRS_BASE_URL", "https://lazyrs.trade").rstrip("/")
HTTP_TIMEOUT = int(os.environ.get("LAZYRS_HTTP_TIMEOUT", "30"))
HTTP_RETRIES = int(os.environ.get("LAZYRS_HTTP_RETRIES", "2"))
CACHE_TTL = int(os.environ.get("LAZYRS_CACHE_TTL", "120"))

# 公開分頁：tab -> 顯示名
TABS = {
    "stocks": "美股",
    "hkstocks": "港股",
    "crypto": "加密貨幣",
    "fx": "外匯",
    "commodities": "大宗商品",
}
DEFAULT_TAB = "stocks"

# --- Telegram ---
TELEGRAM_TOKEN = os.environ.get("USER_TG_BOT_TOKEN", "")
ADMIN_CHAT_ID = os.environ.get("USER_TG_ADMIN_CHAT_ID", "")
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "12"))

# --- LLM（自然語言問答，可選；沒有 key 時只跑規則命令）---
LLM_PROVIDER = os.environ.get("USER_LLM_PROVIDER", "gemini").lower()
LLM_API_KEY = os.environ.get("USER_LLM_API_KEY", "")
LLM_MODEL = os.environ.get("USER_LLM_MODEL", "gemini-2.0-flash")
LLM_BASE_URL = os.environ.get(
    "USER_LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
).rstrip("/")
LLM_TIMEOUT = int(os.environ.get("USER_LLM_TIMEOUT", "60"))

DISCLAIMER = "非投資建議，僅供研究參考，風險自負。"


def llm_enabled():
    return bool(LLM_API_KEY)


def validate(require_telegram=True):
    missing = []
    if require_telegram and not TELEGRAM_TOKEN:
        missing.append("USER_TG_BOT_TOKEN")
    if LLM_PROVIDER not in ("gemini", "openai"):
        missing.append("USER_LLM_PROVIDER(gemini|openai)")
    return missing
