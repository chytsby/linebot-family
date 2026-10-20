"""Orchestrator: scrape → diff → download → push LINE → update state."""

import json
import os
from pathlib import Path

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests

import config
from scraper import get_albums, get_news, get_today_homework
from notifier import push_text, push_image

_PROJECT_DIR = Path(__file__).resolve().parent
_STATE_PATH = _PROJECT_DIR / "state.json"
_IMAGES_DIR = _PROJECT_DIR / "images"


def _load_state() -> dict:
    if _STATE_PATH.exists():
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    return {"last_album_mainid": 0, "last_news_id": 0, "last_homework_date": None}


def _save_state(state: dict) -> None:
    _STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[STATE] written: {state}")


def _download_image(url: str, filename: str) -> Path:
    """Download an image to images/<filename>. Skip if already exists."""
    _IMAGES_DIR.mkdir(exist_ok=True)
    dest = _IMAGES_DIR / filename
    if dest.exists():
        print(f"[SKIP] image already exists: {filename}")
        return dest

    resp = requests.get(url, verify=False, timeout=config.REQUEST_TIMEOUT)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"[DOWNLOAD] {filename} ({len(resp.content)} bytes)")
    return dest


def _handle_albums(state: dict) -> None:
    """Check for new albums and push notifications."""
    albums = get_albums()
    last_id = state["last_album_mainid"]
    new_albums = sorted(
        [a for a in albums if a["mainid"] > last_id],
        key=lambda a: a["mainid"],
    )

    if not new_albums:
        print(f"[ALBUMS] no new albums (last_mainid={last_id})")
        return

    for album in new_albums:
        msg = (
            f"📷 新相簿：{album['title']}\n"
            f"日期：{album['date']}｜{album['count']} 張\n"
            f"{album['url']}"
        )
        print(f"[ALBUMS] new: mainid={album['mainid']} {album['title']}")
        push_text(msg)

    state["last_album_mainid"] = max(a["mainid"] for a in new_albums)


def _handle_news(state: dict) -> None:
    """Check for new announcements and push title + link."""
    news = get_news()
    last_id = state.get("last_news_id", 0)
    new_items = sorted(
        [n for n in news if n["news_id"] > last_id],
        key=lambda n: n["news_id"],
    )

    if not new_items:
        print(f"[NEWS] no new announcements (last_news_id={last_id})")
        return

    for item in new_items:
        msg = (
            f"📢 新公告：{item['title']}\n"
            f"日期：{item['date']}\n"
            f"{item['url']}"
        )
        print(f"[NEWS] new: news_id={item['news_id']} {item['title']}")
        push_text(msg)

    state["last_news_id"] = max(n["news_id"] for n in new_items)


def _handle_homework(state: dict) -> None:
    """Check today's homework and push notification + images."""
    hw = get_today_homework()
    if hw is None:
        print("[HOMEWORK] no homework today")
        return

    today_str = hw["date"]
    if today_str == state["last_homework_date"]:
        print(f"[SKIP] homework already pushed for {today_str}")
        return

    # Push text summary
    msg = f"📝 今日作業 ({today_str})\n標題：{hw['title']}\n{hw['content']}\n\n🔗 {hw['url']}"
    print(f"[HOMEWORK] pushing for {today_str}: {hw['title']}")
    push_text(msg)

    # Push attachment images
    raw_base = config.RAW_BASE_URL
    for att in hw["attachments"]:
        filename = att["filename"]
        _download_image(att["url"], filename)

        if raw_base:
            public_url = raw_base + filename
            push_image(public_url)
        else:
            print(f"[SKIP] RAW_BASE_URL not set, skipping image push for {filename}")

    state["last_homework_date"] = today_str


def main() -> None:
    dry = os.environ.get("DRY_RUN")
    if dry:
        print("[DRY_RUN] mode enabled — no LINE API calls will be made")

    state = _load_state()
    print(f"[STATE] loaded: {state}")

    _handle_albums(state)
    _handle_news(state)
    _handle_homework(state)

    _save_state(state)


if __name__ == "__main__":
    main()
