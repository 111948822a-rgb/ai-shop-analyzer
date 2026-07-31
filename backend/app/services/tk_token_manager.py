import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

TIKTOK_AUTH_URL = "https://auth.tiktok-shops.com/api/v2/token/get"
TIKTOK_REFRESH_URL = "https://auth.tiktok-shops.com/api/v2/token/refresh"

_token_cache = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": None,
    "last_updated": None,
}

REFRESH_THRESHOLD_MINUTES = 60
_PLATFORM_KEY = "tiktok"


# ----------------------------- 数据库持久化 -----------------------------
def _load_tokens_from_db() -> bool:
    """从数据库加载 token。成功返回 True。"""
    try:
        from app.db import SessionLocal
        from app.models.standard import PlatformToken
        db = SessionLocal()
        try:
            row = db.query(PlatformToken).filter(PlatformToken.platform == _PLATFORM_KEY).first()
            if row and row.access_token and row.refresh_token:
                _token_cache["access_token"] = row.access_token
                _token_cache["refresh_token"] = row.refresh_token
                _token_cache["expires_at"] = row.expires_at
                logger.info("Tokens loaded from database")
                return True
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Load tokens from DB failed: {e}")
    return False


def _save_tokens_to_db(access_token: str, refresh_token: str, expires_at: datetime):
    """把 token 写入数据库（upsert）。生产环境持久化的关键。"""
    try:
        from app.db import SessionLocal
        from app.models.standard import PlatformToken
        db = SessionLocal()
        try:
            row = db.query(PlatformToken).filter(PlatformToken.platform == _PLATFORM_KEY).first()
            if row:
                row.access_token = access_token
                row.refresh_token = refresh_token
                row.expires_at = expires_at
            else:
                db.add(PlatformToken(
                    platform=_PLATFORM_KEY,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                ))
            db.commit()
            logger.info("Tokens saved to database")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Save tokens to DB failed: {e}")


def _load_tokens_from_env():
    """从环境变量加载（首次引导用）。"""
    _token_cache["access_token"] = settings.TK_AUTH_ACCESS_TOKEN
    _token_cache["refresh_token"] = settings.TK_AUTH_REFRESH_TOKEN
    if settings.TK_TOKEN_EXPIRES_AT:
        try:
            _token_cache["expires_at"] = datetime.fromisoformat(settings.TK_TOKEN_EXPIRES_AT)
        except ValueError:
            logger.warning(f"Invalid TK_TOKEN_EXPIRES_AT format: {settings.TK_TOKEN_EXPIRES_AT}")
            _token_cache["expires_at"] = None


def _load_tokens():
    """加载 token：优先数据库，没有则用环境变量（首次引导）。

    这是一劳永逸的关键：
    - 首次启动：环境变量有 token → 加载并写入数据库
    - 之后重启：数据库有 token → 直接用，不再依赖环境变量
    - 刷新后：新 token 写数据库 → 重启后从数据库恢复，永不需要手动改环境变量
    """
    if _load_tokens_from_db():
        return
    # 数据库没有，从环境变量加载（首次引导）
    _load_tokens_from_env()
    # 如果环境变量有 token，立即写入数据库，以后就不用依赖环境变量了
    if _token_cache["access_token"] and _token_cache["refresh_token"]:
        _save_tokens_to_db(
            _token_cache["access_token"],
            _token_cache["refresh_token"],
            _token_cache["expires_at"] or (datetime.now() + timedelta(hours=24)),
        )


def _save_tokens(access_token: str, refresh_token: str, expires_at: datetime):
    """刷新后持久化：内存缓存 + 数据库 + 环境变量 + .env(本地)。"""
    # 1. 内存缓存（无论什么环境都要更新）
    _token_cache["access_token"] = access_token
    _token_cache["refresh_token"] = refresh_token
    _token_cache["expires_at"] = expires_at
    _token_cache["last_updated"] = datetime.now()

    # 2. 数据库（生产环境持久化的关键，重启后从这里恢复）
    _save_tokens_to_db(access_token, refresh_token, expires_at)

    # 3. os.environ（同进程内 settings 读取）
    os.environ["TK_AUTH_ACCESS_TOKEN"] = access_token
    os.environ["TK_AUTH_REFRESH_TOKEN"] = refresh_token
    os.environ["TK_TOKEN_EXPIRES_AT"] = expires_at.isoformat()

    # 4. .env 文件（本地开发用；生产环境文件不存在则跳过）
    try:
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".env",
        )
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = _replace_env_var(content, "TK_AUTH_ACCESS_TOKEN", access_token)
        content = _replace_env_var(content, "TK_AUTH_REFRESH_TOKEN", refresh_token)
        content = _replace_env_var(content, "TK_TOKEN_EXPIRES_AT", expires_at.isoformat())
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Tokens saved to .env successfully")
    except FileNotFoundError:
        logger.info("Tokens saved to DB only (.env not present, production env)")
    except OSError as e:
        logger.warning(f"Tokens saved to DB only (.env write failed: {e})")


