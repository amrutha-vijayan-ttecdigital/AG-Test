"""Lucid REST API client shared by the design skills."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from .errors import LucidApiError, LucidConfigError


@dataclass(frozen=True)
class LucidClientConfig:
    api_base: str = "https://api.lucid.co/v1"
    timeout: tuple[float, float] = (10.0, 60.0)
    max_retries: int = 4
    user_agent: str = "lucid-core/1"


class LucidClient:
    """Small Lucid API client with typed errors and bounded retry behavior."""

    def __init__(self, token: str | None = None, config: LucidClientConfig | None = None):
        self.config = config or LucidClientConfig()
        self.token = token or os.getenv("LUCID_API_KEY") or os.getenv("LUCID_TOKEN")
        if not self.token:
            raise LucidConfigError("Set LUCID_API_KEY. LUCID_TOKEN is accepted as a deprecated alias.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Lucid-Api-Version": "1",
                "User-Agent": self.config.user_agent,
            }
        )

    def fetch_document_contents(self, document_id: str) -> dict[str, Any]:
        return self._json("GET", f"/documents/{document_id}/contents")

    def export_page_png(self, document_id: str, *, page_id: str | None = None, page_index: int | None = None) -> bytes:
        params: dict[str, Any] = {}
        if page_id:
            params["pageId"] = page_id
        elif page_index is not None:
            params["page"] = page_index
        return self._bytes("GET", f"/documents/{document_id}", accept="image/png", params=params)

    def _json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = self._request(method, path, accept="application/json", **kwargs)
        content_type = resp.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise LucidApiError(f"Expected JSON from Lucid, got content-type '{content_type}'", resp.status_code)
        return resp.json()

    def _bytes(self, method: str, path: str, *, accept: str, **kwargs: Any) -> bytes:
        resp = self._request(method, path, accept=accept, **kwargs)
        content_type = resp.headers.get("content-type", "")
        if accept == "image/png" and "image/png" not in content_type and not content_type.startswith("image/"):
            raise LucidApiError(f"Expected PNG image from Lucid, got content-type '{content_type}'", resp.status_code)
        return resp.content

    def _request(self, method: str, path: str, *, accept: str, **kwargs: Any) -> requests.Response:
        url = self.config.api_base.rstrip("/") + "/" + path.lstrip("/")
        headers = dict(kwargs.pop("headers", {}))
        headers["Accept"] = accept
        last_error: LucidApiError | None = None
        for attempt in range(self.config.max_retries + 1):
            resp = self.session.request(method, url, headers=headers, timeout=self.config.timeout, **kwargs)
            if resp.status_code < 400:
                return resp
            if resp.status_code in (401, 403, 404):
                raise LucidApiError(self._status_message(resp), resp.status_code)
            if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                last_error = LucidApiError(self._status_message(resp), resp.status_code)
                if attempt < self.config.max_retries:
                    time.sleep(self._retry_delay(resp, attempt))
                    continue
            raise LucidApiError(self._status_message(resp), resp.status_code)
        raise last_error or LucidApiError("Lucid API request failed")

    @staticmethod
    def _status_message(resp: requests.Response) -> str:
        body = (resp.text or "").strip().replace("\n", " ")
        if len(body) > 400:
            body = body[:397] + "..."
        return f"Lucid API returned HTTP {resp.status_code}: {body}"

    @staticmethod
    def _retry_delay(resp: requests.Response, attempt: int) -> float:
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), 30.0))
            except ValueError:
                try:
                    dt = parsedate_to_datetime(retry_after)
                    return max(0.0, min(dt.timestamp() - time.time(), 30.0))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(0.5 * (2**attempt) + random.uniform(0.0, 0.25), 8.0)

