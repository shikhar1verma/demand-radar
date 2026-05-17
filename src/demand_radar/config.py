from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

RedditBackendName = Literal["praw", "public_json"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    reddit_backend: RedditBackendName = Field(default="public_json", alias="REDDIT_BACKEND")
    reddit_client_id: str | None = Field(default=None, alias="REDDIT_CLIENT_ID")
    reddit_client_secret: str | None = Field(default=None, alias="REDDIT_CLIENT_SECRET")
    reddit_user_agent: str = Field(
        default="demand-radar-local/0.1", alias="REDDIT_USER_AGENT"
    )
    database_path: Path = Field(default=Path("data/demand_radar.sqlite3"), alias="DATABASE_PATH")
    reports_dir: Path = Field(default=Path("reports"), alias="REPORTS_DIR")
    llm_provider: str = Field(default="none", alias="LLM_PROVIDER")

    def require_reddit_credentials(self) -> None:
        missing = []
        if not self.reddit_client_id:
            missing.append("REDDIT_CLIENT_ID")
        if not self.reddit_client_secret:
            missing.append("REDDIT_CLIENT_SECRET")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing Reddit credentials: {joined}. Check .env.")


def get_settings() -> Settings:
    return Settings()
