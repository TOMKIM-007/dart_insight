# imagegen — Gemini 이미지 생성 CLI

Antigravity 에이전트가 내부에서 쓰는 것과 같은 Google 이미지 모델(Nano Banana 계열)을
**Gemini API로 직접** 호출하는 명령줄 도구입니다. Antigravity를 켜 둘 필요가 없습니다.

> 왜 Antigravity CLI를 직접 쓰지 않나요?
> `antigravity-ide` 명령은 에디터 런처일 뿐이고, 에이전트 명령(`agentapi`)은
> 실행 중인 Antigravity 세션 안에서만 동작합니다(`ANTIGRAVITY_LS_ADDRESS is not set`).

## 1. API 키 발급

1. https://aistudio.google.com/apikey 에서 키 발급
2. 저장소 루트의 `.env` 파일에 추가:
   ```
   GEMINI_API_KEY=발급받은키
   ```

**주의:** Gemini 앱 구독(Google AI Pro/Ultra)과 Gemini API 과금은 별개입니다.
이미지 모델은 무료 등급 한도가 낮아 429(쿼터 초과)가 날 수 있으니,
AI Studio에서 키가 속한 프로젝트에 결제(billing)를 연결하세요.

## 2. 설치

```bash
python -m venv .venv
.venv\Scripts\pip install -r imagegen/requirements.txt
```

## 3. 사용법

```bash
# 기본 생성
.venv\Scripts\python imagegen/generate.py "수채화 스타일의 숲 속 여우"

# 비율 지정 + 여러 장
.venv\Scripts\python imagegen/generate.py "미니멀한 제품 사진, 흰 배경" --aspect 16:9 -n 3

# 기존 이미지 편집 (여러 장 합성도 가능: -i a.png -i b.png)
.venv\Scripts\python imagegen/generate.py "밤 풍경으로 바꿔줘" -i imagegen/output/여우.png

# 사용 가능한 이미지 모델 확인 / 다른 모델 사용
.venv\Scripts\python imagegen/generate.py --list-models
.venv\Scripts\python imagegen/generate.py "포스터" -m gemini-3-pro-image-preview
```

결과는 `imagegen/output/`에 `날짜-시간_프롬프트.png` 형식으로 저장됩니다 (git에는 올라가지 않음).

기본 모델은 `gemini-2.5-flash-image`이며, `.env`의 `GEMINI_IMAGE_MODEL`로 바꿀 수 있습니다.
