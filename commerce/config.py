import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

SERVICES = ("identity", "product", "inventory", "payment", "order", "notification", "gateway")
PORTS = {name: 8001 + index for index, name in enumerate(SERVICES)}


@dataclass
class Settings:
    service: str
    database_url: str
    jwt_secret: str
    internal_secret: str
    rabbit_url: str = ""
    urls: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, service=None):
        load_dotenv()
        service = service or os.getenv("SERVICE", "gateway")
        if service not in SERVICES:
            raise ValueError("Unknown SERVICE")
        jwt_secret = os.getenv("JWT_SECRET", "")
        internal_secret = os.getenv("INTERNAL_SECRET", "")
        if min(len(jwt_secret), len(internal_secret)) < 32:
            raise ValueError("Run python -m commerce.manage init: secrets must be at least 32 characters")
        Path(".data").mkdir(exist_ok=True)
        offset = int(os.getenv("PORT_OFFSET", "0"))
        return cls(
            service=service,
            database_url=os.getenv("DATABASE_URL", f"sqlite:///.data/{service}.db"),
            jwt_secret=jwt_secret,
            internal_secret=internal_secret,
            rabbit_url=os.getenv("RABBIT_URL", ""),
            urls={
                name: os.getenv(f"{name.upper()}_URL", f"http://127.0.0.1:{PORTS[name] + offset}")
                for name in SERVICES
            },
        )