def _replace_env_var(content: str, key: str, value: str) -> str:
    import re
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    
    if re.search(pattern, content, re.MULTILINE):
        return re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        return content + f"\n{replacement}"


def _is_token_expiring_soon() -> bool:
    if _token_cache["expires_at"] is None:
        return True
    
    now = datetime.now()
    threshold = _token_cache["expires_at"] - timedelta(minutes=REFRESH_THRESHOLD_MINUTES)
    
    return now >= threshold


def exchange_auth_code(auth_code: str) -> bool:
    if not auth_code:
        logger.error("No auth_code provided")
        return False

    if not settings.TK_PARTNER_APP_KEY or not settings.TK_PARTNER_APP_SECRET:
        logger.error("TikTok Partner App Key/Secret not configured")
        return False

    params = {
        "app_key": settings.TK_PARTNER_APP_KEY,
        "app_secret": settings.TK_PARTNER_APP_SECRET,
        "auth_code": auth_code,
        "grant_type": "authorized_code",
    }

    try:
        logger.info("Exchanging auth_code for TikTok access token...")
        response = requests.get(TIKTOK_AUTH_URL, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("code") != 0:
            logger.error(f"Auth code exchange failed: code={result.get('code')}, message={result.get('message')}")
            return False

        data = result.get("data", {})
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = int(data.get("expires_in", 86400))

        if not access_token or not refresh_token:
            logger.error("Auth code exchange response missing access_token or refresh_token")
            return False

        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        _save_tokens(access_token, refresh_token, expires_at)
        
        logger.info(f"Auth code exchange successful. Token expires at: {expires_at}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Auth code exchange request failed: {e}")
        try:
            if response:
                logger.error(f"Response content: {response.text[:500]}")
        except:
            pass
        return False


def _refresh_token() -> bool:
    refresh_token = _token_cache["refresh_token"] or settings.TK_AUTH_REFRESH_TOKEN
    
    if not refresh_token:
        logger.error("No refresh_token available, cannot refresh")
        return False

    if not settings.TK_PARTNER_APP_KEY or not settings.TK_PARTNER_APP_SECRET:
        logger.error("TikTok Partner App Key/Secret not configured")
        return False

    params = {
        "app_key": settings.TK_PARTNER_APP_KEY,
        "app_secret": settings.TK_PARTNER_APP_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        logger.info("Refreshing TikTok access token...")
        response = requests.get(TIKTOK_REFRESH_URL, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("code") != 0:
            logger.error(f"Token refresh failed: code={result.get('code')}, message={result.get('message')}")
            return False

        data = result.get("data", {})
        new_access_token = data.get("access_token")
        new_refresh_token = data.get("refresh_token", refresh_token)
        # TK API 有时返回 expires_in=0，用默认值 86400（24h）兜底
        expires_in = int(data.get("expires_in") or 86400)

        if not new_access_token:
            logger.error("Refresh response did not contain access_token")
            return False

        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        _save_tokens(new_access_token, new_refresh_token, expires_at)
        
        logger.info(f"Token refresh successful. New token expires at: {expires_at}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Token refresh request failed: {e}")
        try:
            if response:
                logger.error(f"Response content: {response.text[:500]}")
        except:
            pass
        return False


def get_access_token(force_refresh: bool = False) -> Optional[str]:
    if _token_cache["access_token"] is None:
        _load_tokens()

    if force_refresh or not _token_cache["access_token"] or _is_token_expiring_soon():
        if not _refresh_token():
            logger.warning("Token refresh failed, using existing token if available")
            if _token_cache["access_token"]:
                return _token_cache["access_token"]
            return None

    return _token_cache["access_token"]


def get_refresh_token() -> Optional[str]:
    if _token_cache["refresh_token"] is None:
        _load_tokens()
    return _token_cache["refresh_token"]


def get_token_expires_at() -> Optional[datetime]:
    if _token_cache["expires_at"] is None:
        _load_tokens()
    return _token_cache["expires_at"]


def set_initial_tokens(access_token: str, refresh_token: str, expires_in_seconds: int = 86400):
    expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)
    _save_tokens(access_token, refresh_token, expires_at)
    logger.info(f"Initial tokens set. Expires at: {expires_at}")


def get_token_status() -> Dict[str, Any]:
    if _token_cache["access_token"] is None:
        _load_tokens()
    
    now = datetime.now()
    expires_at = _token_cache["expires_at"]
    
    status = {
        "has_access_token": bool(_token_cache["access_token"]),
        "has_refresh_token": bool(_token_cache["refresh_token"]),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "is_expiring_soon": _is_token_expiring_soon(),
        "last_updated": _token_cache["last_updated"].isoformat() if _token_cache["last_updated"] else None,
    }
    
    if expires_at:
        remaining = (expires_at - now).total_seconds()
        status["remaining_seconds"] = remaining
        status["remaining_hours"] = remaining / 3600
    
    return status


def validate_and_refresh():
    token = get_access_token()
    if token:
        logger.info(f"Token is valid, expires in ~{get_token_status().get('remaining_hours', 0):.1f} hours")
    else:
        logger.error("No valid access token available")
    return token