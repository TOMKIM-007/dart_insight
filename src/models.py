"""출력 데이터 모델 정의 (스펙 6장 참고)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Corp:
    corp_code: str
    corp_name: str
    stock_code: str
    modify_date: str = ""


@dataclass
class FinancialSummary:
    revenue: int | None = None
    operating_profit: int | None = None
    net_income: int | None = None
    total_assets: int | None = None
    total_liabilities: int | None = None
    bsns_year: str = ""
    reprt_code: str = ""


@dataclass
class EmployeeGroup:
    division: str
    headcount: int | None = None
    avg_tenure_years: float | None = None
    avg_salary: int | None = None


@dataclass
class DisclosureDetail:
    financial_summary: FinancialSummary | None = None
    employee_status: list[EmployeeGroup] = field(default_factory=list)
    business_overview: str | None = None
    notes_summary: str | None = None


@dataclass
class Disclosure:
    rcept_no: str
    rcept_dt: str
    report_nm: str
    corp_name: str = ""
    is_periodic: bool = False
    report_type: str | None = None
    reprt_code: str | None = None
    bsns_year: str | None = None
    detail: DisclosureDetail | None = None

    @property
    def dart_url(self) -> str:
        return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={self.rcept_no}"
