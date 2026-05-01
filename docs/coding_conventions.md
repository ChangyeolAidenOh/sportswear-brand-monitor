# Coding Conventions

Stage 0 spike 스크립트에서 확립된 코딩 컨벤션. Stage 1 이후 collector/preprocessor/analysis 모듈에도 동일하게 적용한다.

---

## 1. File Structure

모든 `.py` 파일은 다음 순서를 따른다:

```python
"""
모듈 docstring — Stage/목적/산출물 명시
Usage 포함 (CLI 실행 방법)
"""

# stdlib
import os
import sys
import time

# third-party
import pandas as pd
import requests

# local
from database.connection import get_cursor
```

- **import 순서:** stdlib → third-party → local, 각 그룹 내 알파벳 순, 그룹 사이 빈 줄 1개
- **`load_dotenv()`**: third-party import 직후, 모듈 상수 정의 전
- **optional dependency**: `try/except ImportError` + `sys.exit(1)` 패턴

```python
try:
    from pytrends.request import TrendReq
except ImportError:
    print("[ERROR] pytrends not installed. Run: pip install pytrends")
    sys.exit(1)
```

---

## 2. Constants

- **UPPER_SNAKE_CASE**, 모듈 최상단(import 직후)에 선언
- 경로 상수에는 `os.path.join` 없이 문자열로 정의, 사용 시점에 `os.path.join` 적용

```python
GTRENDS_DIR = "data/raw/google_trends"
FIG_DIR = "figures/exploratory"
REPORT_PATH = "docs/exploratory_findings.md"

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    "Content-Type": "application/json",
}

CALL_INTERVAL = 5
BACKOFF_BASE = 10
```

---

## 3. Function Naming

- **snake_case**, 동사 시작
- 검증 함수: `check_` 접두사 (`check_naver_datalab_api`, `check_nb_product_lines`)
- 가설 함수: `h{N}_` 접두사 (`h1_korea_global_alignment`, `h4_instagram_lead`)
- 재실행 함수: `h{N}_rerun` 접미사 (`h4_rerun`, `h5_rerun`)
- 데이터 fetch: `fetch_` 접두사 (`fetch_naver_datalab`, `fetch_naver_single_group`)
- 리포트 생성: `generate_report`
- 파싱: `parse_` 접두사 (`parse_google_trends_csv`)
- 유틸: 동작 동사 (`compute_ccf`, `compute_scale_ratio`, `find_overlap`, `rank_candidates`)

---

## 4. Function Docstrings

- 첫 줄에 목적 1문장, `"""` 같은 줄에서 시작
- 복잡한 함수만 추가 설명, 단순 함수는 1줄 docstring

```python
def fetch_naver_single_group(group_name, keywords, start_date, end_date):
    """Fetch a single keyword group from Naver DataLab (independent scale)."""
```

```python
def stitch_chunks(chunks, keyword_cols):
    """
    Stitch multiple chunks into a single DataFrame.
    First chunk is the reference (scale = 1.0).
    Each subsequent chunk is scaled using overlap with the previous.
    """
```

---

## 5. Section Separators

함수 블록 사이에 `# ===` 구분선 사용. 64자 고정.

```python
# ================================================================
# CHECK 1: Naver DataLab Search Trend API - response format
# ================================================================
def check_naver_datalab_api():
```

```python
# ================================================================
# H4: Instagram Proxy → NB Search Lead
# ================================================================
def h4_instagram_lead():
```

---

## 6. Print / Logging

- **spike 스크립트**: `print()` 직접 사용 (logging 모듈 미사용)
- **`log()` 헬퍼**: 콘솔 출력 + 리포트 라인 동시 누적

```python
REPORT_LINES = []

def log(msg=""):
    print(msg)
    REPORT_LINES.append(msg)

def section(title):
    log("")
    log(f"## {title}")
    log("")
```

- **진행 상황**: `print(f"  Step 1: ...")` — 2칸 들여쓰기로 계층 표시
- **경고/에러**: `[WARN]`, `[ERROR]`, `[RATE LIMITED]` 태그
- **장식 없음**: 이모지, `===`, `***` 같은 데코 마커 사용 안 함

```python
print(f"  [WARN] suggestions('{q}') failed: {e}")
print(f"  [ERROR] {err_name}: {e}")
print(f"    [RATE LIMITED] attempt {attempt+1}/{retries+1}, waiting {wait}s...")
```

---

## 7. Error Handling

- API 호출: `try/except` + 구체적 에러 타입 분기
- HTTP 에러: `requests.exceptions.HTTPError` 먼저, 그 다음 `Exception`
- rate limit: 지수 백오프 (`BACKOFF_BASE * (2 ** attempt)`)
- 실패 시 `None` 반환, 호출측에서 `if result is None` 체크

```python
try:
    resp = requests.post(url, headers=NAVER_HEADERS, json=body, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    ...
except requests.exceptions.HTTPError as e:
    log(f"- API HTTP error: {e}")
    log(f"- Response body: {e.response.text[:500] if e.response else 'N/A'}")
except Exception as e:
    log(f"- API error: {e}")
```

