"""LINE Messaging API push helpers using raw requests (no SDK)."""

import json
import os

import requests

_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def _is_dry_run() -> bool:
    return bool(os.environ.get("DRY_RUN"))


def _headers() -> dict:
    token = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def _group_id() -> str:
    """Return the target group id. In dry-run mode, fall back to a placeholder
    so verification works without LINE credentials configured."""
    if _is_dry_run():
        return os.environ.get("LINE_GROUP_ID", "DRY_RUN_GROUP_ID")
    return os.environ["LINE_GROUP_ID"]


def push_text(text: str) -> None:
    """Push a text message to the configured LINE group."""
    group_id = _group_id()
    payload = {
        "to": group_id,
        "messages": [{"type": "text", "text": text}],
    }

    if _is_dry_run():
        print(f"[DRY_RUN] push_text payload: {json.dumps(payload, ensure_ascii=False)}")
        return

    resp = requests.post(_PUSH_URL, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    print(f"[PUSH] text sent ({len(text)} chars)")


def push_image(image_url: str) -> None:
    """Push an image message to the configured LINE group."""
    group_id = _group_id()
    payload = {
        "to": group_id,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ],
    }

    if _is_dry_run():
        print(f"[DRY_RUN] push_image payload: {json.dumps(payload, ensure_ascii=False)}")
        return

    resp = requests.post(_PUSH_URL, headers=_headers(), json=payload, timeout=15)
    resp.raise_for_status()
    print(f"[PUSH] image sent: {image_url}")
