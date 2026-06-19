import json
from logging import getLogger
from pathlib import Path
from time import time

from pydantic import BaseModel

from .vendor.tiddl.core.api import TidalClient, TidalAPI
from .vendor.tiddl.core.auth import AuthAPI

log = getLogger(__name__)

AUTH_FILE = Path(__file__).resolve().parent.parent / "data" / "auth.json"


class AuthData(BaseModel):
    token: str | None = None
    refresh_token: str | None = None
    expires_at: int = 0
    user_id: str | None = None
    country_code: str | None = None


def load_auth() -> AuthData:
    if not AUTH_FILE.exists():
        return AuthData()
    try:
        return AuthData.model_validate_json(AUTH_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Failed to load auth: %s", e)
        return AuthData()


def save_auth(auth_data: AuthData) -> None:
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTH_FILE.write_text(auth_data.model_dump_json(), encoding="utf-8")


def make_api(auth_data: AuthData | None = None) -> TidalAPI:
    if auth_data is None:
        auth_data = load_auth()

    assert auth_data.token, "Not logged in. Run `tidpl auth login` first."
    assert auth_data.refresh_token, "No refresh token."
    assert auth_data.user_id, "No user ID."
    assert auth_data.country_code, "No country code."

    refresh_token = auth_data.refresh_token

    def on_token_expiry() -> str | None:
        auth_api = AuthAPI()
        resp = auth_api.refresh_token(refresh_token)
        auth_data.token = resp.access_token
        auth_data.expires_at = resp.expires_in + int(time())
        save_auth(auth_data)
        return resp.access_token

    client = TidalClient(
        token=auth_data.token,
        cache_name=str(AUTH_FILE.parent / "api_cache"),
        on_token_expiry=on_token_expiry,
    )

    return TidalAPI(client, auth_data.user_id, auth_data.country_code)
