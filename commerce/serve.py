import uvicorn

from commerce.config import Settings
from commerce.manage import migrate, seed

if __name__ == "__main__":
    settings = Settings.from_env()
    migrate(settings)
    seed(settings)
    uvicorn.run("commerce.app:create_app", factory=True, host="0.0.0.0", port=8000)
