import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import yt_dlp
from nonebot import on_keyword, on_message
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent, MessageSegment
from nonebot.log import logger
from nonebot.params import ArgPlainText
from nonebot.typing import T_State

# 下载目录（放在插件目录下的 downloads 文件夹）
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 超过该大小（字节）不直接发视频消息，避免 QQ 发送失败
MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50MB

# 抖音/快手等需要 cookie 才能下载，从浏览器导出后放到插件目录下
COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

URL_RE = re.compile(r"https?://[^\s\"'<>\[\]]+")


def _rank_urls(urls):
    """过滤掉图片等非视频链接，视频链接优先"""
    video, others = [], []
    for u in urls:
        if re.search(r"\.(jpg|jpeg|png|gif|webp|ico)(\?|$)", u, re.I):
            continue
        if "b23.tv" in u or "bilibili" in u or "acg.tv" in u:
            video.append(u)
        else:
            others.append(u)
    return video + others


def _urls_from_json(raw):
    """从 json 卡片里正确解析链接（解析 JSON，避免正则误提取）"""
    unescaped = raw.replace("\\/", "/")
    try:
        obj = json.loads(unescaped)
    except Exception:
        return URL_RE.findall(unescaped)

    found = []

    def walk(o):
        if isinstance(o, str):
            if o.startswith("http"):
                found.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(obj)
    ranked = _rank_urls(found)
    return ranked if ranked else URL_RE.findall(unescaped)


def _extract_urls(event: MessageEvent) -> list:
    """从消息里提取所有链接（支持纯文本、分享卡片、json/xml 卡片）"""
    urls = []
    urls.extend(URL_RE.findall(event.get_plaintext()))
    for seg in event.get_message():
        if seg.type == "share":
            urls.append(seg.data.get("url", ""))
            continue
        if seg.type == "json":
            urls.extend(_urls_from_json(seg.data.get("data", "")))
        elif seg.type == "xml":
            urls.extend(URL_RE.findall(seg.data.get("data", "").replace("\\/", "/")))
        elif seg.type == "text":
            urls.extend(URL_RE.findall(seg.data.get("text", "")))
    return [u for u in urls if u]


def _is_douyin(url: str) -> bool:
    """判断是否是抖音链接"""
    return "douyin.com" in url or "iesdouyin.com" in url


def _parse_douyin(url: str):
    """调用 dwo.cc 接口解析抖音，返回 data（含 type/url/images 等字段）"""
    api = "https://openapi.dwo.cc/api/svparse?url=" + urllib.parse.quote(url, safe="")
    req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise Exception("抖音接口繁忙（请求过于频繁），请稍后再试")
        raise Exception(f"解析失败：HTTP {e.code}")
    try:
        data = json.loads(raw)
    except Exception:
        logger.warning(f"[抖音解析] 返回非JSON url={url} raw={raw[:300]}")
        raise Exception("解析失败：接口返回异常")
    if data.get("code") != 200:
        logger.warning(f"[抖音解析] code异常 url={url} 返回={raw[:500]}")
        if data.get("code") == 429:
            raise Exception("抖音接口繁忙（请求过于频繁），请稍后再试")
        raise Exception(f"解析失败：{data.get('msg', '未知错误')}")
    d = data.get("data") or {}
    if not d:
        raise Exception("解析结果为空")
    return d


def _download_direct(url: str, filepath: str):
    """用 urllib 下载直链到本地文件"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(filepath, "wb") as f:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)


async def _send_douyin_images(bot: Bot, data: dict):
    """下载并发送抖音图文（多张图片）"""
    images = data.get("images") or []
    if not images:
        await video_matcher.send("❌ 图文里没有图片")
        return
    title = data.get("title") or "抖音图文"
    image_files = []
    for i, img_url in enumerate(images):
        fname = os.path.join(DOWNLOAD_DIR, f"douyin_img_{int(time.time() * 1000)}_{i}.jpg")
        _download_direct(img_url, fname)
        image_files.append(fname)
    segs = [MessageSegment.text(f"{title}\n")]
    for f in image_files:
        uri = "file:///" + os.path.abspath(f).replace("\\", "/")
        segs.append(MessageSegment.image(file=uri))
    await video_matcher.send(Message(segs))


easter_egg = on_keyword("我们还行吧", priority=5, block=True)


@easter_egg.handle()
async def handle_easter_egg():
    await easter_egg.finish("那当然")


video_matcher = on_message(priority=10, block=False)


@video_matcher.handle()
async def handle_video(bot: Bot, event: MessageEvent, state: T_State):
    urls = _extract_urls(event)
    if not urls:
        await video_matcher.finish()

    state["url"] = urls[0]


@video_matcher.got("confirm", prompt="🔍 检测到链接，是否要下载？")
async def handle_confirm(bot: Bot, event: MessageEvent, state: T_State, confirm: str = ArgPlainText("confirm")):
    if confirm.strip() != "是":
        await video_matcher.finish("已取消下载")
    url = state.get("url")
    prefix = "好的！尊敬的【你的昵称】大人\n" if event.get_user_id() == "【你的QQ号】" else ""
    await video_matcher.send(prefix + "🔍 开始解析并下载...")
    await _download_and_send(bot, event, url)


async def _download_and_send(bot: Bot, event: MessageEvent, url: str):
    try:
        if _is_douyin(url):
            data = _parse_douyin(url)
            if data.get("type") == "image":
                # 图文：下载并发送图片
                await _send_douyin_images(bot, data)
                return
            # 视频：拿直链下载
            direct_url = data.get("url") or ""
            title = data.get("title") or "抖音视频"
            if not direct_url:
                raise Exception("解析结果里没有视频直链")
            filename = os.path.join(DOWNLOAD_DIR, f"douyin_{int(time.time() * 1000)}.mp4")
            _download_direct(direct_url, filename)
        else:
            # 其他平台：走 yt-dlp
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(id)s.%(ext)s"),
                "restrictfilenames": True,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "proxy": "",  # 禁用代理，避免系统残留代理导致连接失败
            }
            if os.path.exists(COOKIE_FILE):
                ydl_opts["cookiefile"] = COOKIE_FILE
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            # 合并转 mp4 后实际文件可能是 .mp4，做一下纠正
            if not os.path.exists(filename):
                filename = os.path.splitext(filename)[0] + ".mp4"
            title = info.get("title") or "视频"

        if not os.path.exists(filename):
            await video_matcher.send("❌ 下载完成但未找到文件")
            return

        size = os.path.getsize(filename)
        file_uri = "file:///" + os.path.abspath(filename).replace("\\", "/")

        # 超过大小限制：直接改发文件（文件通道比视频消息宽松得多）
        if size > MAX_VIDEO_SIZE:
            await video_matcher.send(
                f"⚠️ 超过 {MAX_VIDEO_SIZE // 1024 // 1024}MB，已改为发送文件（对方需下载查看）"
            )
            await video_matcher.send(MessageSegment("file", {"file": file_uri}))
            return

        try:
            await video_matcher.send(MessageSegment.video(file=file_uri))
        except Exception:
            # 视频消息发送失败时，退化为发送文件
            await video_matcher.send(MessageSegment("file", {"file": file_uri}))
            await video_matcher.send("（视频消息发送失败，已改为发送文件）")

    except Exception as e:
        logger.exception("视频下载或发送失败")
        await video_matcher.send(f"❌ 失败：{e}")
