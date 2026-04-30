# Stage 4 Track A — Robustness Check

**Date:** 2026-04-30 18:55
**Purpose:** Verify Granger results for non-stationary residual series
**Method:** 1st differencing of MSTL residual, re-run bidirectional Granger

---
Stage 4 Track A: Robustness Check
Started: 2026-04-30 18:55:21.243671

## Robustness Check: Non-stationary Residual Series

Non-stationary series identified in Step A3:
  adidas/global: ADF p=0.2703 (Search->CSI sig at lag 4, p=0.0443)
  nike/global: ADF p=0.0562 (Independent — null result, lower concern)

Procedure: apply 1st differencing to residual, verify ADF, re-run Granger.

### adidas/global
  residual diff1 ADF: stat=-6.0176, p=0.0000
  residual diff1: stationary (p=0.0000)
  observations: 40

  Search(d1) -> CSI(d1):
  | Lag | F-stat | p-value | Sig |
  |---|---|---|---|
  | 1 | 3.9455 | 0.0546 | No |
  | 2 | 2.8791 | 0.0704 | No |
  | 3 | 3.1135 | 0.0409 | **Yes** |
  | 4 | 3.8084 | 0.0140 | **Yes** |

  CSI(d1) -> Search(d1):
  | Lag | F-stat | p-value | Sig |
  |---|---|---|---|
  | 1 | 1.0758 | 0.3066 | No |
  | 2 | 0.9763 | 0.3873 | No |
  | 3 | 0.8438 | 0.4807 | No |
  | 4 | 0.5684 | 0.6877 | No |

  Verdict: Search->CSI significance SURVIVES after differencing
  -> adidas/global 'Search leads CSI' result is robust

### nike/global
  residual diff1 ADF: stat=-5.1565, p=0.0000
  residual diff1: stationary (p=0.0000)
  observations: 40

  Search(d1) -> CSI(d1):
  | Lag | F-stat | p-value | Sig |
  |---|---|---|---|
  | 1 | 0.2726 | 0.6048 | No |
  | 2 | 0.6817 | 0.5127 | No |
  | 3 | 0.8169 | 0.4947 | No |
  | 4 | 0.5826 | 0.6779 | No |

  CSI(d1) -> Search(d1):
  | Lag | F-stat | p-value | Sig |
  |---|---|---|---|
  | 1 | 1.1221 | 0.2965 | No |
  | 2 | 1.2931 | 0.2880 | No |
  | 3 | 2.4135 | 0.0862 | No |
  | 4 | 1.6665 | 0.1868 | No |

  Verdict: remains Independent after differencing (consistent)
