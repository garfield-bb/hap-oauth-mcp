# -*- coding: utf-8 -*-
"""
明道云 integration/oauth2 相关 API（需 md_pss_id）。

命名说明（避免误解）：
- **getAllAccessTokenList**：返回的是当前集成下已授权的**账号列表**（每条有 id、name 等），不是「access_token 字符串列表」。
- **getRefreshTokenLogs**：返回的是指定账号下与换票/刷新 **access_token** 相关的**日志列表**，从中解析成功记录里的 token。
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urljoin

import requests

from .http_retry import post_json_retry

PATH_GET_ALL_ACCESS_TOKEN_LIST = "/integration/oauth2/getAllAccessTokenList"
PATH_GET_REFRESH_TOKEN_LOGS = "/integration/oauth2/getRefreshTokenLogs"


def integration_post(
    api_base: str,
    path: str,
    json_body: dict[str, Any],
    md_pss_token: str,
    web_origin: str,
    *,
    timeout: int = 30,
) -> tuple[int, Any | None, str]:
    url = urljoin(api_base.rstrip("/") + "/", path.lstrip("/"))
    referer = web_origin.rstrip("/") + "/"
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Authorization": f"md_pss_id {md_pss_token.strip()}",
        "Origin": web_origin,
        "Referer": referer,
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (compatible; mingdao-mcp-login/1.0)",
    }
    resp = post_json_retry(url, json=json_body, headers=headers, timeout=timeout)
    text = resp.text
    body: Any | None = None
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = None
    return resp.status_code, body, text


def get_all_access_token_list(
    *,
    api_base: str,
    integration_id: str,
    md_pss_token: str,
    web_origin: str,
) -> tuple[int, Any | None, str]:
    """POST …/getAllAccessTokenList，body `{"id": integration_id}` → 集成下**已授权账号列表**。"""
    return integration_post(
        api_base,
        PATH_GET_ALL_ACCESS_TOKEN_LIST,
        {"id": integration_id.strip()},
        md_pss_token,
        web_origin,
    )


def get_refresh_token_logs(
    *,
    api_base: str,
    account_id: str,
    md_pss_token: str,
    web_origin: str,
    page_size: int = 50,
    page_index: int = 1,
    keyword: str = "",
) -> tuple[int, Any | None, str]:
    """POST …/getRefreshTokenLogs，body 的 `id` 为**账号列表里某条账号的 id** → **换票/刷新 token 日志列表**。"""
    return integration_post(
        api_base,
        PATH_GET_REFRESH_TOKEN_LOGS,
        {
            "id": account_id.strip(),
            "pageSize": page_size,
            "pageIndex": page_index,
            "keyword": keyword,
        },
        md_pss_token,
        web_origin,
    )


def extract_record_list(body: Any) -> list[dict[str, Any]]:
    """从典型明道 JSON 中取出 dict 列表。"""
    if body is None:
        return []
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if not isinstance(body, dict):
        return []
    d = body.get("data")
    if isinstance(d, list):
        return [x for x in d if isinstance(x, dict)]
    if isinstance(d, dict):
        for key in ("list", "records", "rows", "items", "data", "accountList", "logs"):
            v = d.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def account_sort_key(acc: dict[str, Any]) -> str:
    """用于比较「哪条账号授权记录更新」；含 getAllAccessTokenList 常见的 createdDate。"""
    for k in (
        "authorizeTime",
        "authorizedTime",
        "lastAuthorizeTime",
        "lastModifiedDate",
        "updateTime",
        "modifyTime",
        "createTime",
        "createDate",
        "createdDate",
    ):
        if k in acc and acc[k] is not None:
            return str(acc[k])
    return ""


def sort_accounts_newest_first(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []
    try:
        return sorted(records, key=account_sort_key, reverse=True)
    except (TypeError, ValueError):
        return list(reversed(records))


def pick_latest_account(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    if len(records) == 1:
        return records[0]
    try:
        return max(records, key=account_sort_key)
    except (TypeError, ValueError):
        return records[-1]


def access_token_from_account_row(acc: dict[str, Any]) -> str | None:
    """部分环境下 getAllAccessTokenList 可能在账号行直接返回 token。"""
    for k in ("access_token", "accessToken", "token"):
        v = acc.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def pick_account_id(acc: dict[str, Any]) -> str | None:
    for k in ("id", "accountId", "_id"):
        v = acc.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def log_sort_key(log: dict[str, Any]) -> str:
    for k in (
        "createTime",
        "createDate",
        "createdDate",
        "modifyTime",
        "updateTime",
        "time",
        "completeDate",
        "id",
    ):
        if k in log and log[k] is not None:
            return str(log[k])
    return ""


def pick_latest_log(logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not logs:
        return None
    if len(logs) == 1:
        return logs[0]
    try:
        return max(logs, key=log_sort_key)
    except (TypeError, ValueError):
        return logs[0]


def parse_result_field(result: Any) -> dict[str, Any] | None:
    if isinstance(result, dict):
        return result
    if isinstance(result, str) and result.strip():
        try:
            parsed = json.loads(result)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _dicts_from_log_result(log: dict[str, Any]) -> list[dict[str, Any]]:
    """从日志顶层 result 与 requestCatch.json.result 等位置收集可解析的 dict。"""
    out: list[dict[str, Any]] = []
    r = parse_result_field(log.get("result"))
    if r:
        out.append(r)
    rc = log.get("requestCatch")
    if isinstance(rc, dict):
        j = rc.get("json")
        if isinstance(j, dict):
            r2 = parse_result_field(j.get("result"))
            if r2:
                out.append(r2)
    return out


def _extract_access_token_from_parsed_result(r: dict[str, Any]) -> str | None:
    """
    成功时接口可能返回顶层 access_token，或包在 data 内：
    {"data": {"access_token": "...", ...}, "success": true, "error_code": 1}
    """
    if r.get("success") is False:
        return None
    tok = r.get("access_token") or r.get("accessToken")
    if tok is not None and str(tok).strip():
        return str(tok).strip()
    inner = r.get("data")
    if isinstance(inner, dict):
        tok = inner.get("access_token") or inner.get("accessToken")
        if tok is not None and str(tok).strip():
            return str(tok).strip()
    return None


def access_token_from_log(log: dict[str, Any]) -> str | None:
    """
    从刷新日志中取 access_token。
    成功响应常在 requestCatch.json.result（JSON 字符串）里；失败时含 error_msg / success:false。
    """
    for r in _dicts_from_log_result(log):
        got = _extract_access_token_from_parsed_result(r)
        if got:
            return got
    return None


def pick_log_with_access_token(logs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """按时间从新到旧尝试，返回第一条能解析出 access_token 的日志（跳过仅失败记录）。"""
    if not logs:
        return None
    try:
        ordered = sorted(logs, key=log_sort_key, reverse=True)
    except (TypeError, ValueError):
        ordered = list(reversed(logs))
    for log in ordered:
        if access_token_from_log(log):
            return log
    return None
