import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


def _int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, default) or default)
    except ValueError:
        return default


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = _int("GUILD_ID")
REPORT_CHANNEL_ID = _int("REPORT_CHANNEL_ID")
REPORT_HOUR_UTC = min(max(_int("REPORT_HOUR_UTC", 14), 0), 23)
REFRESH_MINUTES = max(_int("REFRESH_MINUTES", 60), 5)
SIMULATION_MODE = _bool("SIMULATION_MODE", True)

DB_PATH = os.getenv("DB_PATH") or ("/data/dropbot.db" if os.path.isdir("/data") else "dropbot.db")

REFERRAL_FEE_PCT = _float("REFERRAL_FEE_PCT", 15.0)
FULFILLMENT_FEE = _float("FULFILLMENT_FEE", 0.0)
PAYMENT_FEE_PCT = _float("PAYMENT_FEE_PCT", 0.0)
MIN_MARGIN_PCT = _float("MIN_MARGIN_PCT", 15.0)

SUPPLIER_API_KEY = os.getenv("SUPPLIER_API_KEY", "")
SPAPI_CREDS = {
    "client_id": os.getenv("SPAPI_LWA_CLIENT_ID", ""),
    "client_secret": os.getenv("SPAPI_LWA_CLIENT_SECRET", ""),
    "refresh_token": os.getenv("SPAPI_REFRESH_TOKEN", ""),
}

SECRETS = [v for v in [DISCORD_TOKEN, SUPPLIER_API_KEY, *SPAPI_CREDS.values()] if v]
