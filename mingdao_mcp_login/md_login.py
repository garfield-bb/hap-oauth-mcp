#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用邮箱/手机号 + 密码调用 /api/Login/MDAccountLogin，并从响应中提取 md_pss_id（会话 token）。

说明：
- account、password 在请求中需为 RSA 加密后的 Base64（本脚本通过 encrypt.py 自动加密明文）。
- 请求体字段名必须是 "account" 与 "password"（加密后），不要对调。
- captchaType：默认**不传**；需要与 Web 完全一致时再使用 --captcha-type。
- 中国大陆手机号建议使用 E.164，例如 +8615012345678。
- 成功时 token 常见于：响应头 Authorization、Set-Cookie(md_pss_id)、JSON data.sessionId（脚本已做兜底解析）。
- 传入 `--oauth-app-id` 时，登录成功后会再请求 `POST {api_base}/integration/oauth2/authorize`（默认 api.mingdao.com），解析 `oauth2Url`。
详见仓库 README.md。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from .encrypt import encrypt
from .http_retry import post_json_retry, session_post_retry

DEFAULT_PATH = "/api/Login/MDAccountLogin"
OAUTH2_AUTHORIZE_PATH = "/integration/oauth2/authorize"


def _deep_find(obj: Any, keys: set[str]) -> str | None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, str) and v.strip():
                return v.strip()
            found = _deep_find(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find(item, keys)
            if found:
                return found
    return None


def extract_md_pss_id(
    body: dict[str, Any] | list[Any] | None,
    headers: dict[str, str],
) -> tuple[str | None, str | None]:
    """
    返回 (完整 Authorization 值, 纯 token)。
    明道云 Web 端常见为 Authorization: md_pss_id <token>
    """
    auth_keys = {
        "authorization",
        "Authorization",
        "md_pss_id",
        "md_pass_id",
        "mdPssId",
        "token",
        "accessToken",
    }
    h_lower = {k.lower(): v for k, v in headers.items()}
    for hk in ("authorization", "x-authorization"):
        raw = h_lower.get(hk)
        if raw and "md_pss" in raw.lower():
            m = re.search(r"(md_pss_id\s+[^\s]+|md_pss_id[^\s]*)", raw, re.I)
            if m:
                full = m.group(0).strip()
                parts = full.split(None, 1)
                token = parts[1] if len(parts) > 1 else full
                return full, token

    if body is not None:
        full = _deep_find(body, auth_keys)
        if full:
            full = full.strip()
            if full.lower().startswith("md_pss_id"):
                parts = full.split(None, 1)
                token = parts[1] if len(parts) > 1 else full
                return full, token
            return full, full
        if isinstance(body, (dict, list)):
            raw = json.dumps(body, ensure_ascii=False)
            m = re.search(r"md_pss_id[\s:=]+([^\s\"',}]+)", raw, re.I)
            if m:
                token = m.group(1).strip().strip('"').strip("'")
                return f"md_pss_id {token}", token

    return None, None


def extract_md_pss_id_fallback(
    body: dict[str, Any] | list[Any] | None,
    session: requests.Session,
) -> tuple[str | None, str | None]:
    """
    邮箱/密码登录成功时，md_pss_id 常出现在 Set-Cookie（session.cookies）或 JSON 的 data.sessionId。
    """
    ck = session.cookies.get("md_pss_id")
    if ck and str(ck).strip():
        t = str(ck).strip()
        return f"md_pss_id {t}", t
    if isinstance(body, dict):
        data = body.get("data")
        if isinstance(data, dict):
            sid = data.get("sessionId")
            if isinstance(sid, str) and sid.strip():
                t = sid.strip()
                return f"md_pss_id {t}", t
    return None, None


def build_login_url(base: str) -> str:
    base = base.rstrip("/") + "/"
    return urljoin(base, DEFAULT_PATH.lstrip("/"))


def build_oauth_authorize_url(api_base: str) -> str:
    base = api_base.rstrip("/") + "/"
    return urljoin(base, OAUTH2_AUTHORIZE_PATH.lstrip("/"))


def extract_oauth2_url(body: Any) -> str | None:
    """从 OAuth2 authorize 响应 JSON 中解析授权页 URL。"""
    if body is None:
        return None
    u = _deep_find(body, {"oauth2Url", "oauth2_url", "oauthUrl"})
    return u if u else None


def fetch_oauth2_url(
    *,
    api_base: str,
    app_id: str,
    md_pss_token: str,
    web_origin: str,
    dump: bool = False,
) -> tuple[int, dict[str, Any] | list[Any] | None, str | None, str]:
    """
    POST {api_base}/integration/oauth2/authorize，请求体 {"id": app_id}。
    返回 (http_status, json_body, oauth2Url 或 None, 原始响应文本)。
    """
    url = build_oauth_authorize_url(api_base)
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
    try:
        resp = post_json_retry(url, json={"id": app_id.strip()}, headers=headers, timeout=30)
    except requests.RequestException as e:
        if dump:
            print(f"OAuth 请求失败: {e}", file=sys.stderr)
        raise
    text = resp.text
    body: dict[str, Any] | list[Any] | None = None
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = None
    if dump:
        print("OAuth HTTP", resp.status_code, file=sys.stderr)
        print(text[:8000], file=sys.stderr)
    oauth_url = extract_oauth2_url(body)
    return resp.status_code, body, oauth_url, text


def login_mdaccount(
    *,
    account: str,
    password: str,
    base_url: str = "https://www.mingdao.com",
    is_cookie: bool = False,
    captcha_type: int | None = None,
) -> tuple[str | None, str, requests.Session, int, dict[str, Any] | list[Any] | None]:
    """
    调用 MDAccountLogin，返回 (md_pss_id, Web Origin, session, http_status, 响应 JSON)。
    md_pss_id 失败时为 None。
    """
    acc = (account or "").strip()
    pwd = password or ""
    if not acc or not pwd:
        return None, "", requests.Session(), 0, None

    payload: dict[str, Any] = {
        "account": encrypt(acc),
        "password": encrypt(pwd),
        "isCookie": bool(is_cookie),
    }
    if captcha_type is not None:
        payload["captchaType"] = captcha_type

    url = build_login_url(base_url)
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"

    session = requests.Session()
    session.headers.update(
        {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": origin,
            "Referer": urljoin(origin + "/", "login"),
            "User-Agent": "Mozilla/5.0 (compatible; mingdao-mcp-login/1.0)",
        }
    )

    resp = session_post_retry(session, url, json=payload, timeout=30)
    body: dict[str, Any] | list[Any] | None = None
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = None

    full_auth, token = extract_md_pss_id(body, dict(resp.headers))
    if token is None:
        full_auth, token = extract_md_pss_id_fallback(body, session)

    return token, origin, session, resp.status_code, body


def main() -> int:
    p = argparse.ArgumentParser(description="明道云 MDAccountLogin 并提取 md_pss_id")
    p.add_argument(
        "--base-url",
        default=os.environ.get("MINGDAO_BASE_URL", "https://www.mingdao.com"),
        help="站点根地址，如 https://meihua.mingdao.com 或 https://www.mingdao.com",
    )
    p.add_argument(
        "--account",
        default=os.environ.get("MINGDAO_ACCOUNT", ""),
        help="登录邮箱或手机号（明文）；手机号建议 +86 格式，如 +8615012345678",
    )
    p.add_argument("--password", default=os.environ.get("MINGDAO_PASSWORD", ""), help="密码（明文）；建议用环境变量")
    p.add_argument(
        "--is-cookie",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="是否记住登录（默认 false）",
    )
    p.add_argument(
        "--captcha-type",
        type=int,
        default=None,
        help="可选；传入时才会在 JSON 里带 captchaType（默认不传该字段）",
    )
    p.add_argument("--dump-response", action="store_true", help="打印完整响应 JSON（调试用）")
    p.add_argument(
        "--oauth-app-id",
        default=os.environ.get("MINGDAO_OAUTH_APP_ID", ""),
        help="集成/应用 id；若提供则在登录成功后请求 OAuth2 authorize 并解析 oauth2Url",
    )
    p.add_argument(
        "--api-base-url",
        default=os.environ.get("MINGDAO_API_BASE_URL", "https://api.mingdao.com"),
        help="API 域名根地址（authorize 接口所在），默认 https://api.mingdao.com",
    )
    p.add_argument("--dump-oauth-response", action="store_true", help="打印 OAuth authorize 原始响应（调试用）")
    args = p.parse_args()

    acc = (args.account or "").strip()
    pwd = args.password or ""
    if not acc or not pwd:
        print("请提供 --account 与 --password（或环境变量 MINGDAO_ACCOUNT / MINGDAO_PASSWORD）", file=sys.stderr)
        return 2

    try:
        token, origin, session, status, body = login_mdaccount(
            account=acc,
            password=pwd,
            base_url=args.base_url,
            is_cookie=bool(args.is_cookie),
            captcha_type=args.captcha_type,
        )
    except requests.RequestException as e:
        print(f"请求失败: {e}", file=sys.stderr)
        return 1

    url = build_login_url(args.base_url)
    text = ""
    if body is not None:
        try:
            text = json.dumps(body, ensure_ascii=False)
        except (TypeError, ValueError):
            text = ""

    if args.dump_response:
        print("HTTP", status)
        print(text[:8000] if text else "")

    full_auth = None
    if token:
        full_auth = f"md_pss_id {token}"

    out: dict[str, Any] = {
        "http_status": status,
        "login_url": url,
        "md_pss_id": token,
        "authorization": full_auth,
    }
    if args.captcha_type is not None:
        out["captchaType"] = args.captcha_type
    if token is None and isinstance(body, dict):
        out["hint"] = "未在响应头/JSON 中解析到 md_pss_id，请使用 --dump-response 查看结构或浏览器抓包"

    oauth_app_id = (args.oauth_app_id or "").strip()
    if oauth_app_id and token:
        auth_url = build_oauth_authorize_url(args.api_base_url)
        out["oauth2_authorize_url"] = auth_url
        try:
            oauth_status, oauth_body, oauth_url, oauth_raw = fetch_oauth2_url(
                api_base=args.api_base_url,
                app_id=oauth_app_id,
                md_pss_token=token,
                web_origin=origin,
                dump=args.dump_oauth_response,
            )
        except requests.RequestException:
            out["oauth2_error"] = "OAuth authorize 请求失败"
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 1
        out["oauth2_http_status"] = oauth_status
        out["oauth2Url"] = oauth_url
        if oauth_url is None:
            if oauth_body is not None:
                out["oauth2_response"] = oauth_body
            else:
                out["oauth2_body_preview"] = (oauth_raw or "")[:2000]

    print(json.dumps(out, ensure_ascii=False, indent=2))

    if status >= 400:
        return 1
    if token is None:
        return 3
    if oauth_app_id and token:
        oauth_st = out.get("oauth2_http_status")
        oauth_u = out.get("oauth2Url")
        if oauth_st is not None and (oauth_st >= 400 or not oauth_u):
            return 4
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
