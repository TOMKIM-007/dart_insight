"""OpenDART API 호출 래퍼.

필드명은 OpenDART 개발가이드(https://opendart.fss.or.kr/guide/main.do)를 참고해
구현 시점에 확인한 값이다. API 사양이 바뀌면 이 파일만 수정하면 된다.
"""
from __future__ import annotations

import io
import zipfile

import requests

BASE_URL = "https://opendart.fss.or.kr/api/"


class DartApiError(RuntimeError):
    """OpenDART가 status != '000' 을 반환했을 때 발생."""


class DartClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("DART_API_KEY가 설정되지 않았습니다.")
        self.api_key = api_key
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict) -> requests.Response:
        params = {"crtfc_key": self.api_key, **params}
        resp = self.session.get(f"{BASE_URL}{endpoint}", params=params, timeout=30)
        resp.raise_for_status()
        return resp

    def _get_json(self, endpoint: str, params: dict) -> dict:
        data = self._get(endpoint, params).json()
        status = data.get("status")
        if status == "013":
            # 조회된 데이터가 없습니다 - 정상적인 "결과 없음" 상황
            return {**data, "list": []}
        if status != "000":
            raise DartApiError(f"{endpoint} 실패 [{status}]: {data.get('message')}")
        return data

    def fetch_corp_code_xml(self) -> bytes:
        """전체 회사 corp_code 매핑 zip을 받아 내부 XML 바이트를 반환."""
        resp = self._get("corpCode.xml", {})
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            name = zf.namelist()[0]
            return zf.read(name)

    def get_company(self, corp_code: str) -> dict:
        return self._get_json("company.json", {"corp_code": corp_code})

    def get_disclosure_list(
        self,
        corp_code: str,
        bgn_de: str,
        end_de: str,
        pblntf_ty: str | None = None,
        page_no: int = 1,
        page_count: int = 100,
    ) -> dict:
        params = {
            "corp_code": corp_code,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "page_no": page_no,
            "page_count": page_count,
        }
        if pblntf_ty:
            params["pblntf_ty"] = pblntf_ty
        return self._get_json("list.json", params)

    def get_financial_summary(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict:
        return self._get_json(
            "fnlttSinglAcnt.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )

    def get_employee_status(self, corp_code: str, bsns_year: str, reprt_code: str) -> dict:
        return self._get_json(
            "empSttus.json",
            {"corp_code": corp_code, "bsns_year": bsns_year, "reprt_code": reprt_code},
        )
