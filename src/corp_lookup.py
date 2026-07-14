"""corp_code 캐싱 및 회사명/종목코드 검색 (F1)."""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from .dart_client import DartClient
from .models import Corp

CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "corp_code.json"
CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 7일


def _parse_corp_code_xml(xml_bytes: bytes) -> list[Corp]:
    root = ET.fromstring(xml_bytes)
    corps = []
    for item in root.findall("list"):
        stock_code = (item.findtext("stock_code") or "").strip()
        corps.append(
            Corp(
                corp_code=(item.findtext("corp_code") or "").strip(),
                corp_name=(item.findtext("corp_name") or "").strip(),
                stock_code=stock_code,
                modify_date=(item.findtext("modify_date") or "").strip(),
            )
        )
    return corps


def _load_cache() -> list[Corp] | None:
    if not CACHE_PATH.exists():
        return None
    if time.time() - CACHE_PATH.stat().st_mtime > CACHE_MAX_AGE_SECONDS:
        return None
    raw = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return [Corp(**item) for item in raw]


def _save_cache(corps: list[Corp]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps([c.__dict__ for c in corps], ensure_ascii=False),
        encoding="utf-8",
    )


def load_corps(client: DartClient, force_refresh: bool = False) -> list[Corp]:
    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            return cached
    xml_bytes = client.fetch_corp_code_xml()
    corps = _parse_corp_code_xml(xml_bytes)
    _save_cache(corps)
    return corps


def search_corp(corps: list[Corp], query: str, limit: int = 10) -> list[Corp]:
    """회사명 또는 종목코드로 검색. 정확도 순으로 정렬해 반환."""
    query = query.strip()
    if not query:
        return []

    if re.fullmatch(r"\d{6}", query):
        matches = [c for c in corps if c.stock_code == query]
        return matches[:limit]

    listed = [c for c in corps if c.stock_code]
    unlisted = [c for c in corps if not c.stock_code]

    def rank(c: Corp) -> tuple:
        name = c.corp_name
        if name == query:
            return (0, name)
        if name.startswith(query):
            return (1, name)
        if query in name:
            return (2, name)
        return (9, name)

    candidates = [c for c in listed + unlisted if rank(c)[0] < 9]
    candidates.sort(key=rank)
    return candidates[:limit]
