import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Deployment mode ──────────────────────────────────────────────
DEPLOY_MODE = os.getenv("DEPLOY_MODE", "local")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

# ── CORS ─────────────────────────────────────────────────────────
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:80")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ── Auth ──────────────────────────────────────────────────────────
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true" or DEPLOY_MODE == "cloud"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS_HASH = os.getenv("ADMIN_PASS_HASH", "")

# ── Database ─────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/job_agent.db")

# ── Encryption ───────────────────────────────────────────────────
def _get_or_create_encryption_key() -> bytes:
    key = os.getenv("ENCRYPTION_KEY", "").strip()
    if key:
        return key.encode()

    env_path = BASE_DIR / ".env"
    new_key = Fernet.generate_key().decode()

    if env_path.exists():
        content = env_path.read_text()
        if "ENCRYPTION_KEY=" in content:
            lines = content.splitlines()
            lines = [f"ENCRYPTION_KEY={new_key}" if l.startswith("ENCRYPTION_KEY=") else l for l in lines]
            env_path.write_text("\n".join(lines) + "\n")
        else:
            with env_path.open("a") as f:
                f.write(f"\nENCRYPTION_KEY={new_key}\n")
    else:
        env_path.write_text(f"ENCRYPTION_KEY={new_key}\n")

    print(f"[config] Generated new ENCRYPTION_KEY and wrote to .env")
    return new_key.encode()


class FernetEncryption:
    def __init__(self):
        self._fernet = Fernet(_get_or_create_encryption_key())

    def encrypt(self, text: str) -> str:
        return self._fernet.encrypt(text.encode()).decode()

    def decrypt(self, token: str) -> str:
        return self._fernet.decrypt(token.encode()).decode()


encryption = FernetEncryption()
