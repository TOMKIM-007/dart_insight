"""DART 공시 자동 정리 앱 - Streamlit 엔트리포인트 (Phase 1 MVP)."""
from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.corp_lookup import load_corps, search_corp
from src.dart_client import DartApiError, DartClient
from src.disclosure_service import fetch_latest_periodic_report, fetch_recent_disclosures
from src.financial_parser import parse_employee_status, parse_financial_summary
from src.models import Corp, Disclosure

load_dotenv()

st.set_page_config(page_title="DART 공시 자동 정리", page_icon="📄", layout="wide")


def _get_api_key() -> str | None:
    """로컬(.env)과 Streamlit Cloud(secrets.toml) 양쪽을 지원."""
    api_key = os.getenv("DART_API_KEY")
    if api_key:
        return api_key
    try:
        return st.secrets.get("DART_API_KEY")
    except Exception:
        return None


@st.cache_resource
def get_client() -> DartClient | None:
    api_key = _get_api_key()
    if not api_key:
        return None
    return DartClient(api_key)


@st.cache_data(ttl=24 * 60 * 60, show_spinner="회사 목록을 불러오는 중...")
def cached_corps() -> list[Corp]:
    client = get_client()
    return load_corps(client)


@st.cache_data(ttl=60 * 60, show_spinner="최근 공시를 조회하는 중...")
def cached_disclosures(corp_code: str, months: int) -> list[Disclosure]:
    client = get_client()
    return fetch_recent_disclosures(client, corp_code, months=months)


@st.cache_data(ttl=60 * 60, show_spinner="재무 정보를 조회하는 중...")
def cached_financial_summary(corp_code: str, bsns_year: str, reprt_code: str):
    client = get_client()
    data = client.get_financial_summary(corp_code, bsns_year, reprt_code)
    return parse_financial_summary(data, bsns_year, reprt_code)


@st.cache_data(ttl=60 * 60, show_spinner="임직원 현황을 조회하는 중...")
def cached_employee_status(corp_code: str, bsns_year: str, reprt_code: str):
    client = get_client()
    data = client.get_employee_status(corp_code, bsns_year, reprt_code)
    return parse_employee_status(data)


def format_number(n: int | None) -> str:
    return f"{n:,}" if n is not None else "-"


def render_detail(corp: Corp, disclosure: Disclosure) -> None:
    st.subheader(disclosure.report_nm)
    st.caption(f"접수일자 {disclosure.rcept_dt} · [DART 원문 보기]({disclosure.dart_url})")

    if not disclosure.reprt_code or not disclosure.bsns_year:
        st.warning("보고서 기간 정보를 해석하지 못해 상세 조회를 할 수 없습니다.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["요약재무제표", "사업의 내용", "임직원 현황", "주석내용"])

    with tab1:
        try:
            summary = cached_financial_summary(corp.corp_code, disclosure.bsns_year, disclosure.reprt_code)
            rows = [
                ("매출액", format_number(summary.revenue)),
                ("영업이익", format_number(summary.operating_profit)),
                ("당기순이익", format_number(summary.net_income)),
                ("자산총계", format_number(summary.total_assets)),
                ("부채총계", format_number(summary.total_liabilities)),
            ]
            st.table({"항목": [r[0] for r in rows], "금액(원)": [r[1] for r in rows]})
        except DartApiError as e:
            st.error(f"요약재무제표 조회 실패: {e}")

    with tab2:
        st.info("사업의 내용 AI 요약은 Phase 2에서 제공될 예정입니다.")

    with tab3:
        try:
            groups = cached_employee_status(corp.corp_code, disclosure.bsns_year, disclosure.reprt_code)
            if groups:
                st.dataframe(
                    [
                        {
                            "부문": g.division,
                            "인원": g.headcount,
                            "평균근속연수": g.avg_tenure_years,
                            "1인평균급여(원)": format_number(g.avg_salary),
                        }
                        for g in groups
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("임직원 현황 데이터가 없습니다.")
        except DartApiError as e:
            st.error(f"임직원 현황 조회 실패: {e}")

    with tab4:
        st.info("주석내용 AI 요약은 Phase 2에서 제공될 예정입니다.")


def main() -> None:
    st.title("📄 DART 공시 자동 정리")
    st.caption("회사명 또는 종목코드를 입력하면 최근 공시를 날짜별로 정리하고, 정기보고서는 핵심 재무·인력 정보를 표로 보여줍니다.")

    client = get_client()
    if client is None:
        st.error("DART_API_KEY가 설정되지 않았습니다. `.env` 파일에 DART_API_KEY를 입력한 뒤 앱을 다시 시작하세요.")
        st.stop()

    with st.sidebar:
        st.header("검색")
        query = st.text_input("회사명 또는 종목코드", placeholder="예: 삼성전자 또는 005930")
        months = st.slider("조회 기간(개월)", min_value=1, max_value=12, value=3)

    if not query:
        st.info("왼쪽에서 회사명 또는 종목코드를 입력하고 검색하세요.")
        return

    try:
        corps = cached_corps()
    except DartApiError as e:
        st.error(f"회사 목록 로딩 실패: {e}")
        st.stop()
        return

    matches = search_corp(corps, query, limit=10)
    if not matches:
        st.warning(f"'{query}'와 일치하는 회사를 찾지 못했습니다.")
        return

    if len(matches) == 1:
        corp = matches[0]
    else:
        options = {f"{c.corp_name} ({c.stock_code or '비상장'})": c for c in matches}
        selected_label = st.selectbox("검색 결과가 여러 건입니다. 회사를 선택하세요.", list(options.keys()))
        corp = options[selected_label]

    st.markdown(f"### {corp.corp_name} `{corp.corp_code}`")

    try:
        disclosures = cached_disclosures(corp.corp_code, months)
    except DartApiError as e:
        st.error(f"공시 리스트 조회 실패: {e}")
        return

    if not disclosures:
        st.warning(f"최근 {months}개월간 공시가 없습니다.")
        if st.button("가장 최근 정기보고서 찾기 (최대 15개월 전까지)"):
            try:
                latest = fetch_latest_periodic_report(client, corp.corp_code)
            except DartApiError as e:
                st.error(f"조회 실패: {e}")
                latest = None
            if latest:
                st.session_state["selected_rcept_no"] = latest.rcept_no
                render_detail(corp, latest)
            else:
                st.warning("최근 15개월 내 정기보고서를 찾지 못했습니다.")
        return

    st.markdown(f"최근 {months}개월간 공시 **{len(disclosures)}건**")

    for d in disclosures:
        badge = f"🟦 정기보고서({d.report_type})" if d.is_periodic else ""
        cols = st.columns([2, 6, 2])
        cols[0].write(d.rcept_dt)
        cols[1].write(d.report_nm)
        cols[2].write(badge)
        if d.is_periodic:
            if st.button("상세 보기", key=f"detail_{d.rcept_no}"):
                st.session_state["selected_rcept_no"] = d.rcept_no

    selected_rcept_no = st.session_state.get("selected_rcept_no")
    if selected_rcept_no:
        selected = next((d for d in disclosures if d.rcept_no == selected_rcept_no), None)
        if selected:
            st.divider()
            render_detail(corp, selected)


if __name__ == "__main__":
    main()
