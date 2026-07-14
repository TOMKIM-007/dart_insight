# DART 공시 자동 정리 (Phase 1 MVP)

회사명 또는 종목코드를 입력하면 최근 공시를 날짜별로 정리하고, 정기보고서(사업/분기/반기보고서)는
요약재무제표·임직원 현황을 표로 보여주는 로컬 Streamlit 앱입니다.

Phase 1 범위이며, "사업의 내용"·"주석내용" AI 요약(Phase 2)은 아직 구현되어 있지 않습니다.

## 실행 방법

```bash
python -m venv .venv
.venv/Scripts/activate       # Windows
pip install -r requirements.txt

cp .env.example .env
# .env에 DART_API_KEY 입력 (https://opendart.fss.or.kr 에서 발급)

streamlit run app.py
```

## 사용법

1. 왼쪽 사이드바에 회사명(예: 삼성전자) 또는 종목코드(예: 005930)를 입력
2. 검색 결과가 여러 건이면 목록에서 회사 선택
3. 최근 N개월(기본 3개월) 공시가 날짜별로 표시되고, 정기보고서는 🟦 뱃지로 구분
4. 정기보고서의 "상세 보기"를 누르면 요약재무제표·임직원 현황 표가 표시됨
5. 최근 조회 기간 내 정기보고서가 없으면 "가장 최근 정기보고서 찾기" 버튼으로 최대 15개월 전까지 탐색 가능

## 폴더 구조

```
src/
├── dart_client.py        # OpenDART API 호출 래퍼
├── corp_lookup.py         # corp_code 캐싱·검색 (F1)
├── disclosure_service.py  # 공시 리스트 조회·정기보고서 판별 (F2, F3)
├── financial_parser.py    # 요약재무제표·임직원현황 파싱 (F4 트랙 A)
└── models.py               # 데이터 모델
app.py                      # Streamlit 엔트리포인트
cache/corp_code.json        # corp_code 매핑 캐시(최초 실행 시 자동 생성, 7일 캐시)
```

## 참고

- 캐싱: 회사 목록은 로컬 파일(`cache/corp_code.json`, 7일)과 Streamlit 세션 캐시를 함께 사용합니다.
  공시 리스트·재무·임직원 조회는 Streamlit 캐시(1시간)로 재호출을 줄입니다.
- OpenDART가 `013`(조회된 데이터가 없습니다) 상태를 반환하면 에러가 아닌 빈 결과로 처리합니다.
- 일부 분기보고서는 임직원 현황을 상세히 기재하지 않아("-" 로만 표기) 데이터가 없을 수 있습니다.
  이 경우 사업보고서(연 1회)를 조회하면 상세 데이터를 확인할 수 있습니다.
