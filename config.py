"""Centralized configuration for linebot-family scraper and notifier."""

import os

# ── Site parameters ──────────────────────────────────────────────
SITE_BASE_URL = "http://class.baps.tp.edu.tw/ver2/474/"
CLASS_CODE = "474"

# Page paths (relative to SITE_BASE_URL)
CALENDAR_PATH = "cld/Default.asp"
HOMEWORK_DETAIL_PATH = "cld/show.asp?EventDate={date}"  # date = YYYY/M/D
ALBUM_LIST_PATH = "pa/Default.asp"
ALBUM_DETAIL_PATH = "pa/pt_all.asp?mainid={mainid}"
NEWS_LIST_PATH = "main/Default.asp"
NEWS_DETAIL_PATH = "news/show.asp?news_id={news_id}&news_item=1"

# Attachment files live under this prefix
ATTACHMENT_BASE_PATH = "up_files/cld/"

# ── Request settings ─────────────────────────────────────────────
REQUEST_TIMEOUT = 15  # seconds

# ── Public image hosting ─────────────────────────────────────────
# The public GitHub raw URL base for serving images to LINE.
# Set via environment variable; empty string when not configured.
RAW_BASE_URL = os.environ.get("RAW_BASE_URL", "")
