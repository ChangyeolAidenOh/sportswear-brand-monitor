# Google Trends CSV Download Protocol

**Date:** 2026-04-28
**Author:** Changyeol Oh
**Purpose:** Check 5 data collection — standardized download procedure

---

## Key decisions

1. **Korea: Search term with `+` operator** — transparent, reproducible, no Entity ambiguity
2. **Worldwide: Entity/Topic per brand** — selected for time-series continuity (see brand_topics.csv)
3. **Period: Apr 1, 2023 ~ Apr 1, 2026** (3 years, weekly granularity)
4. **Download: Interest over time only** (Top/Rising queries deferred to Stage 4-5)

## Entity selection rules

- Select the Entity/Topic with **continuous data from 2023-04 onward**
- If two candidates have similar patterns, pick the one with higher avg and no structural breaks
- Document selection in `database/seed/brand_topics.csv`
- If primary is deprecated later, switch to fallback

## Worldwide Entity mapping (confirmed)

| Brand | Selected | Type | Reason |
|---|---|---|---|
| Nike | Nike — Footwear company | Entity | Continuous from 2023 |
| Adidas | ADIDAS — Fashion brand | Entity | Apparel company has no data pre-2024 |
| Puma | Puma — Footwear corporation | Entity | TBD: verify continuity |
| New Balance | New Balance — Topic (large NB logo) | Topic | Footwear company starts low in 2023, Topic is consistent |

---

## Download matrix

### Group A: Core 4 brands — Korea (Search term)

| # | File name | Keywords (search term, `+` combined) | Region | Search type |
|---|---|---|---|---|
| A1 | `brands_kr_web.csv` | 나이키+Nike, 아디다스+Adidas, 푸마+Puma, 뉴발란스+New Balance | South Korea | Web Search |
| A2 | `brands_kr_youtube.csv` | 나이키+Nike, 아디다스+Adidas, 푸마+Puma, 뉴발란스+New Balance | South Korea | YouTube Search |
| A3 | `brands_kr_shopping.csv` | 나이키+Nike, 아디다스+Adidas, 푸마+Puma, 뉴발란스+New Balance | South Korea | Google Shopping |

### Group B: Core 4 brands — Worldwide (Entity/Topic)

| # | File name | Keywords (Entity/Topic) | Region | Search type |
|---|---|---|---|---|
| B1 | `brands_ww_web.csv` | Nike(Footwear co.), ADIDAS(Fashion brand), Puma(Footwear corp.), NB(Topic-large logo) | Worldwide | Web Search |
| B2 | `brands_ww_youtube.csv` | (same entities) | Worldwide | YouTube Search |
| B3 | `brands_ww_shopping.csv` | (same entities) | Worldwide | Google Shopping |

### Group C: Korean-language only (for 한글 비중 분석)

| # | File name | Keywords (search term, Korean only) | Region | Search type |
|---|---|---|---|---|
| C1 | `brands_kr_hangul_web.csv` | 나이키, 아디다스, 푸마, 뉴발란스 | South Korea | Web Search |

### Group D: NB product lines

| # | File name | Keywords (search term) | Region | Search type |
|---|---|---|---|---|
| D1 | `products_kr_web.csv` | 뉴발란스 530, 뉴발란스 992 | South Korea | Web Search |
| D2 | `products_ww_web.csv` | new balance 530, new balance 992 | Worldwide | Web Search |

---

## Total: 9 CSV downloads

Save all files to: `data/raw/google_trends/`

## Post-download validation

```bash
python spike_check5_gtrends.py
```

## MID Resolution (BEFORE downloading)

MIDs are NOT in CSV headers. Resolve them before downloading.

### Step 1: Run resolve script

```bash
python database/seed/resolve_brand_mids.py
```

This calls pytrends `suggestions()` for each brand to discover all Entity/Topic
candidates with their MIDs, then validates each via `build_payload()` with a
3-year time-series check (avg, 2023H1 avg, zero weeks, continuity).

### Step 2: Review outputs

- `docs/mid_resolution_report.md` — ranked candidates per brand
- `database/seed/brand_topics.csv` — auto-filled primary_mid + fallback_mid

### Step 3: Manual verification (if rate-limited)

If pytrends is blocked, the script still outputs suggestions (Step 1).
Manually verify time-series on trends.google.com:
1. Enter each candidate Entity/Topic
2. Set period: Apr 2023 ~ Apr 2026, Worldwide
3. Check: does data exist continuously from 2023-04?
4. Record the selected Entity/Topic name and type in brand_topics.csv
5. MID field can remain blank if only using web UI for downloads

### Step 4: Download CSVs

With confirmed Entity/Topic selections, proceed to the 9 downloads above.
When entering Worldwide keywords on trends.google.com, select the EXACT
Entity/Topic documented in brand_topics.csv from the dropdown.
