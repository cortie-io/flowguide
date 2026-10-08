"""
eval/analyze_pilot.py — pilot_results.jsonl 통계 분석 + 리포트 생성 (§4.7 준용)

§4.7 전체 계획 중 파일럿에서 실제로 계산하는 것:
  - H1: PCR(Tier1 vs Tier3_final) — Wilcoxon 부호순위검정(연속형 원 지표) +
        McNemar(PCR==1.0 완전정합 이분화, 강건성 확인)
  - H2: WIS(Tier1 vs Tier3) — Wilcoxon 부호순위검정
  - H3: EFR(Tier2_raw vs Tier3_corrected) — McNemar
  - H5: RCR — 교정 성공 여부와 파라미터명 길이 간 Spearman 순위상관
  - 효과크기(Cohen's h / rank-biserial) + 부트스트랩 95% CI(10,000회) + Holm-Bonferroni
파일럿(N=30)에서 생략, N=330 본실험에서 수행: 질의 내 군집성을 고려한 회귀모형
1차 분석(PCR·EFR은 GEE, WIS는 선형혼합모형) — N=30에서는 수렴이 불안정해 통계적으로
방어하기 어려움. 이번 실행에서도 생략: H4(Gemini 교차모델), DRR, HR.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats as sps
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests


def run_glmm(rows: list[dict]) -> dict:
    """§4.7 1차 분석(GLMM) — N이 작으면(파일럿) 수렴이 불안정해 생략하고,
    N=330 본실험에서 실행한다. PCR은 파라미터 단위 이항 GEE(질의로 군집화,
    교환가능 상관구조)로 질의 무작위효과를 근사하고, WIS는 질의를 무작위
    절편으로 갖는 선형혼합모형으로 적합한다. EFR도 동일한 GEE 구조를 사용한다."""
    try:
        import pandas as pd
        import statsmodels.api as sm
        import statsmodels.formula.api as smf
    except ImportError as e:
        return {"error": f"statsmodels/pandas 미설치: {e}"}

    out: dict = {}

    # PCR: 파라미터 단위 이항 GEE
    recs = []
    for r in rows:
        qid = r["id"]
        for tier, d in (("Tier1", r["tier1"]["pcr"]), ("Tier3", r["tier23"]["pcr_final"])):
            if d.get("pcr") is None:
                continue
            n_valid, n_total = d["n_valid"], d["n_params"]
            for i in range(n_total):
                recs.append({"query": qid, "tier": tier, "valid": 1 if i < n_valid else 0})
    try:
        df = pd.DataFrame(recs)
        df["tier_bin"] = (df["tier"] == "Tier3").astype(int)
        gee = smf.gee("valid ~ tier_bin", groups="query", data=df,
                       family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
        res = gee.fit()
        coef, se, p = float(res.params["tier_bin"]), float(res.bse["tier_bin"]), float(res.pvalues["tier_bin"])
        out["pcr_gee"] = {
            "n_obs": len(df), "coef_log_odds": coef, "se": se, "p_value": p,
            "odds_ratio": float(np.exp(coef)),
            "odds_ratio_95ci": [float(np.exp(coef - 1.96 * se)), float(np.exp(coef + 1.96 * se))],
        }
    except Exception as e:
        out["pcr_gee"] = {"error": str(e)}

    # WIS: 질의 무작위 절편을 갖는 선형혼합모형
    recs2 = []
    for r in rows:
        qid = r["id"]
        w1, w3 = r["tier1"]["wis"].get("wis"), r["tier23"]["wis"].get("wis")
        if w1 is not None:
            recs2.append({"query": qid, "tier": "Tier1", "wis": w1})
        if w3 is not None:
            recs2.append({"query": qid, "tier": "Tier3", "wis": w3})
    try:
        df2 = pd.DataFrame(recs2)
        df2["tier_bin"] = (df2["tier"] == "Tier3").astype(int)
        md = smf.mixedlm("wis ~ tier_bin", data=df2, groups=df2["query"])
        mdf = md.fit()
        coef, se, p = float(mdf.params["tier_bin"]), float(mdf.bse["tier_bin"]), float(mdf.pvalues["tier_bin"])
        out["wis_lmm"] = {"n_obs": len(df2), "coef": coef, "se": se, "p_value": p,
                           "ci_95": [coef - 1.96 * se, coef + 1.96 * se]}
    except Exception as e:
        out["wis_lmm"] = {"error": str(e)}

    # EFR: 질의 단위 이항 GEE (Tier2_raw vs Tier3_corrected)
    recs3 = []
    for r in rows:
        qid = r["id"]
        e2 = r["tier23"]["efr_raw"].get("efr_pass")
        e3 = r["tier23"]["efr_corrected"].get("efr_pass")
        if e2 is not None:
            recs3.append({"query": qid, "tier": "Tier2", "pass_": int(e2)})
        if e3 is not None:
            recs3.append({"query": qid, "tier": "Tier3", "pass_": int(e3)})
    try:
        df3 = pd.DataFrame(recs3)
        df3["tier_bin"] = (df3["tier"] == "Tier3").astype(int)
        gee3 = smf.gee("pass_ ~ tier_bin", groups="query", data=df3,
                        family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
        res3 = gee3.fit()
        coef, se, p = float(res3.params["tier_bin"]), float(res3.bse["tier_bin"]), float(res3.pvalues["tier_bin"])
        out["efr_gee"] = {"n_obs": len(df3), "coef_log_odds": coef, "se": se, "p_value": p}
    except Exception as e:
        out["efr_gee"] = {"error": str(e)}

    return out


def _load(results_path: Path) -> list[dict]:
    rows = []
    with open(results_path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _paired(a: list, b: list) -> tuple[list, list]:
    pa, pb = [], []
    for x, y in zip(a, b):
        if x is not None and y is not None:
            pa.append(x)
            pb.append(y)
    return pa, pb


def bootstrap_mean_diff_ci(x: list[float], y: list[float], n_boot: int = 10000, seed: int = 42):
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    if len(x) == 0:
        return None, None, None
    rng = np.random.default_rng(seed)
    n = len(x)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        diffs.append(np.mean(y[idx]) - np.mean(x[idx]))
    diffs = np.array(diffs)
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return float(np.mean(y) - np.mean(x)), float(lo), float(hi)


def cohens_h(p1: float, p2: float) -> float:
    return float(2 * np.arcsin(np.sqrt(p2)) - 2 * np.arcsin(np.sqrt(p1)))


def rank_biserial_wilcoxon(x: list[float], y: list[float]) -> float | None:
    diffs = np.array(y, dtype=float) - np.array(x, dtype=float)
    diffs = diffs[diffs != 0]
    if len(diffs) == 0:
        return None
    ranks = sps.rankdata(np.abs(diffs))
    r_plus = ranks[diffs > 0].sum()
    r_minus = ranks[diffs < 0].sum()
    n = len(diffs)
    total = n * (n + 1) / 2
    return float((r_plus - r_minus) / total)


def wilcoxon_test(x: list[float], y: list[float]) -> dict:
    x, y = _paired(x, y)
    if len(x) < 2 or all(a == b for a, b in zip(x, y)):
        return {"n": len(x), "p_value": None, "note": "표본 부족 또는 전원 동률"}
    try:
        stat, p = sps.wilcoxon(x, y)
    except ValueError as e:
        return {"n": len(x), "p_value": None, "note": str(e)}
    mean_diff, lo, hi = bootstrap_mean_diff_ci(x, y)
    return {
        "n": len(x),
        "statistic": float(stat),
        "p_value": float(p),
        "mean_x": float(np.mean(x)),
        "mean_y": float(np.mean(y)),
        "mean_diff_y_minus_x": mean_diff,
        "bootstrap_95ci": [lo, hi],
        "rank_biserial_r": rank_biserial_wilcoxon(x, y),
    }


def mcnemar_test(x: list[bool | None], y: list[bool | None]) -> dict:
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 2:
        return {"n": len(pairs), "p_value": None, "note": "표본 부족"}
    n01 = sum(1 for a, b in pairs if (not a) and b)   # x fail, y pass
    n10 = sum(1 for a, b in pairs if a and (not b))   # x pass, y fail
    n00 = sum(1 for a, b in pairs if (not a) and (not b))
    n11 = sum(1 for a, b in pairs if a and b)
    table = [[n11, n10], [n01, n00]]
    try:
        res = mcnemar(table, exact=(n01 + n10) < 25, correction=True)
        p = float(res.pvalue)
    except Exception as e:
        p = None
    p1 = sum(1 for a, _ in pairs if a) / len(pairs)
    p2 = sum(1 for _, b in pairs if b) / len(pairs)
    return {
        "n": len(pairs),
        "table_[[both_pass,x_only],[y_only,both_fail]]": table,
        "p_value": p,
        "rate_x": p1,
        "rate_y": p2,
        "cohens_h": cohens_h(p1, p2) if 0 < p1 < 1 and 0 < p2 < 1 else cohens_h(max(p1, 1e-6), max(p2, 1e-6)),
    }


def run(results_path: Path, report_path: Path, stats_path: Path) -> None:
    rows = _load(results_path)
    n = len(rows)

    pcr1 = [r["tier1"]["pcr"]["pcr"] for r in rows]
    pcr3f = [r["tier23"]["pcr_final"]["pcr"] for r in rows]
    pcr2raw = [r["tier23"]["pcr_raw"]["pcr"] for r in rows]

    sa1 = [r["tier1"]["sa"]["sa"] for r in rows]
    sa23 = [r["tier23"]["sa"]["sa"] for r in rows]

    wis1 = [r["tier1"]["wis"].get("wis") for r in rows]
    wis3 = [r["tier23"]["wis"].get("wis") for r in rows]

    efr1 = [r["tier1"]["efr"].get("efr_pass") for r in rows]
    efr2raw = [r["tier23"]["efr_raw"].get("efr_pass") for r in rows]
    efr3corr = [r["tier23"]["efr_corrected"].get("efr_pass") for r in rows]

    pcr1_conform = [(p == 1.0) if p is not None else None for p in pcr1]
    pcr3_conform = [(p == 1.0) if p is not None else None for p in pcr3f]

    tests: dict = {}
    tests["H1_pcr_wilcoxon_tier1_vs_tier3final"] = wilcoxon_test(pcr1, pcr3f)
    tests["H1_pcr_mcnemar_fullconform_tier1_vs_tier3final"] = mcnemar_test(pcr1_conform, pcr3_conform)
    tests["H2_wis_wilcoxon_tier1_vs_tier3"] = wilcoxon_test(wis1, wis3)
    tests["H3_efr_mcnemar_tier2raw_vs_tier3corrected"] = mcnemar_test(efr2raw, efr3corr)
    tests["extra_sa_wilcoxon_tier1_vs_tier23"] = wilcoxon_test(sa1, sa23)
    tests["extra_efr_mcnemar_tier1_vs_tier3corrected"] = mcnemar_test(efr1, efr3corr)

    # Holm-Bonferroni across the three pre-registered hypothesis tests (H1 wilcoxon, H2, H3)
    primary_keys = ["H1_pcr_wilcoxon_tier1_vs_tier3final", "H2_wis_wilcoxon_tier1_vs_tier3", "H3_efr_mcnemar_tier2raw_vs_tier3corrected"]
    pvals = [tests[k]["p_value"] for k in primary_keys if tests[k].get("p_value") is not None]
    keys_with_p = [k for k in primary_keys if tests[k].get("p_value") is not None]
    if pvals:
        reject, corrected, _, _ = multipletests(pvals, alpha=0.05, method="holm")
        for k, r, c in zip(keys_with_p, reject, corrected):
            tests[k]["holm_bonferroni_corrected_p"] = float(c)
            tests[k]["reject_at_alpha_0.05_after_correction"] = bool(r)

    # H5: RCR — 교정 성공(1/0) vs 파라미터명 길이, 전 질의 풀링
    lengths_all: list[int] = []
    success_all: list[int] = []
    for r in rows:
        rcr = r["tier23"]["rcr"]
        # 개별 토큰 단위 성공/실패를 복원할 수 없으므로(집계만 저장), 질의 단위 rcr 비율과
        # 평균 길이를 사용한 근사 상관으로 대체하고 그 한계를 리포트에 명시한다.
        if rcr.get("lengths"):
            avg_len = sum(rcr["lengths"]) / len(rcr["lengths"])
            lengths_all.append(avg_len)
            success_all.append(rcr["rcr"] if rcr["rcr"] is not None else 0.0)
    if len(lengths_all) >= 3:
        rho, p5 = sps.spearmanr(lengths_all, success_all)
        tests["H5_rcr_vs_length_spearman"] = {"n": len(lengths_all), "rho": float(rho), "p_value": float(p5),
                                               "note": "질의 단위 근사(평균 파라미터명 길이 vs RCR) — 토큰 단위 원자료는 본실험에서 저장 예정"}
    else:
        tests["H5_rcr_vs_length_spearman"] = {"n": len(lengths_all), "p_value": None, "note": "표본 부족"}

    # 요약 통계
    def _mean(xs):
        xs = [x for x in xs if x is not None]
        return float(np.mean(xs)) if xs else None

    def _rate(xs):
        xs = [x for x in xs if x is not None]
        return float(sum(1 for x in xs if x) / len(xs)) if xs else None

    summary = {
        "n_queries": n,
        "pcr_tier1_mean": _mean(pcr1),
        "pcr_tier2_raw_mean": _mean(pcr2raw),
        "pcr_tier3_final_mean": _mean(pcr3f),
        "sa_tier1_mean": _mean(sa1),
        "sa_tier23_mean": _mean(sa23),
        "wis_tier1_mean": _mean(wis1),
        "wis_tier3_mean": _mean(wis3),
        "efr_tier1_rate": _rate(efr1),
        "efr_tier2_raw_rate": _rate(efr2raw),
        "efr_tier3_corrected_rate": _rate(efr3corr),
        "rcr_mean": _mean([r["tier23"]["rcr"].get("rcr") for r in rows]),
    }

    glmm = run_glmm(rows) if n >= 100 else {"note": f"N={n} < 100 — 질의 무작위효과 수렴 불안정 우려로 생략(McNemar/Wilcoxon만 수행)"}

    out = {"summary": summary, "tests": tests, "glmm": glmm, "n": n}
    with open(stats_path, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    _write_report(rows, summary, tests, glmm, report_path)


def _fmt(x, nd=3):
    return "N/A" if x is None else f"{x:.{nd}f}"


def _write_report(rows, summary, tests, glmm, report_path: Path) -> None:
    lines = []
    lines.append("# §4 평가 방법론 실행 결과 (N={})".format(summary["n_queries"]))
    lines.append("")
    lines.append("**범위**: WORKFLOW_BUILD 인텐트, GPT-4o 단일 모델, HR(인간판정)·DRR·Gemini 교차모델 제외.")
    lines.append("")
    lines.append("## 요약 지표")
    lines.append("")
    lines.append("| 지표 | Tier 1 (Raw LLM) | Tier 2 (H_pre) | Tier 3 (H_pre+H_post) |")
    lines.append("|---|---|---|---|")
    lines.append(f"| PCR (평균) | {_fmt(summary['pcr_tier1_mean'])} | {_fmt(summary['pcr_tier2_raw_mean'])} | {_fmt(summary['pcr_tier3_final_mean'])} (PCR_final) |")
    lines.append(f"| SA (평균) | {_fmt(summary['sa_tier1_mean'])} | {_fmt(summary['sa_tier23_mean'])} | {_fmt(summary['sa_tier23_mean'])} (Tier2·3 동일 생성물) |")
    lines.append(f"| WIS (평균, 낮을수록 우수) | {_fmt(summary['wis_tier1_mean'])} | — | {_fmt(summary['wis_tier3_mean'])} |")
    lines.append(f"| EFR (비율) | {_fmt(summary['efr_tier1_rate'])} | {_fmt(summary['efr_tier2_raw_rate'])} (raw) | {_fmt(summary['efr_tier3_corrected_rate'])} (corrected) |")
    lines.append(f"| RCR (평균) | — | — | {_fmt(summary['rcr_mean'])} |")
    lines.append("")
    lines.append("## 가설 검정 결과 (Holm-Bonferroni 보정 후)")
    lines.append("")
    for key, label in [
        ("H1_pcr_wilcoxon_tier1_vs_tier3final", "H1 — PCR, Tier1 vs Tier3_final (Wilcoxon)"),
        ("H1_pcr_mcnemar_fullconform_tier1_vs_tier3final", "H1 강건성 — PCR 완전정합(=1.0) 이분화 (McNemar)"),
        ("H2_wis_wilcoxon_tier1_vs_tier3", "H2 — WIS, Tier1 vs Tier3 (Wilcoxon)"),
        ("H3_efr_mcnemar_tier2raw_vs_tier3corrected", "H3 — EFR, Tier2(raw) vs Tier3(corrected) (McNemar)"),
        ("H5_rcr_vs_length_spearman", "H5 — RCR vs 파라미터명 길이 (Spearman, 질의 단위 근사)"),
    ]:
        t = tests.get(key, {})
        lines.append(f"### {label}")
        lines.append(f"- n = {t.get('n')}")
        if t.get("p_value") is not None:
            lines.append(f"- p = {_fmt(t['p_value'], 4)}" + (f", Holm-Bonferroni 보정 p = {_fmt(t.get('holm_bonferroni_corrected_p'), 4)}" if "holm_bonferroni_corrected_p" in t else ""))
        else:
            lines.append(f"- p = N/A ({t.get('note', '')})")
        if "mean_diff_y_minus_x" in t:
            lines.append(f"- 평균 차이(Tier3−Tier1) = {_fmt(t['mean_diff_y_minus_x'])}, 부트스트랩 95% CI = [{_fmt(t['bootstrap_95ci'][0])}, {_fmt(t['bootstrap_95ci'][1])}]")
            lines.append(f"- rank-biserial r = {_fmt(t.get('rank_biserial_r'))}")
        if "rate_x" in t:
            lines.append(f"- 비율: x={_fmt(t['rate_x'])}, y={_fmt(t['rate_y'])}, Cohen's h = {_fmt(t.get('cohens_h'))}")
        if "rho" in t:
            lines.append(f"- Spearman ρ = {_fmt(t['rho'])}")
        lines.append("")

    lines.append("## 1차 분석 — 질의 내 군집성을 고려한 회귀모형 (PCR·EFR: GEE / WIS: 선형혼합모형)")
    lines.append("")
    if "note" in glmm:
        lines.append(f"- {glmm['note']}")
    else:
        pcr_g = glmm.get("pcr_gee", {})
        wis_g = glmm.get("wis_lmm", {})
        efr_g = glmm.get("efr_gee", {})
        lines.append("### PCR — 파라미터 단위 이항 GEE (질의로 군집화, 교환가능 상관구조)")
        if "error" in pcr_g:
            lines.append(f"- 적합 실패: {pcr_g['error']}")
        else:
            lines.append(f"- n_obs = {pcr_g['n_obs']}, Tier 계수(log-odds) = {_fmt(pcr_g['coef_log_odds'])}, p = {_fmt(pcr_g['p_value'], 4)}")
            lines.append(f"- 승산비(OR) = {_fmt(pcr_g['odds_ratio'])}, 95% CI = [{_fmt(pcr_g['odds_ratio_95ci'][0])}, {_fmt(pcr_g['odds_ratio_95ci'][1])}]")
        lines.append("")
        lines.append("### WIS — 질의 무작위 절편을 갖는 선형혼합모형")
        if "error" in wis_g:
            lines.append(f"- 적합 실패: {wis_g['error']}")
        else:
            lines.append(f"- n_obs = {wis_g['n_obs']}, Tier 계수 = {_fmt(wis_g['coef'])}, p = {_fmt(wis_g['p_value'], 4)}, 95% CI = [{_fmt(wis_g['ci_95'][0])}, {_fmt(wis_g['ci_95'][1])}]")
        lines.append("")
        lines.append("### EFR — 질의 단위 이항 GEE (Tier2_raw vs Tier3_corrected)")
        if "error" in efr_g:
            lines.append(f"- 적합 실패: {efr_g['error']}")
        else:
            lines.append(f"- n_obs = {efr_g['n_obs']}, Tier 계수(log-odds) = {_fmt(efr_g['coef_log_odds'])}, p = {_fmt(efr_g['p_value'], 4)}")
        lines.append("")

    lines.append("## 주의사항")
    lines.append("")
    n_q = summary["n_queries"]
    min_n = 91
    if n_q < min_n:
        lines.append(f"- N={n_q}은 §4.3의 최소 표본(조건당 {min_n}건)에 못 미쳐 위 p값은 확증적 결론이 아닌 예비 신호로 해석해야 한다.")
    else:
        pcr_n = tests.get("H1_pcr_wilcoxon_tier1_vs_tier3final", {}).get("n")
        wis_n = tests.get("H2_wis_wilcoxon_tier1_vs_tier3", {}).get("n")
        efr_n = tests.get("H3_efr_mcnemar_tier2raw_vs_tier3corrected", {}).get("n")
        lines.append(f"- N={n_q}은 §4.3의 최소 표본(조건당 {min_n}건)을 상회한다. 아래 각 검정의 유효 n(PCR={pcr_n}, WIS={wis_n}, EFR={efr_n})이 {n_q}보다 작은 것은 표본 부족이 아니라, 쌍대 비교의 전제조건(양쪽 Tier 모두에서 해당 지표가 계산 가능해야 함)에 따라 일부 문항이 제외되었기 때문이다(예: 워크플로우 JSON 추출 실패, 실행 검증 응답 미수신).")
    lines.append("- 1차 분석(GEE·선형혼합모형)은 N<100에서는 수렴이 불안정할 수 있어 생략하고 McNemar/Wilcoxon 강건성 검정만 수행한다.")
    lines.append("- HR(환각률, 인간판정)·Gemini 교차모델(H4)·DRR(재현성)은 사용자 확인에 따라 이번 실행 범위에서 제외하였다.")
    lines.append("- EFR은 n8n Public API 제약상 웹훅 트리거 워크플로우만 실제 실행 결과까지 확인하고, 그 외는 스키마 검증 통과 여부로 판정한다(§3.7/§5.2).")
    lines.append("- §4.3의 \"질의의 약 40%를 실제 커뮤니티에서 수집\"은 이번 실행에서 생략하고 전량 체계적 자동 생성으로 구성하였다(§4.8 외적 타당성 한계).")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import sys
    results = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("eval/pilot_results.jsonl")
    report = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("eval/pilot_report.md")
    stats = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("eval/pilot_stats.json")
    run(results, report, stats)
