"""최근 공시 리스트 조회·정렬·정기보고서 판별 (F2, F3)."""
from __future__ import annotations

import re
from datetime import date

from .dart_client import DartClient
from .models import Disclosure

PERIODIC_REPORT_TYPES = ["사업보고서", "분기보고서", "반기보고서"]

# report_nm에 표기되는 결산월(MM) -> reprt_code 매핑
_MONTH_TO_REPRT_CODE = {
    "03": "11013",  # 1분기보고서
    "06": "11012",  # 반기보고서
    "09": "11014",  # 3분기보고서
    "12": "11011",  # 사업보고서(사업연도)
}

_PERIOD_PATTERN = re.compile(r"\((\d{4})\.(\d{2})\)")


def months_ago(base: date, months: int) -> date:
    month_index = base.month - 1 - months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, 28)  # 말일 경계 문제 회피
    return date(year, month, day)


def default_period(months: int = 3) -> tuple[str, str]:
    end = date.today()
    start = months_ago(end, months)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _classify(report_nm: str) -> tuple[bool, str | None, str | None, str | None]:
    """반환: (is_periodic, report_type, reprt_code, bsns_year)"""
    report_type = next((t for t in PERIODIC_REPORT_TYPES if t in report_nm), None)
    if report_type is None:
        return False, None, None, None

    m = _PERIOD_PATTERN.search(report_nm)
    if not m:
        return True, report_type, None, None

    year, month = m.group(1), m.group(2)
    reprt_code = _MONTH_TO_REPRT_CODE.get(month)
    # 사업보고서(12월 결산)는 해당 연도가 그대로 사업연도
    bsns_year = year
    return True, report_type, reprt_code, bsns_year


def fetch_recent_disclosures(
    client: DartClient,
    corp_code: str,
    months: int = 3,
    pblntf_ty: str | None = None,
) -> list[Disclosure]:
    bgn_de, end_de = default_period(months)
    disclosures: list[Disclosure] = []
    page_no = 1
    while True:
        data = client.get_disclosure_list(
            corp_code, bgn_de, end_de, pblntf_ty=pblntf_ty, page_no=page_no, page_count=100
        )
        items = data.get("list", [])
        for item in items:
            report_nm = item.get("report_nm", "")
            is_periodic, report_type, reprt_code, bsns_year = _classify(report_nm)
            disclosures.append(
                Disclosure(
                    rcept_no=item.get("rcept_no", ""),
                    rcept_dt=item.get("rcept_dt", ""),
                    report_nm=report_nm,
                    corp_name=item.get("corp_name", ""),
                    is_periodic=is_periodic,
                    report_type=report_type,
                    reprt_code=reprt_code,
                    bsns_year=bsns_year,
                )
            )
        total_page = data.get("total_page", 1) or 1
        if page_no >= total_page:
            break
        page_no += 1

    disclosures.sort(key=lambda d: d.rcept_dt, reverse=True)
    return disclosures


def fetch_latest_periodic_report(client: DartClient, corp_code: str) -> Disclosure | None:
    """최근 3개월 내 정기보고서가 없을 때를 대비해 최근 15개월까지 넓혀 탐색."""
    disclosures = fetch_recent_disclosures(client, corp_code, months=15, pblntf_ty="A")
    periodic = [d for d in disclosures if d.is_periodic]
    return periodic[0] if periodic else None
