
## Check 5: Google Trends Manual CSV Validation

**Test date:** 2026-04-29 20:42
**Method:** Manual CSV download from trends.google.com
**Files found:** 9

### brands_kr_shopping.csv

- **Status:** OK
- **Shape:** 174 rows x 9 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma

### multiTimeline.csv

- **Status:** OK
- **Shape:** 38 rows x 5 cols
- **Date range:** 2023-03-01 ~ 2026-04-01
- **Granularity:** monthly
- **Keywords:** 아디다스, Adidas, nike, 나이키

### products_ww_web.csv

- **Status:** OK
- **Shape:** 174 rows x 6 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** New Balance 990, New Balance 574, New Balance 9060, New Balance 2002R, New Balance 1906R

### brands_ww_youtube.csv

- **Status:** OK
- **Shape:** 174 rows x 5 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** New Balance, Nike, ADIDAS, PUMA

### products_kr_web.csv

- **Status:** OK
- **Shape:** 174 rows x 6 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** 뉴발란스 530, 뉴발란스 992, 뉴발란스 574, 뉴발란스 2002R, 뉴발란스 327

### brands_ww_web.csv

- **Status:** OK
- **Shape:** 174 rows x 5 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** New Balance, Nike, ADIDAS, PUMA

### brands_kr_web.csv

- **Status:** OK
- **Shape:** 174 rows x 9 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma

### brands_kr_youtube.csv

- **Status:** OK
- **Shape:** 174 rows x 9 cols
- **Date range:** 2022-12-25 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** 뉴발란스, New Balance, 나이키, Nike, 아디다스, Adidas, 푸마, Puma

### padding_competitive_kr.csv

- **Status:** OK
- **Shape:** 278 rows x 6 cols
- **Date range:** 2020-12-27 ~ 2026-04-19
- **Granularity:** weekly
- **Keywords:** 뉴발란스 패딩, 나이키 패딩, 아디다스 패딩, 노스페이스 패딩, 뉴발란스 574

### Verdict

**PASS.** Google Trends CSV parsing pipeline works correctly.
Manual CSV download is a viable primary collection method.

### Collection strategy

| Download | Keywords | Region | Estimated |
|---|---|---|---|
| 4 brands comparison | nike, adidas, puma, new balance | Global | 1 CSV |
| 4 brands comparison | nike, adidas, puma, new balance | Korea (KR) | 1 CSV |
| NB product lines | new balance 530, new balance 992 | Global | 1 CSV |
| NB product lines | new balance 530, new balance 992 | Korea (KR) | 1 CSV |
| Cross-reference anchor | new balance 530, new balance 992, nike | Global | 1 CSV |

**Total: 5 manual downloads. collector_google_trends.py will support CSV load (primary) + pytrends (optional fallback).**
