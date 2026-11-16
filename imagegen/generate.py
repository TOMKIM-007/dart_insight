"""Gemini 이미지 생성 CLI.

Antigravity 에이전트가 내부적으로 쓰는 것과 같은 Google 이미지 모델(Nano Banana 계열)을
Gemini API로 직접 호출합니다.

사용 예:
    python imagegen/generate.py "수채화 스타일의 숲 속 여우" --aspect 16:9
    python imagegen/generate.py "밤 풍경으로 바꿔줘" -i imagegen/output/fox.png
    python imagegen/generate.py --list-models
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_OUT = HERE / "output"
DEFAULT_MODEL = "gemini-2.5-flash-image"
ASPECTS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

# Windows 콘솔에서 한글이 깨지지 않도록
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def die(msg: str, code: int = 1) -> None:
    print(f"[오류] {msg}", file=sys.stderr)
    sys.exit(code)


def load_api_key() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
    except ImportError:
        pass
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key or key.strip() in ("", "your_key_here"):
        die(
            "GEMINI_API_KEY가 설정되지 않았습니다.\n"
            "  1) https://aistudio.google.com/apikey 에서 API 키 발급\n"
            f"  2) {REPO_ROOT / '.env'} 파일에 GEMINI_API_KEY=발급받은키 추가"
        )
    return key.strip()


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w가-힣]+", "_", text, flags=re.UNICODE).strip("_")
    return (s[:max_len] or "image").rstrip("_")


def explain_api_error(err: Exception) -> str:
    code = getattr(err, "code", None)
    text = str(err)
    if code in (401, 403) or "API_KEY_INVALID" in text or "PERMISSION_DENIED" in text:
        return "API 키가 잘못되었거나 이 모델 권한이 없습니다. AI Studio에서 키와 결제(billing) 연결을 확인하세요.\n" + text
    if code == 429 or "RESOURCE_EXHAUSTED" in text:
        return (
            "쿼터 초과(429). 이미지 모델은 무료 등급 한도가 매우 낮습니다. "
            "Gemini 앱 구독과 API 결제는 별개이므로 AI Studio에서 결제 프로젝트를 연결하세요.\n" + text
        )
    if code == 404 or "NOT_FOUND" in text:
        return "모델을 찾을 수 없습니다. --list-models 로 사용 가능한 이미지 모델을 확인하세요.\n" + text
    return text


def list_models(client) -> None:
    print("사용 가능한 이미지 관련 모델:")
    found = False
    for m in client.models.list():
        name = m.name.removeprefix("models/")
        if "image" in name or "imagen" in name:
            found = True
            print(f"  {name}")
    if not found:
        print("  (없음 — 키 권한을 확인하세요)")


def generate(client, args) -> list[Path]:
    from google.genai import types

    contents: list = []
    if args.image:
        from PIL import Image

        for p in args.image:
            path = Path(p)
            if not path.exists():
                die(f"입력 이미지가 없습니다: {path}")
            contents.append(Image.open(path))
    contents.append(args.prompt)

    config_kwargs = {"response_modalities": ["TEXT", "IMAGE"]}
    if args.aspect:
        config_kwargs["image_config"] = types.ImageConfig(aspect_ratio=args.aspect)
    config = types.GenerateContentConfig(**config_kwargs)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(args.prompt)
    saved: list[Path] = []

    for run in range(1, args.count + 1):
        print(f"[{run}/{args.count}] 생성 중... (모델: {args.model})")
        try:
            resp = client.models.generate_content(model=args.model, contents=contents, config=config)
        except Exception as e:  # google.genai.errors.APIError 등
            die(explain_api_error(e))

        cand = (resp.candidates or [None])[0]
        parts = (cand.content.parts if cand and cand.content else None) or []
        img_idx = 0
        for part in parts:
            if getattr(part, "text", None):
                print(f"  모델 메시지: {part.text.strip()}")
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                img_idx += 1
                ext = (inline.mime_type or "image/png").split("/")[-1].replace("jpeg", "jpg")
                suffix = f"_{run}" if args.count > 1 else ""
                suffix += f"-{img_idx}" if img_idx > 1 else ""
                path = out_dir / f"{stamp}_{slug}{suffix}.{ext}"
                path.write_bytes(inline.data)
                saved.append(path)
                print(f"  저장: {path}")
        if img_idx == 0:
            reason = getattr(cand, "finish_reason", None) if cand else None
            block = getattr(resp, "prompt_feedback", None)
            print(f"  이미지가 반환되지 않았습니다 (finish_reason={reason}, feedback={block}). "
                  "안전 필터에 걸렸거나 프롬프트를 더 구체적으로 바꿔 보세요.", file=sys.stderr)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini API로 이미지를 생성/편집합니다.")
    parser.add_argument("prompt", nargs="?", help="이미지 설명 프롬프트")
    parser.add_argument("-i", "--image", action="append", help="편집/합성용 입력 이미지 (여러 번 지정 가능)")
    parser.add_argument("-n", "--count", type=int, default=1, help="생성 횟수 (기본 1)")
    parser.add_argument("-m", "--model", default=None,
                        help=f"모델 ID (기본: GEMINI_IMAGE_MODEL 환경변수 또는 {DEFAULT_MODEL})")
    parser.add_argument("--aspect", choices=ASPECTS, help="가로세로 비율")
    parser.add_argument("-o", "--out", default=str(DEFAULT_OUT), help="저장 폴더")
    parser.add_argument("--list-models", action="store_true", help="사용 가능한 이미지 모델 목록 출력")
    args = parser.parse_args()

    if not args.list_models and not args.prompt:
        parser.error("프롬프트를 입력하세요 (또는 --list-models)")
    if args.count < 1:
        parser.error("--count 는 1 이상이어야 합니다")

    key = load_api_key()
    args.model = args.model or os.getenv("GEMINI_IMAGE_MODEL") or DEFAULT_MODEL

    try:
        from google import genai
    except ImportError:
        die("google-genai 패키지가 없습니다: pip install -r imagegen/requirements.txt")

    client = genai.Client(api_key=key)
    if args.list_models:
        try:
            list_models(client)
        except Exception as e:
            die(explain_api_error(e))
        return

    saved = generate(client, args)
    print(f"\n완료: {len(saved)}개 이미지 저장" if saved else "\n저장된 이미지가 없습니다.")
    if not saved:
        sys.exit(2)


if __name__ == "__main__":
    main()
