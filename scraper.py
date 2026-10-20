"""Scrape homework and album data from the class website.

Returns plain dicts (JSON-serializable). No LINE logic here.
"""

import re
from datetime import datetime, timezone, timedelta

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
from bs4 import BeautifulSoup

import config

_TW_TZ = timezone(timedelta(hours=8))


def _fetch(path: str) -> BeautifulSoup:
    """GET a page relative to SITE_BASE_URL and return parsed soup."""
    url = config.SITE_BASE_URL + path
    resp = requests.get(url, verify=False, timeout=config.REQUEST_TIMEOUT)
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "html.parser")


# ── Homework ─────────────────────────────────────────────────────

def get_today_homework(date_str: str | None = None) -> dict | None:
    """Return today's homework dict, or *None* if none exists.

    Parameters
    ----------
    date_str : str, optional
        Date in ``YYYY/M/D`` format.  Defaults to today (UTC+8).

    Returns
    -------
    dict | None
        ``{date, title, content, attachments: [{filename, url}]}``
    """
    if date_str is None:
        now = datetime.now(_TW_TZ)
        date_str = f"{now.year}/{now.month}/{now.day}"

    path = config.HOMEWORK_DETAIL_PATH.format(date=date_str)
    detail_url = config.SITE_BASE_URL + path
    soup = _fetch(path)

    # The homework table uses <th> headers: 標題, 內容, 附檔 N
    table = soup.find("table", class_="news-table")
    if table is None:
        return None

    rows = table.find_all("tr")
    title = ""
    content = ""
    attachments: list[dict] = []

    for row in rows:
        th = row.find("th")
        td = row.find("td")
        if th is None or td is None:
            continue

        header = th.get_text(strip=True)

        if header == "標題":
            title = td.get_text(strip=True)
        elif header == "內容":
            # Preserve <br> as newlines
            content = td.decode_contents().strip()
            # Convert <br> variants to newline, then strip tags
            content = re.sub(r"<br\s*/?>", "\n", content)
            content = re.sub(r"<[^>]+>", "", content).strip()
        elif header.startswith("附檔"):
            link = td.find("a")
            if link and link.get("href"):
                href = link["href"]
                # href is like ../up_files/cld/2310821.jpg
                filename = href.rsplit("/", 1)[-1]
                abs_url = config.SITE_BASE_URL + config.ATTACHMENT_BASE_PATH + filename
                attachments.append({"filename": filename, "url": abs_url})

    # If there's no title at all, the page was empty / no homework
    if not title:
        return None

    return {
        "date": date_str,
        "title": title,
        "content": content,
        "url": detail_url,
        "attachments": attachments,
    }


# ── Albums ───────────────────────────────────────────────────────

_ALBUM_LINK_RE = re.compile(r"pt_all\.asp\?mainid=(\d+)")
_COUNT_RE = re.compile(r"（\s*(\d+)\s*張\s*）")


def get_albums() -> list[dict]:
    """Return every album on the list page.

    Returns
    -------
    list[dict]
        Each dict: ``{mainid: int, title: str, date: str, count: str,
        url: str}``.  *url* is the absolute URL to the album page.
    """
    soup = _fetch(config.ALBUM_LIST_PATH)

    albums: list[dict] = []
    seen_ids: set[int] = set()

    # Each album's metadata lives in a <table width="240"> block containing
    # a <span class="font_small"> with the title link, date, and count.
    for span in soup.find_all("span", class_="font_small"):
        link = span.find("a", href=_ALBUM_LINK_RE)
        if link is None:
            continue

        m = _ALBUM_LINK_RE.search(link["href"])
        if m is None:
            continue

        mainid = int(m.group(1))
        if mainid in seen_ids:
            continue
        seen_ids.add(mainid)

        title = link.get_text(strip=True)

        # The text after the <a> and <br> looks like:
        #   \n                            2026/10/7（<span class="font_red">4</span>張）
        # We grab the full text of the parent span to extract date and count.
        full_text = span.get_text(separator=" ", strip=True)
        # Extract date: YYYY/M/D or YYYY/MM/DD
        date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})", full_text)
        date_str = date_match.group(1) if date_match else ""

        # Extract count
        count_match = _COUNT_RE.search(full_text)
        count_str = count_match.group(1) if count_match else ""

        abs_url = config.SITE_BASE_URL + config.ALBUM_DETAIL_PATH.format(mainid=mainid)

        albums.append({
            "mainid": mainid,
            "title": title,
            "date": date_str,
            "count": count_str,
            "url": abs_url,
        })

    return albums


# ── News ─────────────────────────────────────────────────────────

_NEWS_LINK_RE = re.compile(r"news/show\.asp\?news_id=(\d+)")


def get_news() -> list[dict]:
    """Return every announcement on the news list page.

    Returns
    -------
    list[dict]
        Each dict: ``{news_id: int, title: str, date: str, url: str}``.
        *url* is the absolute URL to the announcement detail page.
    """
    soup = _fetch(config.NEWS_LIST_PATH)

    news: list[dict] = []
    seen_ids: set[int] = set()

    for link in soup.find_all("a", href=_NEWS_LINK_RE):
        m = _NEWS_LINK_RE.search(link["href"])
        if m is None:
            continue

        news_id = int(m.group(1))
        if news_id in seen_ids:
            continue
        seen_ids.add(news_id)

        title = link.get_text(strip=True)

        # Date lives in the sibling <td> of the row (the <a> sits in a
        # <div> inside the first <td>; the date is the next <td>).
        date_str = ""
        row = link.find_parent("tr")
        if row is not None:
            tds = row.find_all("td")
            if len(tds) >= 2:
                date_match = re.search(r"(\d{4}/\d{1,2}/\d{1,2})",
                                       tds[-1].get_text(strip=True))
                if date_match:
                    date_str = date_match.group(1)

        abs_url = config.SITE_BASE_URL + config.NEWS_DETAIL_PATH.format(
            news_id=news_id)

        news.append({
            "news_id": news_id,
            "title": title,
            "date": date_str,
            "url": abs_url,
        })

    return news
