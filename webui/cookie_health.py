"""平台登录态（cookies）预检。

批量任务启动前对涉及平台做一次轻量验证，避免下载到一半才发现 cookies 过期。
"""

import json
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import requests

try:
    from .http_utils import request_kwargs
except ImportError:
    from http_utils import request_kwargs


@dataclass(frozen=True)
class CookieHealth:
    ok: bool
    platform: str
    detail: str
    suggestion: str = ""
    skipped: bool = False


def _load_cookie_jar(cookiefile: Path) -> MozillaCookieJar | None:
    jar = MozillaCookieJar(str(cookiefile))
    try:
        jar.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        return None
    return jar


def _has_unexpired_cookies(jar: MozillaCookieJar) -> bool:
    import time

    now = time.time()
    for cookie in jar:
        if cookie.expires and cookie.expires < now:
            continue
        return True
    return False


def check_bilibili(cookiefile: Path) -> CookieHealth:
    jar = _load_cookie_jar(cookiefile)
    if jar is None:
        return CookieHealth(
            ok=False,
            platform="Bilibili",
            detail="bilibili.cookies.txt 无法解析。",
            suggestion="重新导出 cookies 文件，或在 .env 配置 BILIBILI_COOKIES_FROM_BROWSER=chrome。",
        )

    session = requests.Session()
    session.cookies = jar
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Origin": "https://www.bilibili.com",
        "Accept": "application/json",
    })
    try:
        resp = session.get(
            "https://api.bilibili.com/x/web-interface/nav",
            timeout=(10, 15),
            **request_kwargs(),
        )
    except requests.RequestException as exc:
        return CookieHealth(
            ok=False,
            platform="Bilibili",
            detail=f"预检请求失败：{exc}",
            suggestion="网络抖动可加 --skip-cookie-check 跳过预检；或检查 OPENROUTER_PROXY 配置。",
        )

    if resp.status_code == 412:
        return CookieHealth(
            ok=False,
            platform="Bilibili",
            detail="B 站返回 412（登录态失效或被风控）。",
            suggestion="重新登录 B 站后导出 cookies，或在 .env 配置 BILIBILI_COOKIES_FROM_BROWSER=chrome。",
        )

    try:
        data = resp.json()
    except json.JSONDecodeError:
        return CookieHealth(
            ok=False,
            platform="Bilibili",
            detail=f"响应非 JSON（HTTP {resp.status_code}）。",
            suggestion="可能被 CDN 拦截，稍后重试或加 --skip-cookie-check。",
        )

    code = data.get("code")
    if code == 0:
        uname = (data.get("data") or {}).get("uname") or "已登录"
        return CookieHealth(ok=True, platform="Bilibili", detail=f"登录态有效（{uname}）。")
    if code == -101:
        return CookieHealth(
            ok=False,
            platform="Bilibili",
            detail="未登录或 cookies 过期（code=-101）。",
            suggestion="重新登录 B 站后更新 bilibili.cookies.txt，或配置 BILIBILI_COOKIES_FROM_BROWSER=chrome。",
        )
    return CookieHealth(
        ok=False,
        platform="Bilibili",
        detail=f"B 站返回 code={code}：{data.get('message')}",
        suggestion="如确认 cookies 有效，可加 --skip-cookie-check 跳过预检。",
    )


def check_douyin(cookiefile: Path) -> CookieHealth:
    """抖音接口需要复杂签名，这里只做 cookies 文件级校验。"""
    jar = _load_cookie_jar(cookiefile)
    if jar is None:
        return CookieHealth(
            ok=False,
            platform="Douyin",
            detail="douyin.cookies.txt 无法解析。",
            suggestion="重新导出 cookies 文件，或在 .env 配置 DOUYIN_COOKIES_FROM_BROWSER=chrome。",
        )
    if not _has_unexpired_cookies(jar):
        return CookieHealth(
            ok=False,
            platform="Douyin",
            detail="cookies 已全部过期。",
            suggestion="重新登录抖音后更新 douyin.cookies.txt。",
        )
    names = {cookie.name for cookie in jar}
    key_cookies = {"SESSSID", "ttwid", "msToken", "sid_guard", "sid_tt"} & names
    if not key_cookies:
        return CookieHealth(
            ok=False,
            platform="Douyin",
            detail="cookies 文件缺少关键登录字段。",
            suggestion="确认导出的是已登录抖音账号的完整 cookies。",
        )
    return CookieHealth(
        ok=True,
        platform="Douyin",
        detail=f"cookies 文件有效（包含 {', '.join(sorted(key_cookies))}）。",
    )


