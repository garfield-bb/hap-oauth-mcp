#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
登录 → **先** getAllAccessTokenList + getRefreshTokenLogs 尝试解析已有 **access_token**；
仅当没有有效 token（或账号列表为空）时，再请求 **oauth2Url** 引导用户浏览器授权，然后再次拉日志 → 输出 MCP JSON。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import webbrowser

import requests

from .md_login import fetch_oauth2_url, login_mdaccount
from .oauth_api import (
    access_token_from_account_row,
    access_token_from_log,
    extract_record_list,
    get_all_access_token_list,
    get_refresh_token_logs,
    pick_account_id,
    pick_log_with_access_token,
    sort_accounts_newest_first,
)

DEFAULT_MCP_URL_TEMPLATE = "https://api2.mingdao.com/mcp?Authorization=Bearer {access_token}"


class FetchAbort(Exception):
    """中断流程并退出（与旧版 exit code 对齐）。"""

    def __init__(self, code: int) -> None:
        self.code = code


def build_mcp_json(mcp_key: str, access_token: str, url_template: str) -> dict[str, dict[str, str]]:
    url = url_template.format(access_token=access_token)
    return {mcp_key: {"url": url}}


def try_fetch_access_token(
    *,
    md_pss_token: str,
    web_origin: str,
    integration_id: str,
    api_base: str,
    log_page_size: int,
    log_poll_attempts: int,
    log_poll_interval: float,
    dump_api: bool,
    phase: str,
) -> str | None:
    """
    拉账号列表并逐账号查换票日志，解析 access_token；未找到则返回 None。
    """
    try:
        st, list_body, list_raw = get_all_access_token_list(
            api_base=api_base,
            integration_id=integration_id,
            md_pss_token=md_pss_token,
            web_origin=web_origin,
        )
    except requests.RequestException as e:
        print(f"[{phase}] getAllAccessTokenList 请求失败: {e}", file=sys.stderr)
        raise FetchAbort(5) from e

    if dump_api:
        print(f"[{phase}] getAllAccessTokenList HTTP", st, file=sys.stderr)
        print(json.dumps(list_body, ensure_ascii=False, indent=2) if list_body else list_raw[:4000], file=sys.stderr)

    if st >= 400:
        print(f"[{phase}] getAllAccessTokenList 失败 HTTP {st}", file=sys.stderr)
        print(list_raw[:2000], file=sys.stderr)
        raise FetchAbort(5)

    accounts = extract_record_list(list_body)
    if not accounts:
        print(f"[{phase}] 账号列表为空。", file=sys.stderr)
        if list_body is not None:
            print(json.dumps(list_body, ensure_ascii=False, indent=2)[:4000], file=sys.stderr)
        return None

    accounts_ordered = sort_accounts_newest_first(accounts)
    print(
        f"[{phase}] 已拉取 {len(accounts_ordered)} 个授权账号，依次查换票日志…",
        file=sys.stderr,
        flush=True,
    )

    for idx, acc_row in enumerate(accounts_ordered):
        access_token: str | None = None
        account_id = pick_account_id(acc_row)
        if not account_id:
            print(f"[{phase}] 跳过无法解析 id 的账号行", file=sys.stderr)
            continue
        aname = acc_row.get("name", "")
        print(
            f"[{phase}] 账号 [{idx + 1}/{len(accounts_ordered)}] id={account_id} name={aname!r}",
            file=sys.stderr,
            flush=True,
        )

        tok_direct = access_token_from_account_row(acc_row)
        if tok_direct:
            return tok_direct

        for attempt in range(max(1, log_poll_attempts)):
            try:
                st2, logs_body, logs_raw = get_refresh_token_logs(
                    api_base=api_base,
                    account_id=account_id,
                    md_pss_token=md_pss_token,
                    web_origin=web_origin,
                    page_size=max(1, log_page_size),
                )
            except requests.RequestException as e:
                print(f"[{phase}] getRefreshTokenLogs 请求失败: {e}", file=sys.stderr)
                raise FetchAbort(7) from e

            if dump_api:
                print(
                    f"[{phase}] getRefreshTokenLogs account={account_id} attempt {attempt + 1} HTTP {st2}",
                    file=sys.stderr,
                )
                print(
                    json.dumps(logs_body, ensure_ascii=False, indent=2) if logs_body else logs_raw[:4000],
                    file=sys.stderr,
                )

            if st2 >= 400:
                print(f"[{phase}] getRefreshTokenLogs 失败 HTTP {st2}", file=sys.stderr)
                print(logs_raw[:2000], file=sys.stderr)
                raise FetchAbort(7)

            logs = extract_record_list(logs_body)
            if not logs and isinstance(logs_body, dict):
                inner = logs_body.get("data")
                if isinstance(inner, dict):
                    for key in ("list", "records", "logs", "rows"):
                        v = inner.get(key)
                        if isinstance(v, list):
                            logs = [x for x in v if isinstance(x, dict)]
                            break

            log_row = pick_log_with_access_token(logs)
            if log_row is not None:
                access_token = access_token_from_log(log_row)
                if access_token:
                    return access_token
            if attempt + 1 < max(1, log_poll_attempts):
                print(
                    f"[{phase}] 本账号暂无有效 token，{log_poll_interval}s 后重试 ({attempt + 1}/{log_poll_attempts})…",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(log_poll_interval)

        print(f"[{phase}] 账号 {account_id} 日志中无有效 access_token，试下一账号…", file=sys.stderr, flush=True)

    print(f"[{phase}] 所有账号均未解析到有效 access_token。", file=sys.stderr, flush=True)
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="登录并生成明道 MCP 个人配置（Cursor 等）")
    p.add_argument(
        "--base-url",
        default=os.environ.get("MINGDAO_BASE_URL", "https://www.mingdao.com"),
        help="Web 登录页站点根地址",
    )
    p.add_argument("--account", default=os.environ.get("MINGDAO_ACCOUNT", ""), help="邮箱或手机号（+86…）")
    p.add_argument("--password", default=os.environ.get("MINGDAO_PASSWORD", ""), help="密码")
    p.add_argument(
        "--oauth-app-id",
        default=os.environ.get("MINGDAO_OAUTH_APP_ID", ""),
        help="集成应用 id（与 authorize / getAllAccessTokenList 的 id 一致）",
    )
    p.add_argument(
        "--api-base-url",
        default=os.environ.get("MINGDAO_API_BASE_URL", "https://api.mingdao.com"),
        help="API 根地址",
    )
    p.add_argument(
        "--mcp-key",
        default=os.environ.get("MINGDAO_MCP_KEY", "HAP Personal MCP"),
        help="生成 JSON 中的顶层 key，默认 HAP Personal MCP",
    )
    p.add_argument(
        "--mcp-url-template",
        default=os.environ.get("MINGDAO_MCP_URL_TEMPLATE", DEFAULT_MCP_URL_TEMPLATE),
        help="含 {access_token} 占位符的 MCP URL 模板",
    )
    p.add_argument(
        "--no-open-browser",
        action="store_true",
        help="只打印授权 URL，不自动打开浏览器",
    )
    p.add_argument(
        "--skip-wait",
        action="store_true",
        help="不等待按 Enter（适用于已在浏览器完成 OAuth 后再拉 token）",
    )
    p.add_argument(
        "--dump-api",
        action="store_true",
        help="将接口原始 JSON 打到 stderr（调试用）",
    )
    p.add_argument(
        "--captcha-type",
        type=int,
        default=None,
        help="登录可选 captchaType",
    )
    p.add_argument(
        "--log-page-size",
        type=int,
        default=int(os.environ.get("MINGDAO_LOG_PAGE_SIZE", "100")),
        help="getRefreshTokenLogs 的 pageSize",
    )
    p.add_argument(
        "--log-poll-attempts",
        type=int,
        default=int(os.environ.get("MINGDAO_LOG_POLL_ATTEMPTS", "10")),
        help="拉日志未找到 access_token 时重试次数（授权后日志可能延迟写入）",
    )
    p.add_argument(
        "--log-poll-interval",
        type=float,
        default=float(os.environ.get("MINGDAO_LOG_POLL_INTERVAL", "2")),
        help="两次拉日志之间的间隔秒数",
    )
    args = p.parse_args()

    acc = (args.account or "").strip()
    pwd = args.password or ""
    app_id = (args.oauth_app_id or "").strip()
    if not acc or not pwd:
        print("请提供 --account 与 --password", file=sys.stderr)
        return 2
    if not app_id:
        print("请提供 --oauth-app-id（集成应用 id）", file=sys.stderr)
        return 2

    try:
        token, origin, _session, status, _login_body = login_mdaccount(
            account=acc,
            password=pwd,
            base_url=args.base_url,
            captcha_type=args.captcha_type,
        )
    except requests.RequestException as e:
        print(f"登录请求失败: {e}", file=sys.stderr)
        return 1

    if status >= 400 or not token:
        print("登录失败：未拿到 md_pss_id", file=sys.stderr)
        return 3

    access_token: str | None = None
    try:
        access_token = try_fetch_access_token(
            md_pss_token=token,
            web_origin=origin,
            integration_id=app_id,
            api_base=args.api_base_url,
            log_page_size=args.log_page_size,
            log_poll_attempts=args.log_poll_attempts,
            log_poll_interval=args.log_poll_interval,
            dump_api=args.dump_api,
            phase="先查账号与日志",
        )
    except FetchAbort as e:
        return e.code

    if access_token:
        out = build_mcp_json(args.mcp_key, access_token, args.mcp_url_template)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(
        "未在已有授权记录中解析到有效 access_token，需要获取 OAuth 授权地址并在浏览器中完成授权。",
        file=sys.stderr,
        flush=True,
    )
    try:
        oauth_status, oauth_body, oauth_url, oauth_raw = fetch_oauth2_url(
            api_base=args.api_base_url,
            app_id=app_id,
            md_pss_token=token,
            web_origin=origin,
            dump=False,
        )
    except requests.RequestException as e:
        print(f"获取授权地址失败: {e}", file=sys.stderr)
        return 4
    if oauth_status >= 400 or not oauth_url:
        print("获取授权地址失败:", file=sys.stderr)
        print(oauth_body or oauth_raw[:2000], file=sys.stderr)
        return 4

    print("请在浏览器中完成 OAuth 授权：", flush=True)
    print(oauth_url, flush=True)
    if not args.no_open_browser:
        try:
            webbrowser.open(oauth_url, new=1)
        except (OSError, TypeError) as e:
            print(f"（无法自动打开浏览器: {e}）", file=sys.stderr)

    if not args.skip_wait:
        try:
            input("授权完成后按 Enter 继续拉取 token… ")
        except EOFError:
            print("", file=sys.stderr)
            return 2
    else:
        print("（--skip-wait：立即再次拉取账号列表与日志）", file=sys.stderr, flush=True)

    try:
        access_token = try_fetch_access_token(
            md_pss_token=token,
            web_origin=origin,
            integration_id=app_id,
            api_base=args.api_base_url,
            log_page_size=args.log_page_size,
            log_poll_attempts=args.log_poll_attempts,
            log_poll_interval=args.log_poll_interval,
            dump_api=args.dump_api,
            phase="授权后",
        )
    except FetchAbort as e:
        return e.code

    if not access_token:
        print(
            "授权后仍未解析到 access_token；可稍后重试本命令，或检查集成应用 id 与网络。",
            file=sys.stderr,
        )
        return 8

    out = build_mcp_json(args.mcp_key, access_token, args.mcp_url_template)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
