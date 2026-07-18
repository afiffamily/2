"""
Konfiguratsiya moduli.
.env faylidan o'qiydi va majburiy o'zgaruvchilarni tekshiradi.
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)


def _require(key: str) -> str:
    """Agar muhit o'zgaruvchisi yo'q bo'lsa, aniq xato ko'rsatadi."""
    value = os.getenv(key, "").strip()
    if not value:
        raise EnvironmentError(
            f"[CONFIG ERROR] '{key}' muhit o'zgaruvchisi topilmadi yoki bo'sh. "
            f".env faylini tekshiring."
        )
    return value


# ── Majburiy o'zgaruvchilar ───────────────────────────────────────────────────
BOT_TOKEN: str = _require("BOT_TOKEN")
GROUP_ID: int = int(_require("GROUP_ID"))

_raw_db_url: str = _require("DB_URL")
DB_URL: str = (
    _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if _raw_db_url.startswith("postgresql://")
    else _raw_db_url
)

# ── Ixtiyoriy o'zgaruvchilar ──────────────────────────────────────────────────
ADMINS: list[int] = [
    int(x)
    for x in os.getenv("ADMINS", "").split(",")
    if x.strip().isdigit()
]

# Throttling sozlamalari
THROTTLE_RATE: float = float(os.getenv("THROTTLE_RATE", "1.0"))   # soniya
THROTTLE_LIMIT: int = int(os.getenv("THROTTLE_LIMIT", "3"))        # ketma-ket so'rov

# Broadcast sozlamalari
BROADCAST_DELAY: float = float(os.getenv("BROADCAST_DELAY", "0.05"))  # soniya

# Referral: shuncha do'st taklif qilingandan keyin majburiy obunadan ozod bo'ladi
REFERRAL_THRESHOLD: int = int(os.getenv("REFERRAL_THRESHOLD", "3"))
