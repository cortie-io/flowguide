"""
eval/run_full.py — §4 본실험 실행기 (N=330, WORKFLOW_BUILD, GPT-4o only)

파일럿(eval/run_pilot.py)에서 검증된 채점 로직(run_one 등)을 그대로 import해서
재사용한다 — 프로토콜 동결. 이 파일이 추가하는 것은 (1) 330문항 벤치마크,
(2) 별도 출력 경로, (3) n8n 부하 안전장치(파일럿 중 n8n이 고CPU로 무응답에
빠졌던 사고 재발 방지를 위한 헬스체크+페이싱)뿐이다.

실행 방법(백그라운드, 세션/노트북 종료와 무관하게 계속 실행):
    cd /home/ubuntu/flowguide
    nohup python3 eval/run_full.py > eval/full_run.log 2>&1 < /dev/null &
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
        logging.FileHandler(EVAL_DIR / "full_run.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("full")

import httpx  # noqa: E402

import run_pilot  # noqa: E402 — 파일럿에서 검증된 채점 로직을 그대로 재사용(동결)
from benchmark_330 import BENCHMARK  # noqa: E402

RESULTS_PATH = EVAL_DIR / "full_results.jsonl"
REPORT_PATH = EVAL_DIR / "full_report.md"
STATS_PATH = EVAL_DIR / "full_stats.json"

# n8n 부하 안전장치: 파일럿 중 반복 publish/trigger/poll이 누적되며 n8n이
# 고CPU 무응답 상태에 빠졌던 사고(재시작으로 복구)가 있었다. 본실험은 파일럿의
# 11배 규모이므로 동일 문제가 재발할 위험이 훨씬 크다 — 매 QUERIES_PER_HEALTHCHECK
# 문항마다 n8n 응답성을 확인하고, 무응답이면 최대 3회까지 대기 후 재확인한다.
QUERIES_PER_HEALTHCHECK = 10
INTER_QUERY_DELAY_S = 2.0
N8N_HEALTH_URL = "http://localhost:5678/"


async def check_n8n_healthy(timeout: float = 8.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(N8N_HEALTH_URL)
            return resp.status_code == 200
    except Exception:
        return False


async def wait_for_n8n(max_wait_rounds: int = 6, round_sleep: float = 30.0) -> bool:
    for i in range(max_wait_rounds):
        if await check_n8n_healthy():
            return True
        log.warning("n8n 무응답 — %d/%d회 대기 중 (%.0fs)", i + 1, max_wait_rounds, round_sleep)
        await asyncio.sleep(round_sleep)
    return False


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

    log.info("본실험 시작: 총 %d문항 (완료 %d건 제외 %d건 남음)", len(BENCHMARK), len(done_ids), len(BENCHMARK) - len(done_ids))

    t_start = time.time()
    n_done_this_run = 0
    for item in BENCHMARK:
        if item["id"] in done_ids:
            continue

        if n_done_this_run % QUERIES_PER_HEALTHCHECK == 0:
            healthy = await check_n8n_healthy()
            if not healthy:
                log.warning("n8n 헬스체크 실패 — 복구 대기 시작")
                if not await wait_for_n8n():
                    log.error("n8n이 장시간 복구되지 않아 이번 문항의 EFR은 실패로 기록될 수 있음(계속 진행)")

        try:
            result = await run_pilot.run_one(item)
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
            log.info("진행: %d/%d 완료 (이번 실행), 평균 %.1fs/문항, 예상 잔여 %.0f분",
                      n_done_this_run, len(BENCHMARK) - len(done_ids), rate, eta_min)

        await asyncio.sleep(INTER_QUERY_DELAY_S)

    log.info("전체 330문항 실행 완료. 통계 분석 시작.")
    import analyze_pilot  # noqa: E402
    analyze_pilot.run(RESULTS_PATH, REPORT_PATH, STATS_PATH)
    log.info("완료. 리포트: %s", REPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
