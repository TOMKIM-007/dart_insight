# DART 공시 자동 정리 앱 — 기획서 (Claude Code 개발용)

## 0. 문서 목적
이 문서는 Claude Code가 곧바로 개발에 착수할 수 있도록 요구사항, API 명세, 아키텍처, 데이터 모델, 로드맵을 정리한 스펙 문서다. 각 섹션의 API 파라미터·엔드포인트는 실제 개발 전 [OpenDART 개발가이드](https://opendart.fss.or.kr/guide/main.do)에서 필드명을 한 번 더 대조 확인할 것.

---

## 1. 프로젝트 개요

- **목적**: 회사 이름 또는 회사코드를 입력하면 최근 3개월간의 전자공시 자료를 자동 수집하여 날짜별로 정리하고, 그중 정기보고서(사업보고서/분기보고서/반기보고서)는 4개 핵심 섹션(요약재무제표, 사업의 내용, 임직원 현황, 주석내용)을 상세히 요약해서 보여준다.
- **문제의식**: DART 원본 공시는 회사별로 수십~수백 페이지 분량이라 기획/신규사업 담당자가 매번 원문을 뒤져 핵심만 뽑아내는 데 시간이 많이 든다. 이를 자동화해 리서치 시간을 단축한다.
- **사용자**: 사내 기획팀/신규사업 담당자 (1인 또는 소규모 팀 사용 도구, 초기엔 로그인·권한 관리 불필요)
- **사용 형태**: 로컬 실행 웹앱 또는 CLI (Claude Code로 빠르게 프로토타입 → 필요시 배포)

---

## 2. 핵심 기능 요구사항

| # | 기능 | 설명 |
|---|---|---|
| F1 | 회사 검색 | 회사명 또는 종목코드 입력 → DART 고유번호(corp_code)로 매핑 |
| F2 | 공시 리스트 조회 | 최근 3개월(기본값, 조정 가능) 공시를 날짜별로 정렬해 타임라인으로 표시 |
| F3 | 정기보고서 자동 판별 | 리스트 중 사업보고서/분기보고서/반기보고서를 별도 표시(뱃지 등) |
| F4 | 정기보고서 상세 요약 | 클릭 시 4개 섹션(요약재무제표/사업의 내용/임직원 현황/주석내용) 상세 화면 |
| F5 | 캐싱 | 동일 회사·기간 재조회 시 API 재호출 최소화(로컬 캐시) |

**F1~F3은 순수 API 조합, F4는 AI 요약이 필요한 핵심 기능**이라는 점을 개발 우선순위에 반영한다.

---

## 3. 시스템 아키텍처

데이터는 두 갈래로 처리된다. OpenDART가 이미 구조화된 JSON으로 주는 데이터(트랙 A)와, 원본 문서를 통째로 받아 AI가 파싱·요약해야 하는 데이터(트랙 B)로 나뉜다. 이 구분이 이 앱 설계의 핵심이다.

```
[회사 입력] → [공시검색 API] → [정기보고서 판별]
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                        ▼
         [트랙 A: 구조화 API]                        [트랙 B: 원본문서 API]
         재무제표 주요계정 API                         공시서류원본파일 API
         직원현황 API                                  (document.xml)
                    │                                        │
              필드 그대로 매핑                        Claude API로 섹션 추출·요약
                    │                                        │
                    └───────────────────┬───────────────────┘
                                         ▼
                              [날짜별·섹션별 통합 리포트]
```

- **트랙 A**: API 응답 JSON을 그대로 파싱해 화면에 매핑. 별도 AI 처리 불필요.
- **트랙 B**: `document.xml`로 원본(zip 내 XML/HTML)을 받아 텍스트를 추출한 뒤, Claude API에 "이 문서에서 사업의 내용/주석 부분만 찾아 요약해줘" 형태로 요청. 문서가 길면 청킹(분할) 후 순차 처리.

---

## 4. OpenDART API 명세

Base URL: `https://opendart.fss.or.kr/api/`
공통 파라미터: `crtfc_key` (발급받은 인증키)

| API명 | 엔드포인트 | 주요 파라미터 | 용도 | 응답형식 |
|---|---|---|---|---|
| 고유번호 | `corpCode.xml` | crtfc_key | 전체 회사의 corp_code/회사명/종목코드 매핑 zip 다운로드 (최초 1회 캐싱해서 로컬에서 검색) | ZIP(XML) |
| 기업개황 | `company.json` | crtfc_key, corp_code | 회사 기본정보 | JSON |
| 공시검색 | `list.json` | crtfc_key, corp_code, bgn_de, end_de, pblntf_ty(A=정기공시), page_no, page_count | 공시 리스트 조회 | JSON |
| 공시서류원본파일 | `document.xml` | crtfc_key, rcept_no(접수번호) | 공시 원문 전체 다운로드 | ZIP(XML/HTML) |
| 단일회사 주요계정 | `fnlttSinglAcnt.json` | crtfc_key, corp_code, bsns_year, reprt_code | 요약재무제표(주요 재무상태표/손익계산서 계정) | JSON |
| 단일회사 전체 재무제표 | `fnlttSinglAcntAll.json` | crtfc_key, corp_code, bsns_year, reprt_code, fs_div(OFS/CFS) | 재무제표 전체 계정 (필요시 주석 관련 계정 보강용) | JSON |
| 직원현황 | `empSttus.json` | crtfc_key, corp_code, bsns_year, reprt_code | 임직원 현황(부문별 인원, 평균근속연수, 급여 등) | JSON |
| 임원현황 | `exctvSttus.json` | crtfc_key, corp_code, bsns_year, reprt_code | 임원 현황 | JSON |

**reprt_code 값**: `11013`=1분기보고서, `11012`=반기보고서, `11014`=3분기보고서, `11011`=사업보고서(사업연도)

> ⚠️ 정확한 필드명(response schema)은 API마다 다르므로, 각 API 구현 시 [개발가이드 상세페이지](https://opendart.fss.or.kr/guide/main.do)에서 응답 필드를 한 번 더 확인 후 파서를 작성할 것.

---

## 5. 처리 로직 상세

### 5.1 회사 식별 (F1)
1. `corpCode.xml`을 최초 1회 다운로드해 로컬 파일(JSON/SQLite)로 캐싱
2. 사용자가 입력한 회사명/종목코드를 로컬 캐시에서 검색해 corp_code 확정
3. 매칭 실패 시 유사 이름 후보 리스트 제시

### 5.2 공시 리스트 조회 (F2)
1. `list.json` 호출: `bgn_de` = 오늘 - 3개월, `end_de` = 오늘
2. 응답을 접수일자(`rcept_dt`) 기준 내림차순 정렬해 타임라인으로 렌더링
3. 보고서명(`report_nm`)에 "사업보고서"/"분기보고서"/"반기보고서" 포함 여부로 정기보고서 여부 1차 판별 (`pblntf_ty=A` 필터와 병행)

### 5.3 정기보고서 상세 처리 (F4)
- **요약재무제표**: `fnlttSinglAcnt.json` 호출 → 매출액/영업이익/당기순이익/자산총계/부채총계 등 주요 계정만 추려 표로 표시
- **임직원 현황**: `empSttus.json` 호출 → 부문별/성별 인원, 평균근속연수, 1인평균급여 표로 표시
- **사업의 내용**: `document.xml`로 원문 확보 → 텍스트에서 "사업의 내용" 챕터 범위를 대략 절단(챕터 제목 패턴 매칭) → Claude API로 "다음 텍스트에서 회사의 주요 사업, 시장 현황, 경쟁 상황을 5~10문장으로 요약해줘" 프롬프트 실행
- **주석내용**: 동일 원문에서 재무제표 주석 섹션을 절단 → 분량이 크므로 우발부채/특수관계자거래/차입금 및 담보/소송 등 핵심 항목 위주로 청킹 후 Claude API 요약

### 5.4 AI 요약 프롬프트 설계 원칙
- 원문 텍스트를 그대로 붙여넣지 말고, 섹션 단위로 잘라 컨텍스트를 줄인다.
- "요약"이 아니라 "다음 항목별로 정리"처럼 출력 스키마를 지정하면 후처리가 쉬워진다 (예: JSON 형태로 반환 요청).
- 원문에 없는 내용을 추정하지 않도록 "문서에 명시된 내용만 사용" 지시를 프롬프트에 포함한다.

---

## 6. 출력 데이터 모델 (예시)

```json
{
  "corp_name": "회사명",
  "corp_code": "00126380",
  "period": { "start": "2026-04-14", "end": "2026-07-14" },
  "disclosures": [
    {
      "rcept_no": "20260514000123",
      "rcept_dt": "2026-05-14",
      "report_nm": "분기보고서 (2026.03)",
      "is_periodic": true,
      "report_type": "분기보고서",
      "detail": {
        "financial_summary": { "revenue": 0, "operating_profit": 0, "net_income": 0, "total_assets": 0, "total_liabilities": 0 },
        "business_overview": "AI 요약 텍스트",
        "employee_status": [ { "division": "영업", "headcount": 0, "avg_tenure_years": 0, "avg_salary": 0 } ],
        "notes_summary": "AI 요약 텍스트"
      }
    }
  ]
}
```

---

## 7. 화면 설계 (초안)

- **메인 화면**: 회사 검색창 + 최근 3개월 공시 타임라인(날짜순 카드/리스트). 정기보고서는 뱃지로 구분.
- **상세 화면**: 탭 4개(요약재무제표 / 사업의 내용 / 임직원 현황 / 주석내용). 원문 링크(DART 원본 페이지)도 함께 노출.

---

## 8. 기술 스택 제안

- **언어/런타임**: Python 3.11+
- **API 호출**: `requests`
- **데이터 처리**: `pandas`
- **AI 요약**: Anthropic Claude API (`anthropic` SDK)
- **프론트엔드**: 1차 프로토타입은 Streamlit, 이후 정식 서비스 전환 시 React
- **저장소**: 초기엔 별도 DB 없이 실시간 호출 + 로컬 JSON/SQLite 캐시

---

## 9. 프로젝트 폴더 구조 제안

```
dart-disclosure-app/
├── .env                      # DART_API_KEY, ANTHROPIC_API_KEY
├── README.md
├── requirements.txt
├── src/
│   ├── dart_client.py        # OpenDART API 호출 래퍼
│   ├── corp_lookup.py        # corp_code 캐싱·검색
│   ├── disclosure_service.py # 리스트 조회·정기보고서 판별
│   ├── financial_parser.py   # 트랙 A: 재무제표/임직원현황 파싱
│   ├── document_extractor.py # 트랙 B: 원본문서 다운로드·텍스트 추출
│   ├── ai_summarizer.py      # Claude API 요약 로직
│   └── models.py             # 출력 데이터 모델(dataclass/pydantic)
├── app.py                    # Streamlit 엔트리포인트
└── cache/
    └── corp_code.json
```

---

## 10. 개발 로드맵

### Phase 1 — MVP (트랙 A만)
- [ ] `.env`에 DART_API_KEY 설정 및 연결 테스트
- [ ] corp_code 캐싱 및 회사 검색 (F1)
- [ ] 최근 3개월 공시 리스트 조회·날짜별 정렬 (F2)
- [ ] 정기보고서 뱃지 표시 (F3)
- [ ] 요약재무제표·임직원현황 표 렌더링 (F4의 절반)
- [ ] Streamlit 기본 화면

### Phase 2 — AI 트랙 추가
- [ ] `document.xml` 원문 다운로드·텍스트 추출
- [ ] "사업의 내용" 섹션 절단 로직 + Claude 요약 연동
- [ ] "주석내용" 청킹 + Claude 요약 연동
- [ ] 로컬 캐시(재조회 비용 절감)

### Phase 3 — 확장
- [ ] 여러 회사 비교 뷰
- [ ] 신규 공시 알림
- [ ] 리포트 PDF/문서 내보내기

---

## 11. 환경설정

```
# .env
DART_API_KEY=발급받은_인증키
ANTHROPIC_API_KEY=클로드_API_키
```

- API 키는 코드에 하드코딩하지 않고 `.env`로 관리, `.gitignore`에 반드시 포함.

---

## 12. 리스크 및 고려사항

- **"최근 3개월"에 정기보고서가 없을 수 있음**: 사업보고서 연 1회, 반기보고서 1회, 분기보고서 연 2회만 제출됨. Phase 1에서 "가장 최근 정기보고서 자동 조회" 옵션도 함께 고려.
- **원문 서식 편차**: 회사·업종마다 "사업의 내용" 챕터 구조가 달라 정규식만으로는 불안정 → AI 파싱에 의존하는 설계가 현실적.
- **주석 분량**: 재무제표 주석은 수십 페이지가 흔함 → 통짜 요약보다 핵심 항목 위주 청킹 필요, 토큰 비용 고려.
- **API 호출 한도**: OpenDART는 계정별 일일 호출 한도가 있으므로 개발 중 확인하고 캐싱으로 절감.
- **비상장/금융업 회사**: 일부 API(재무정보 등)는 상장법인·IFRS 적용 대상 위주로 제공되므로 예외 처리 필요.

---

## 13. MVP 완료 기준 (Definition of Done)

- 회사명 또는 종목코드 입력 시 최근 3개월 공시가 날짜순으로 화면에 표시된다.
- 정기보고서는 목록에서 시각적으로 구분된다.
- 정기보고서 클릭 시 요약재무제표·임직원 현황이 표로 표시된다.
- (Phase 2 완료 시) 사업의 내용·주석내용이 AI 요약문으로 표시된다.
- API 키는 `.env`로 분리되어 있고 저장소에 노출되지 않는다.
