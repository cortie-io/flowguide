"""
eval/run_drr.py — §4.5 DRR(Decision Reproducibility Rate) 실행기.

"동일 질의를 동일 조건에서 k=3회 반복 실행했을 때, PCR 판정(정합/부정합)이
3회 모두 일치하는 질의의 비율" — GPT-4o(§4.4 주 모델), Tier3(H_pre+H_post,
실제 배포된 프레임워크 전체) 기준으로 측정한다.

EFR(n8n 실행 검증)은 DRR 정의에 포함되지 않으므로 호출하지 않는다 — 이 덕분에
n8n 부하와 무관하게 §4.4 H4(Gemini) 실행과 동시에 안전하게 돌릴 수 있고, API
제공사도 달라(OpenAI) 요청 한도가 겹치지 않는다.

채점 로직(PCR)은 run_pilot.py에서 그대로 import해 재사용한다("프로토콜 동결").
production 파이프라인의 실제 생성 온도(temperature=0.1, workflow_services.py에
하드코딩)를 그대로 사용한다 — 인위적으로 온도를 높이지 않고, 실사용자가 겪는
그대로의 재현성을 측정한다.

실행 방법(백그라운드):
    cd /home/ubuntu/flowguide
    nohup python3 eval/run_drr.py > eval/drr_run.log 2>&1 < /dev/null &
    disown
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
import traceback
from pathlib import Path

ROOT = Path("/home/ubuntu/flowguide")
EVAL_DIR = ROOT / "eval"
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(EVAL_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(EVAL_DIR / "drr_run.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("drr")

import run_pilot  # noqa: E402 — call_tier23/score_pcr_final 재사용(동결)
from benchmark_330 import BENCHMARK  # noqa: E402

K_REPEATS = 3
RESULTS_PATH = EVAL_DIR / "drr_results.jsonl"
REPORT_PATH = EVAL_DIR / "drr_report.md"
STATS_PATH = EVAL_DIR / "drr_stats.json"

INTER_QUERY_DELAY_S = 1.0


async def run_one(item: dict) -> dict:
    qid, query = item["id"], item["query"]
    reps = []
    for k in range(K_REPEATS):
        tier23 = await run_pilot.call_tier23(query, session_id=f"drr-{qid}-r{k}")
        wf = run_pilot.extract_workflow_json(tier23["text"])
        pcr_final = run_pilot.score_pcr_final(wf, tier23["reg_corrections"])
        reps.append({
            "pcr": pcr_final["pcr"],
            "n_params": pcr_final["n_params"],
            "workflow_extracted": wf is not None,
        })

    valid_pcrs = [r["pcr"] for r in reps if r["pcr"] is not None]
    conform_flags = [p == 1.0 for p in valid_pcrs] if valid_pcrs else []
    agree = len(conform_flags) == K_REPEATS and len(set(conform_flags)) == 1

    result = {"id": qid, "tier_label": item["tier"], "query": query, "reps": reps, "agree": agree}
    log.info("[%s] 완료 — PCR 3회: %s, 일치=%s", qid, [r["pcr"] for r in reps], agree)
    return result


async def main():
    EVAL_DIR.mkdir(exist_ok=True)
    done_ids: set[str] = set()
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            for line in f:
                try:
                    done_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
    if done_ids:
        log.info("이미 완료된 %d건 재사용, 이어서 진행", len(done_ids))

    log.info("DRR 실행 시작: 총 %d문항 x %d회 (완료 %d건 제외)", len(BENCHMARK), K_REPEATS, len(done_ids))

    t_start = time.time()
    n_done_this_run = 0
    for item in BENCHMARK:
        if item["id"] in done_ids:
            continue
        try:
            result = await run_one(item)
        except Exception:
            log.error("[%s] 실패:\n%s", item["id"], traceback.format_exc())
            await asyncio.sleep(5.0)
            continue

        with open(RESULTS_PATH, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

        n_done_this_run += 1
        if n_done_this_run % 10 == 0:
            elapsed = time.time() - t_start
            rate = elapsed / n_done_this_run
            remaining = len(BENCHMARK) - len(done_ids) - n_done_this_run
            eta_min = (remaining * rate) / 60
            log.info("진행: %d/%d 완료, 평균 %.1fs/문항, 예상 잔여 %.0f분",
                      n_done_this_run, len(BENCHMARK) - len(done_ids), rate, eta_min)

        await asyncio.sleep(INTER_QUERY_DELAY_S)

    log.info("DRR 실행 완료. 요약 계산.")
    rows = []
    with open(RESULTS_PATH) as f:
        for line in f:
            rows.append(json.loads(line))
    n = len(rows)
    n_agree = sum(1 for r in rows if r["agree"])
    drr = n_agree / n if n else None

    # 문항별 PCR 분산(변동성) 참고 지표
    import statistics
    stds = []
    for r in rows:
        vals = [x["pcr"] for x in r["reps"] if x["pcr"] is not None]
        if len(vals) >= 2:
            stds.append(statistics.pstdev(vals))

    stats = {
        "n_queries": n,
        "k_repeats": K_REPEATS,
        "n_agree": n_agree,
        "drr": drr,
        "mean_within_query_pcr_std": (sum(stds) / len(stds)) if stds else None,
    }
    with open(STATS_PATH, "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    report = [
        f"# §4.5 DRR(Decision Reproducibility Rate) 결과 (N={n}, k={K_REPEATS})",
        "",
        "**범위**: GPT-4o(§4.4 주 모델), Tier3(H_pre+H_post, 실제 배포된 프레임워크 전체), production 실제 온도(0.1) 사용.",
        "",
        f"- DRR = {drr:.4f} ({n_agree}/{n} 문항에서 PCR 완전정합 여부가 {K_REPEATS}회 모두 일치)" if drr is not None else "- DRR = N/A",
        f"- 문항 내 PCR 표준편차 평균(참고 지표) = {stats['mean_within_query_pcr_std']:.4f}" if stats["mean_within_query_pcr_std"] is not None else "",
        "",
        "## 주의사항",
        "",
        "- EFR(n8n 실행 검증)은 DRR 정의에 포함되지 않아 측정하지 않았다.",
        "- production 파이프라인의 실제 생성 온도(0.1)를 그대로 사용했다 — 인위적으로 온도를 높이지 않은, 실사용자 체감 재현성 지표다.",
    ]
    REPORT_PATH.write_text("\n".join(report), encoding="utf-8")
    log.info("완료. DRR=%s, 리포트: %s", drr, REPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
