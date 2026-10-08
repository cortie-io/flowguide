# §4 평가 방법론 실행 결과 (N=330)

**범위**: WORKFLOW_BUILD 인텐트, GPT-4o 단일 모델, HR(인간판정)·DRR·Gemini 교차모델 제외.

## 요약 지표

| 지표 | Tier 1 (Raw LLM) | Tier 2 (H_pre) | Tier 3 (H_pre+H_post) |
|---|---|---|---|
| PCR (평균) | 0.803 | 0.808 | 0.829 (PCR_final) |
| SA (평균) | 0.964 | 0.998 | 0.998 (Tier2·3 동일 생성물) |
| WIS (평균, 낮을수록 우수) | 0.273 | — | 0.188 |
| EFR (비율) | 0.906 | 0.910 (raw) | 0.914 (corrected) |
| RCR (평균) | — | — | 0.120 |

## 가설 검정 결과 (Holm-Bonferroni 보정 후)

### H1 — PCR, Tier1 vs Tier3_final (Wilcoxon)
- n = 310
- p = 0.0011, Holm-Bonferroni 보정 p = 0.0034
- 평균 차이(Tier3−Tier1) = 0.026, 부트스트랩 95% CI = [0.005, 0.047]
- rank-biserial r = 0.242

### H1 강건성 — PCR 완전정합(=1.0) 이분화 (McNemar)
- n = 310
- p = 0.0053
- 비율: x=0.242, y=0.329, Cohen's h = 0.193

### H2 — WIS, Tier1 vs Tier3 (Wilcoxon)
- n = 330
- p = 0.6326, Holm-Bonferroni 보정 p = 1.0000
- 평균 차이(Tier3−Tier1) = -0.085, 부트스트랩 95% CI = [-0.267, 0.073]
- rank-biserial r = -0.099

### H3 — EFR, Tier2(raw) vs Tier3(corrected) (McNemar)
- n = 324
- p = 1.0000, Holm-Bonferroni 보정 p = 1.0000
- 비율: x=0.910, y=0.914, Cohen's h = 0.011

### H5 — RCR vs 파라미터명 길이 (Spearman, 질의 단위 근사)
- n = 238
- p = 0.0000
- Spearman ρ = -0.600

## 1차 분석 — 질의 내 군집성을 고려한 회귀모형 (PCR·EFR: GEE / WIS: 선형혼합모형)

### PCR — 파라미터 단위 이항 GEE (질의로 군집화, 교환가능 상관구조)
- n_obs = 4609, Tier 계수(log-odds) = 0.273, p = 0.0000
- 승산비(OR) = 1.313, 95% CI = [1.163, 1.483]

### WIS — 질의 무작위 절편을 갖는 선형혼합모형
- n_obs = 660, Tier 계수 = -0.085, p = 0.3306, 95% CI = [-0.256, 0.086]

### EFR — 질의 단위 이항 GEE (Tier2_raw vs Tier3_corrected)
- n_obs = 648, Tier 계수(log-odds) = 0.038, p = 0.3166

## 주의사항

- N=330은 §4.3의 최소 표본(조건당 91건)을 상회한다. 아래 각 검정의 유효 n(PCR=310, WIS=330, EFR=324)이 330보다 작은 것은 표본 부족이 아니라, 쌍대 비교의 전제조건(양쪽 Tier 모두에서 해당 지표가 계산 가능해야 함)에 따라 일부 문항이 제외되었기 때문이다(예: 워크플로우 JSON 추출 실패, 실행 검증 응답 미수신).
- 1차 분석(GEE·선형혼합모형)은 N<100에서는 수렴이 불안정할 수 있어 생략하고 McNemar/Wilcoxon 강건성 검정만 수행한다.
- HR(환각률, 인간판정)·Gemini 교차모델(H4)·DRR(재현성)은 사용자 확인에 따라 이번 실행 범위에서 제외하였다.
- EFR은 n8n Public API 제약상 웹훅 트리거 워크플로우만 실제 실행 결과까지 확인하고, 그 외는 스키마 검증 통과 여부로 판정한다(§3.7/§5.2).
- §4.3의 "질의의 약 40%를 실제 커뮤니티에서 수집"은 이번 실행에서 생략하고 전량 체계적 자동 생성으로 구성하였다(§4.8 외적 타당성 한계).
