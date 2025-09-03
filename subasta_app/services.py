import os
import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Config y errores
@dataclass(frozen=True)
class WAConfig:
    base_url: str = os.getenv("WHATSAPP_SERVICE_BASEURL", "http://localhost:3000")
    api_key: str = os.getenv("WHATSAPP_SERVICE_API_KEY", "")
    timeout_seconds: int = int(os.getenv("WHATSAPP_SERVICE_TIMEOUT", "10"))
    # Retries con backoff exponencial (0.5s, 1s, 2s, 4s ...)
    max_retries: int = int(os.getenv("WHATSAPP_SERVICE_MAX_RETRIES", "3"))


class WhatsAppServiceError(Exception):
    """Error genérico al llamar al servicio de WhatsApp."""


class WhatsAppServiceUnavailable(WhatsAppServiceError):
    """Error cuando el servicio está no disponible (5xx / conexión)."""


_cfg = WAConfig()

# Sesión HTTP con retries
_session = requests.Session()
_retry = Retry(
    total=_cfg.max_retries,
    backoff_factor=0.5,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]),
    raise_on_status=False,
)
_adapter = HTTPAdapter(max_retries=_retry)
_session.mount("http://", _adapter)
_session.mount("https://", _adapter)


def _headers(idempotency_key: Optional[str] = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if _cfg.api_key:
        h["X-Api-Key"] = _cfg.api_key
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


def _parse_json(resp: Response) -> Dict[str, Any]:
    # 204 No Content -> OK sin body
    if resp.status_code == 204 or not resp.content:
        return {"ok": True, "status_code": resp.status_code}
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype.lower():
        try:
            data = resp.json()
        except json.JSONDecodeError:
            raise WhatsAppServiceError("Invalid JSON in response")
        if "ok" not in data:
            data["ok"] = 200 <= resp.status_code < 300
        data["status_code"] = resp.status_code
        return data
    return {
        "ok": 200 <= resp.status_code < 300,
        "status_code": resp.status_code,
        "raw": resp.text,
    }


def _request(
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    url = urljoin(_cfg.base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        resp = _session.request(
            method=method.upper(),
            url=url,
            headers=_headers(idempotency_key),
            json=json_body,
            timeout=_cfg.timeout_seconds,
        )
    except requests.RequestException as e:
        # WhatsApp error: 5xx, connection, DNS
        raise WhatsAppServiceUnavailable(f"WhatsApp service unreachable: {e}") from e

    if 500 <= resp.status_code < 600:
        raise WhatsAppServiceUnavailable(f"Service error {resp.status_code}: {resp.text[:300]}")
    if resp.status_code == 401:
        raise WhatsAppServiceError("Unauthorized (check X-Api-Key)")
    if resp.status_code == 403:
        raise WhatsAppServiceError("Forbidden")
    if resp.status_code == 404:
        raise WhatsAppServiceError("Not Found")
    if resp.status_code == 409:
        return _parse_json(resp)
    if not (200 <= resp.status_code < 300) and resp.status_code != 204:
        # 4xx
        raise WhatsAppServiceError(f"HTTP {resp.status_code}: {resp.text[:300]}")

    return _parse_json(resp)

    # Ordena al servicio de WhatsApp iniciar la subasta.
    # Path-based API simple: POST /auctions/{id}/start


def wa_start(auction_id: int, *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(auction_id, int) or auction_id <= 0:
        raise ValueError("auction_id must be a positive integer")
    return _request("POST", f"/auctions/{auction_id}/start", idempotency_key=idempotency_key)


# Ordena al servicio de WhatsApp cerrar la subasta.
# POST /auctions/{id}/close
def wa_close(auction_id: int, *, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
    if not isinstance(auction_id, int) or auction_id <= 0:
        raise ValueError("auction_id must be a positive integer")
    return _request("POST", f"/auctions/{auction_id}/close", idempotency_key=idempotency_key)


# helper -> health
def wa_health() -> Dict[str, Any]:
    """Chequeo rápido del servicio de WhatsApp (si existe endpoint)."""
    try:
        return _request("GET", "/health")
    except WhatsAppServiceUnavailable as e:
        return {"ok": False, "error": str(e)}
    except WhatsAppServiceError as e:
        return {"ok": False, "error": str(e)}
