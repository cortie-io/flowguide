"""
eval/run_full_gemini.py — §4.4 H4(교차모델) 검증: 동일 330문항을 Gemini로 재실행.

채점 로직(PCR·SA·EFR·WIS·RCR 스코어러)은 run_pilot.py에서 그대로 import해
재사용한다("프로토콜 동결") — 텍스트/JSON을 채점할 뿐 어느 모델이 생성했는지는
채점 로직과 무관하다. 이 파일이 새로 추가하는 것은 생성 호출뿐이다.
  - Tier 1(raw): Gemini에 직접 호출(온톨로지·RAG 없음)
  - Tier 2/3(H_pre[+H_post]): 프로덕션 /api/workspace/stream을
    model="gemini:gemini-3.1-pro-preview"로 호출 — 동일 H_pre 코드 경로,
    모델 제공자만 교체(server/workflow_services.py의 _stream_gemini, §4.4).

실행 방법(백그라운드):
    cd /home/ubuntu/flowguide
    nohup python3 eval/run_full_gemini.py > eval/full_gemini_run.log 2>&1 < /dev/null &
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
        logging.FileHandler(EVAL_DIR / "full_gemini_run.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("full_gemini")

import httpx  # noqa: E402
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

import run_pilot  # noqa: E402 — 채점 로직 재사용(동결)
from benchmark_330 import BENCHMARK  # noqa: E402

GEMINI_MODEL = "gemini-3.1-pro-preview"
BACKEND = "http://localhost:8000"
RESULTS_PATH = EVAL_DIR / "full_gemini_results.jsonl"
REPORT_PATH = EVAL_DIR / "full_gemini_report.md"
STATS_PATH = EVAL_DIR / "full_gemini_stats.json"

QUERIES_PER_HEALTHCHECK = 10
INTER_QUERY_DELAY_S = 2.0
N8N_HEALTH_URL = "http://localhost:5678/"

_gemini_client = genai.Client(api_key=run_pilot._env.get("GEMINI_API_KEY", ""))


async def call_tier1_raw_gemini(query: str) -> dict:
    """Tier 1 — 프레임워크 미적용 Gemini 직접 호출(run_pilot.call_tier1_raw의 Gemini 버전)."""
    t0 = time.time()
    resp = await _gemini_client.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=[types.Part(text=query)])],
        config=types.GenerateContentConfig(
            system_instruction=run_pilot._RAW_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=8192,
        ),
    )
    text = resp.text or ""
    usage = resp.usage_metadata
    return {
        "text": text,
        "latency_ms": int((time.time() - t0) * 1000),
        "prompt_tokens": usage.prompt_token_count if usage else None,
        "completion_tokens": usage.candidates_token_count if usage else None,
        "thoughts_tokens": getattr(usage, "thoughts_token_count", None) if usage else None,
    }


async def call_tier23_gemini(query: str, session_id: str) -> dict:
    """Tier 2/3 — 동일 /api/workspace/stream을 model=gemini:...로 호출(H_pre 코드 경로 동일)."""
    t0 = time.time()
    full_text = ""
    reg_corrections: list[dict] = []
    validation_report: dict | None = None
    detected_nodes: list[str] = []

    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream(
            "POST",
            f"{BACKEND}/api/workspace/stream",
            json={"message": query, "session_id": session_id, "model": f"gemini:{GEMINI_MODEL}"},
        ) as resp:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("0:"):
                    try:
                        tok = json.loads(line[2:])
                        if isinstance(tok, str):
                            full_text += tok
                    except Exception:
                        pass
                elif line.startswith("2:"):
                    try:
                        parts = json.loads(line[2:])
                    except Exception:
                        continue
                    for p in parts if isinstance(parts, list) else []:
                        if not isinstance(p, dict):
                            continue
                        if p.get("type") == "reg_warning":
                            reg_corrections = p.get("corrections", [])
                        elif p.get("type") == "validation_report":
                            validation_report = p
                        elif p.get("type") == "ontology_context":
                            detected_nodes = p.get("detected_nodes", [])

    return {
        "text": full_text,
        "latency_ms": int((time.time() - t0) * 1000),
        "reg_corrections": reg_corrections,
        "validation_report": validation_report,
        "detected_nodes": detected_nodes,
    }


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


async def run_one(item: dict) -> dict:
    qid, query, tier_label = item["id"], item["query"], item["tier"]
    log.info("[%s] 시작 (tier=%s): %s", qid, tier_label, query[:60])

    tier1 = await call_tier1_raw_gemini(query)
    tier23 = await call_tier23_gemini(query, session_id=f"gemini-{qid}")

    wf1 = run_pilot.extract_workflow_json(tier1["text"])
    wf23 = run_pilot.extract_workflow_json(tier23["text"])

    pcr1 = run_pilot.score_pcr(wf1)
    pcr2_raw = run_pilot.score_pcr(wf23)
    pcr3_final = run_pilot.score_pcr_final(wf23, tier23["reg_corrections"])

    sa1 = run_pilot.score_sa(tier1["text"], wf1)
    sa23 = run_pilot.score_sa(tier23["text"], wf23)

    wis1 = run_pilot.score_wis(tier1["text"])
    wis3 = run_pilot.score_wis(tier23["text"])

    rcr = run_pilot.score_rcr(wf23)

    wf23_corrected = run_pilot.apply_corrections(wf23, tier23["reg_corrections"])

    efr1 = await run_pilot.score_efr(wf1)
    efr2_raw = await run_pilot.score_efr(wf23)
    efr3_corrected = await run_pilot.score_efr(wf23_corrected)

    result = {
        "id": qid,
        "tier_label": tier_label,
        "query": query,
        "tier1": {**tier1, "workflow_extracted": wf1 is not None, "pcr": pcr1, "sa": sa1, "wis": wis1, "efr": efr1},
        "tier23": {
            **tier23,
            "workflow_extracted": wf23 is not None,
            "pcr_raw": pcr2_raw,
            "pcr_final": pcr3_final,
            "sa": sa23,
            "wis": wis3,
            "efr_raw": efr2_raw,
            "efr_corrected": efr3_corrected,
            "rcr": rcr,
        },
    }
    log.info(
        "[%s] 완료 — Tier1 PCR=%s SA=%.2f WIS=%s EFR=%s | Tier3 PCR_final=%s SA=%.2f WIS=%s EFR_raw=%s EFR_corrected=%s",
        qid, pcr1["pcr"], sa1["sa"], wis1.get("wis"), efr1.get("efr_status"),
        pcr3_final["pcr"], sa23["sa"], wis3.get("wis"), efr2_raw.get("efr_status"), efr3_corrected.get("efr_status"),
    )
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

    log.info("Gemini 본실험 시작: 총 %d문항 (완료 %d건 제외 %d건 남음), 모델=%s",
              len(BENCHMARK), len(done_ids), len(BENCHMARK) - len(done_ids), GEMINI_MODEL)

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
            log.info("진행: %d/%d 완료 (이번 실행), 평균 %.1fs/문항, 예상 잔여 %.0f분",
                      n_done_this_run, len(BENCHMARK) - len(done_ids), rate, eta_min)

        await asyncio.sleep(INTER_QUERY_DELAY_S)

    log.info("Gemini 330문항 실행 완료. 통계 분석 시작.")
    import analyze_pilot  # noqa: E402
    analyze_pilot.run(RESULTS_PATH, REPORT_PATH, STATS_PATH)
    log.info("완료. 리포트: %s", REPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