---

## 8. CLI / argparse

- `if __name__ == "__main__": main()` 패턴 필수
- CLI 옵션이 있는 스크립트: `argparse` 사용, `parse_args()` 별도 함수
- 플래그: `--dry-run`, `--skip-validation` 같은 명시적 이름

```python
def parse_args():
    parser = argparse.ArgumentParser(description="Resolve Google Trends MIDs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Single probe call to check IP block status")
    parser.add_argument("--skip-validation", action="store_true",
                        help="Run suggestions() only, skip build_payload()")
    return parser.parse_args()
```

---

## 9. Data Handling (pandas)

- 날짜 컬럼: `pd.to_datetime()` 변환 후 `"date"` 으로 통일 rename
- `<1` 값 처리: `df[col].replace("<1", "0.5")` → `pd.to_numeric(errors="coerce")`
- merge: `pd.merge(df1, df2, on="date", how="inner")`
- 0 나누기 방지: `.replace(0, np.nan)`

```python
df[date_col] = pd.to_datetime(df[date_col].str.strip(), errors="coerce")
df = df.rename(columns={date_col: "date"})
df = df.sort_values("date").reset_index(drop=True)
```

---

## 10. Matplotlib

- 백엔드: `matplotlib.use("Agg")` — GUI 없이 파일 저장 전용
- 한글 폰트: `AppleGothic` (macOS)
- 마이너스 부호: `axes.unicode_minus: False`
- 기본 설정 블록:

```python
plt.rcParams.update({
    "font.family": "AppleGothic",
    "axes.unicode_minus": False,
    "figure.dpi": 150,
    "figure.figsize": (12, 5),
    "axes.grid": True,
    "grid.alpha": 0.3,
})
```

- 저장: `plt.savefig(fig_path, bbox_inches="tight")` → `plt.close()`
- twin axis: 스케일이 다른 두 시계열 비교 시 `ax.twinx()` 사용
- 색상: 브랜드/카테고리별 고정 컬러 dict

```python
colors = {"뉴발란스": "#E74C3C", "나이키": "#FF6B00",
          "아디다스": "#3498DB", "노스페이스": "#2ECC71"}
```

---

## 11. Output / Report Generation

- 산출물은 `docs/`, `figures/` 디렉토리에 저장
- 디렉토리 자동 생성: `os.makedirs(dir, exist_ok=True)` — 모듈 최상단
- 리포트: `REPORT_LINES` 리스트에 markdown 누적 → `generate_report()`에서 파일 쓰기
- 리포트 포맷: markdown with `##` 섹션, `|` 테이블, `**bold**` 판정

```python
def generate_report():
    header = ["# Report Title", "", f"**Date:** {datetime.now()}", ...]
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        for line in header + REPORT_LINES:
            f.write(line + "\n")
    print(f"\nReport saved: {REPORT_PATH}")
```

---

## 12. Directory Conventions

```
sportswear-brand-monitor/
├── database/               # DB 스키마, 연결, seed 데이터
│   ├── schema_init.sql
│   ├── connection.py
│   └── seed/               # brand_topics.csv, resolve scripts
├── data/
│   └── raw/                # 원본 데이터 (gitignored)
│       └── google_trends/  # 스티칭 CSV + 청크 하위 폴더
├── docs/                   # 리포트, 프로토콜, 컨벤션
├── figures/
│   └── exploratory/        # Stage 0 시각화
├── spike_*.py              # Stage 0 spike 스크립트 (루트)
├── stitch_gtrends.py       # 유틸리티 (루트)
├── quick_exploratory_pass.py
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

- spike 스크립트: 프로젝트 루트
- collector/preprocessor/analysis: Stage 1 이후 전용 디렉토리 (`collectors/`, `preprocessor/`, `analysis/`)
- 파일명: `snake_case`, 역할 접두사 (`spike_`, `collector_`, `stitch_`)

---

## 13. Comments

- 영어로 작성
- 한국어 키워드/브랜드명은 문자열 내에서만 사용
- 인라인 주석은 코드 옆 2칸 후 `#`
- 블록 주석: 함수 docstring 또는 `# ===` 섹션 헤더로 대체

```python
# Handle '<1' values -> 0.5
for col in keyword_cols:
    if df[col].dtype == object:
        df[col] = df[col].replace("<1", "0.5")
        df[col] = pd.to_numeric(df[col], errors="coerce")
```

---

## 14. Git Conventions

- 커밋 분리: `init` → `feat` → `docs` 순서
- 커밋 메시지: conventional commits (`init:`, `feat:`, `docs:`, `fix:`)
- `.gitignore`: `data/raw/`, `data/postgres/`, `.env`, `__pycache__/`

---

*본 문서는 Stage 0 spike 스크립트에서 추출한 컨벤션이며, Stage 1 이후 production 코드에도 동일하게 적용한다.*
