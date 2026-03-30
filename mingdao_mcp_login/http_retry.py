# -*- coding: utf-8 -*-
"""对 requests.post 做有限次重试，缓解间歇性 SSL / 连接错误（如 BAD_RECORD_MAC）。"""

from __future__ import annotations

import time
from typing import Any

import requests
from requests.exceptions import RequestException


def post_json_retry(
    url: str,
    *,
    max_attempts: int = 8,
    base_delay: float = 0.4,
    **kwargs: Any,
) -> requests.Response:
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return requests.post(url, **kwargs)
        except RequestException as e:
            last = e
            if attempt + 1 < max_attempts:
                time.sleep(base_delay * (attempt + 1))
    assert last is not None
    raise last


def session_post_retry(
    session: requests.Session,
    url: str,
    *,
    max_attempts: int = 8,
    base_delay: float = 0.4,
    **kwargs: Any,
) -> requests.Response:
    """保留 Session 的 Cookie/状态，对 session.post 重试。"""
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return session.post(url, **kwargs)
        except RequestException as e:
            last = e
            if attempt + 1 < max_attempts:
                time.sleep(base_delay * (attempt + 1))
    assert last is not None
    raise last
