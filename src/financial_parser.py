"""트랙 A: 요약재무제표·임직원현황 파싱 (F4의 절반)."""
from __future__ import annotations

from .models import EmployeeGroup, FinancialSummary

_ACCOUNT_CANDIDATES = {
    "revenue": ["매출액", "수익(매출액)", "영업수익"],
    "operating_profit": ["영업이익(손실)", "영업이익"],
    "net_income": ["당기순이익(손실)", "당기순이익"],
    "total_assets": ["자산총계"],
    "total_liabilities": ["부채총계"],
}


def _to_int(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip().replace(",", "")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        try:
            return int(float(raw))
        except ValueError:
            return None


def _pick_account(rows: list[dict], names: list[str]) -> dict | None:
    for name in names:
        exact = [r for r in rows if r.get("account_nm") == name]
        if exact:
            return exact[0]
    for name in names:
        contains = [r for r in rows if name in (r.get("account_nm") or "")]
        if contains:
            return min(contains, key=lambda r: len(r.get("account_nm") or ""))
    return None


def parse_financial_summary(data: dict, bsns_year: str, reprt_code: str) -> FinancialSummary:
    rows = data.get("list", [])
    # 연결재무제표(CFS) 우선, 없으면 개별(OFS)
    consolidated = [r for r in rows if r.get("fs_div") == "CFS"]
    rows_pref = consolidated or rows

    summary = FinancialSummary(bsns_year=bsns_year, reprt_code=reprt_code)
    for field, candidates in _ACCOUNT_CANDIDATES.items():
        row = _pick_account(rows_pref, candidates)
        setattr(summary, field, _to_int(row.get("thstrm_amount")) if row else None)
    return summary


def parse_employee_status(data: dict) -> list[EmployeeGroup]:
    rows = data.get("list", [])
    groups = []
    for row in rows:
        division = row.get("fo_bbm", "").strip()
        sex = row.get("sexdstn", "").strip()
        label = f"{division} ({sex})" if sex and sex not in division else division
        avg_tenure = row.get("avrg_cnwk_sdytrn", "").strip() if row.get("avrg_cnwk_sdytrn") else None
        try:
            avg_tenure_years = float(avg_tenure) if avg_tenure not in (None, "", "-") else None
        except ValueError:
            avg_tenure_years = None
        headcount = _to_int(row.get("sm"))
        avg_salary = _to_int(row.get("jan_salary_am"))
        if headcount is None and avg_tenure_years is None and avg_salary is None:
            continue  # 해당 보고서에 값이 전부 "-"로 기재된, 실질적으로 데이터 없는 행
        groups.append(
            EmployeeGroup(
                division=label or "전체",
                headcount=headcount,
                avg_tenure_years=avg_tenure_years,
                avg_salary=avg_salary,
            )
        )
    return groups