def check_youtube(cookiefile: Path | None) -> CookieHealth:
    return CookieHealth(
        ok=True,
        platform="YouTube",
        detail="YouTube 预检跳过（依赖 yt-dlp 自身的错误提示）。",
        skipped=True,
    )


def check_platform(platform: str, cookiefile: Path | None) -> CookieHealth:
    if cookiefile is None or not Path(cookiefile).exists():
        return CookieHealth(
            ok=True,
            platform=platform,
            detail=f"{platform} 未配置专用 cookies，跳过预检。",
            skipped=True,
        )
    if platform == "Bilibili":
        return check_bilibili(Path(cookiefile))
    if platform == "Douyin":
        return check_douyin(Path(cookiefile))
    if platform == "YouTube":
        return check_youtube(Path(cookiefile))
    return CookieHealth(
        ok=True,
        platform=platform,
        detail=f"{platform} 暂不支持预检，跳过。",
        skipped=True,
    )


_PLATFORM_COOKIE_DOMAINS: dict[str, tuple[str, ...]] = {
    "Bilibili": ("bilibili.com", "biligaming.com", "bilivideo.com", "bilivideo.cn", "biliapi.net"),
    "Douyin": ("douyin.com", "iesdouyin.com", "amemv.com", "snssdk.com", "toutiao.com"),
    "YouTube": ("youtube.com", "youtu.be", "google.com", "googleapis.com", "googlevideo.com"),
}


def _platform_cookie_domains(platform: str) -> tuple[str, ...]:
    return _PLATFORM_COOKIE_DOMAINS.get(platform, ())


def refresh_platform_cookies(
    platform: str,
    cookiefile: Path,
    *,
    browser_spec: tuple[str, str | None, str | None, str | None] | None = None,
) -> CookieHealth:
    """从浏览器提取最新 cookies 写入 cookiefile，然后做一次健康检查。

    本地模式有效；Docker 容器内调用会失败（无法访问宿主机浏览器）。
    browser_spec: (browser_name, profile, keyring, container)。
    """
    from yt_dlp.cookies import YoutubeDLCookieJar, extract_cookies_from_browser

    if browser_spec is None:
        browser_spec = ("chrome", None, None, None)
    browser_name, profile, keyring, container = browser_spec
    domains = _platform_cookie_domains(platform)

    try:
        extracted = extract_cookies_from_browser(
            browser_name,
            profile=profile,
            keyring=keyring,
            container=container,
        )
    except Exception as exc:
        return CookieHealth(
            ok=False,
            platform=platform,
            detail=f"从 {browser_name} 提取 cookies 失败：{exc}",
            suggestion=(
                f"确认 {browser_name} 已登录 {platform}；"
                "且 webui 跑在能访问浏览器的宿主机（非容器）环境。"
            ),
        )

    matching = [c for c in extracted if any(d in (c.domain or "") for d in domains)]
    if not matching:
        return CookieHealth(
            ok=False,
            platform=platform,
            detail=f"在 {browser_name} 里没找到 {platform} 相关 cookies。",
            suggestion=f"先在 {browser_name} 里访问并登录 {platform}，再点刷新。",
        )

    try:
        cookiefile.parent.mkdir(parents=True, exist_ok=True)
        backup = cookiefile.with_suffix(cookiefile.suffix + ".bak-auto")
        if cookiefile.exists():
            import shutil
            shutil.copy2(cookiefile, backup)
        jar = YoutubeDLCookieJar(filename=str(cookiefile))
        for cookie in matching:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True, ignore_expires=True)
    except Exception as exc:
        return CookieHealth(
            ok=False,
            platform=platform,
            detail=f"写入 {cookiefile} 失败：{exc}",
            suggestion=f"检查 {cookiefile.parent} 目录权限和磁盘空间。",
        )

    return check_platform(platform, cookiefile)
