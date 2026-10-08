"""
eval/run_pilot.py — §4 평가 방법론 파일럿 실행기 (N=30, WORKFLOW_BUILD, GPT-4o only)

실행 방법(백그라운드, 세션/노트북 종료와 무관하게 계속 실행):
    cd /home/ubuntu/flowguide
    nohup python3 eval/run_pilot.py > eval/pilot_run.log 2>&1 < /dev/null &
    disown

진행 상황: eval/pilot_results.jsonl (질의 1건 끝날 때마다 즉시 append, 중간에 죽어도 유실 없음)
최종 리포트: eval/pilot_report.md, eval/pilot_stats.json (모든 질의 완료 후 자동 생성)

명시적 제외 범위(사용자 확인 사항):
  - HR(환각률, 인간/LLM-judge 판정)은 제외 — 추후 별도 웹 도구에서 진행.
  - Gemini 교차모델 검증은 제외 — API 키 미보유, GPT-4o만 우선 진행.
  - DRR(동일 질의 k=3 반복 재현성)은 파일럿에서는 생략 — 비용 때문에 본실험(330문항) 범위로 유보.
  - EXPRESSION·ERROR_PATCH 인텐트는 파일럿에서는 생략 — WORKFLOW_BUILD 30문항에 집중.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
from pathlib import Path

ROOT = Path("/home/ubuntu/flowguide")
SERVER_DIR = ROOT / "server"
EVAL_DIR = ROOT / "eval"
sys.path.insert(0, str(SERVER_DIR))
sys.path.insert(0, str(EVAL_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(EVAL_DIR / "pilot_run.log", mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pilot")

# ── .env 로드 (OPENAI_API_KEY 등) ──────────────────────────────────────────
_env: dict[str, str] = {}
with open(ROOT / ".env") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        _env[k] = v
os.environ.setdefault("OPENAI_API_KEY", _env.get("OPENAI_API_KEY", ""))

import httpx  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402

from benchmark_pilot import BENCHMARK  # noqa: E402

BACKEND = "http://localhost:8000"
N8N_URL = "https://n8n.cortie.io"
N8N_API_KEY = _env.get("PILOT_N8N_API_KEY", "")
MODEL = "gpt-4o"

RESULTS_PATH = EVAL_DIR / "pilot_results.jsonl"
REPORT_PATH = EVAL_DIR / "pilot_report.md"
STATS_PATH = EVAL_DIR / "pilot_stats.json"

openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])


# ══════════════════════════════════════════════════════════════════════
# Tier 1 — Raw LLM (프레임워크 미적용)
# ══════════════════════════════════════════════════════════════════════

_RAW_SYSTEM_PROMPT = (
    "You are ChatGPT, a helpful general-purpose AI assistant. A user is asking you about "
    "n8n workflow automation. Answer naturally and helpfully using your own knowledge — you have "
    "no access to any external documentation, tools, or verification system. If the user asks you "
    "to build a workflow, provide the n8n workflow as a JSON code block (```json ... ```) with "
    "\"nodes\" and \"connections\" fields, in addition to a natural-language explanation."
)


async def call_tier1_raw(query: str) -> dict:
    t0 = time.time()
    resp = await openai_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _RAW_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        temperature=0.7,
    )
    text = resp.choices[0].message.content or ""
    usage = resp.usage
    return {
        "text": text,
        "latency_ms": int((time.time() - t0) * 1000),
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
    }


# ══════════════════════════════════════════════════════════════════════
# Tier 2+3 — 프로덕션 파이프라인(H_pre [+H_post]) 실 호출
#   REG 교정(reg_warning)·SemanticValidator(validation_report) 이벤트를
#   함께 캡처해 "Tier2=보정 전" / "Tier3=보정 후" 이중 채점의 원본으로 삼는다.
# ══════════════════════════════════════════════════════════════════════

async def call_tier23(query: str, session_id: str) -> dict:
    """
    중요(발견된 결함, 수정됨): 이 함수가 요청 바디에 "model"을 지정하지 않으면
    workspace.py는 `req.model or settings.llm_model`로 폴백하는데, 서버 기본값
    settings.llm_model은 .env의 LLM_MODEL=gpt-4o-mini다. 즉 model을 명시하지
    않으면 Tier2/3은 Tier1(call_tier1_raw, MODEL="gpt-4o")과 다른 모델
    (gpt-4o-mini)로 생성되어 "동일 LLM 엔진" 비교라는 §2.4의 전제가 깨진다.
    이 결함은 N=30 파일럿과 N=330 본실험 둘 다에 영향을 미쳤으므로, 두 결과
    모두 Tier1=GPT-4o / Tier2·3=GPT-4o-mini의 교란된 비교였다 — 재실행 필요.
    """
    t0 = time.time()
    full_text = ""
    reg_corrections: list[dict] = []
    validation_report: dict | None = None
    detected_nodes: list[str] = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{BACKEND}/api/workspace/stream",
            json={"message": query, "session_id": session_id, "model": f"openai:{MODEL}"},
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


# ══════════════════════════════════════════════════════════════════════
# 워크플로우 JSON 추출
# ══════════════════════════════════════════════════════════════════════

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def extract_workflow_json(text: str) -> dict | None:
    m = _JSON_BLOCK_RE.search(text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


# ══════════════════════════════════════════════════════════════════════
# PCR (Parameter Conformance Rate) — reg_validator의 유효 속성 집합을 재사용해
# 독립적으로 재구현. 노드별 parameters 최상위 키를 추출해 유효성 대조.
# ══════════════════════════════════════════════════════════════════════

import reg_validator  # noqa: E402

_VALID_PROPS = reg_validator._VALID_PROPERTIES


def _extract_param_keys(wf: dict) -> list[str]:
    keys: list[str] = []
    for node in wf.get("nodes", []) if isinstance(wf.get("nodes"), list) else []:
        if not isinstance(node, dict):
            continue
        params = node.get("parameters")
        if isinstance(params, dict):
            keys.extend(params.keys())
    return keys


def score_pcr(wf: dict | None) -> dict:
    if wf is None:
        return {"pcr": None, "n_params": 0, "n_valid": 0, "invalid_keys": []}
    keys = _extract_param_keys(wf)
    if not keys:
        return {"pcr": None, "n_params": 0, "n_valid": 0, "invalid_keys": []}
    invalid = [k for k in keys if k not in _VALID_PROPS]
    n_valid = len(keys) - len(invalid)
    return {
        "pcr": n_valid / len(keys),
        "n_params": len(keys),
        "n_valid": n_valid,
        "invalid_keys": invalid,
    }


def score_pcr_final(wf: dict | None, corrections: list[dict]) -> dict:
    """REG corrections(json_key 컨텍스트)을 적용한 뒤 PCR 재채점 — PCR_final."""
    if wf is None:
        return {"pcr": None, "n_params": 0, "n_valid": 0}
    keys = _extract_param_keys(wf)
    if not keys:
        return {"pcr": None, "n_params": 0, "n_valid": 0}
    fix_map = {c["original"]: c["corrected"] for c in corrections if c.get("context") == "json_key"}
    fixed_keys = [fix_map.get(k, k) for k in keys]
    n_valid = sum(1 for k in fixed_keys if k in _VALID_PROPS)
    return {"pcr": n_valid / len(keys), "n_params": len(keys), "n_valid": n_valid}


# ══════════════════════════════════════════════════════════════════════
# RCR (Rule-based Correction Rate) + 폴백 비율 — reg_validator 내부 함수 재사용
# ══════════════════════════════════════════════════════════════════════

def score_rcr(wf: dict | None) -> dict:
    if wf is None:
        return {"attempted": 0, "corrected": 0, "fallback": 0, "rcr": None, "lengths": []}
    keys = _extract_param_keys(wf)
    invalid = [k for k in keys if k not in _VALID_PROPS and k not in reg_validator._SKIP_TOKENS and len(k) >= 4]
    corrected = 0
    fallback = 0
    lengths: list[int] = []
    for k in invalid:
        suggestion = reg_validator._best_match(k, reg_validator._VALID_PROPERTIES)
        lengths.append(len(k))
        if suggestion:
            corrected += 1
        else:
            fallback += 1
    total = corrected + fallback
    return {
        "attempted": total,
        "corrected": corrected,
        "fallback": fallback,
        "rcr": (corrected / total) if total else None,
        "lengths": lengths,
    }


# ══════════════════════════════════════════════════════════════════════
# SA (Structural Alignment) — WORKFLOW_BUILD 인텐트의 §3.5 출력 통제 스키마가
# 요구하는 필수 구조 요소(마크다운 설명 + ```json 블록 + nodes/connections)
# 누락 여부를 결정론적으로 채점.
# ══════════════════════════════════════════════════════════════════════

def score_sa(text: str, wf: dict | None) -> dict:
    checks = {
        "has_markdown_intro": bool(re.search(r"[가-힣A-Za-z].{20,}", text.split("```")[0] if "```" in text else text)),
        "has_json_block": "```json" in text,
        "json_parses": wf is not None,
        "has_nodes_key": bool(wf and isinstance(wf.get("nodes"), list) and len(wf.get("nodes")) > 0),
        "has_connections_key": bool(wf and isinstance(wf.get("connections"), dict)),
    }
    return {"sa": sum(checks.values()) / len(checks), "checks": checks}


# ══════════════════════════════════════════════════════════════════════
# WIS (Weighted Issue Score) — semantic_validator 직접 호출(프로덕션과 동일 로직)
# ══════════════════════════════════════════════════════════════════════

import semantic_validator  # noqa: E402

_semv = semantic_validator.get_semantic_validator()
_SEV_WEIGHT = {"error": 3, "warning": 2, "info": 1}


def score_wis(text: str) -> dict:
    try:
        report = _semv.validate(workflow_json_str=text, response_text=text)
    except Exception as e:
        return {"wis": None, "error": str(e)}
    n_err, n_warn, n_info = len(report.errors), len(report.warnings), len(report.infos)
    wis = n_err * _SEV_WEIGHT["error"] + n_warn * _SEV_WEIGHT["warning"] + n_info * _SEV_WEIGHT["info"]
    return {"wis": wis, "n_error": n_err, "n_warning": n_warn, "n_info": n_info}


# ══════════════════════════════════════════════════════════════════════
# EFR (Execution Feasibility Rate) — 실제 배포된 /api/workflow/remote-inject
# (verify_execution=true)를 그대로 호출. 웹훅 트리거는 실제 실행결과까지,
# 그 외는 스키마 검증까지 자동 판정(§3.7의 실제 구현 범위와 동일).
# ══════════════════════════════════════════════════════════════════════

def apply_corrections(wf: dict | None, corrections: list[dict]) -> dict | None:
    """REG의 json_key 교정을 노드 parameters 키에 실제로 적용한 사본을 반환한다.

    프로덕션 백엔드는 REG의 교정안을 응답에 얹어 보여줄 뿐 실행에 쓰이는 JSON을
    자동으로 재작성하지는 않는다(교정 적용 여부는 프런트엔드/유저 몫). 따라서
    H3("H_post가 EFR을 추가로 개선하는가")를 의미 있게 측정하려면, "교정이 실제로
    적용되었다면"을 이 함수로 시뮬레이션해 Tier2(raw)와 Tier3(corrected)의 EFR을
    분리해야 한다 — 그러지 않으면 두 Tier가 같은 JSON을 채점하게 되어 차이가
    구조적으로 0이 된다.
    """
    if wf is None:
        return None
    fix_map = {c["original"]: c["corrected"] for c in corrections if c.get("context") == "json_key"}
    if not fix_map:
        return wf
    import copy
    wf2 = copy.deepcopy(wf)
    for node in wf2.get("nodes", []) if isinstance(wf2.get("nodes"), list) else []:
        if not isinstance(node, dict) or not isinstance(node.get("parameters"), dict):
            continue
        node["parameters"] = {fix_map.get(k, k): v for k, v in node["parameters"].items()}
    return wf2


async def score_efr(wf: dict | None, retries: int = 2) -> dict:
    if wf is None or not N8N_API_KEY:
        return {"efr_status": "no_workflow" if wf is None else "no_api_key", "workflow_id": None}
    payload = {
        "n8n_url": N8N_URL,
        "api_key": N8N_API_KEY,
        "verify_execution": True,
        "workflow_json": wf,
    }
    last_err: dict | None = None
    for attempt in range(retries + 1):
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(f"{BACKEND}/api/workflow/remote-inject", json=payload)
            except Exception as e:
                last_err = {"efr_status": "request_error", "detail": str(e) or type(e).__name__, "workflow_id": None}
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            if resp.status_code != 200:
                last_err = {"efr_status": "creation_failed", "http_status": resp.status_code, "detail": resp.text[:300], "workflow_id": None}
                # 502(일시적 n8n 연결 오류)는 재시도, 4xx(요청 자체 문제)는 즉시 반환
                if resp.status_code >= 500 and attempt < retries:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                return last_err
            break
    else:
        return last_err or {"efr_status": "request_error", "detail": "unknown", "workflow_id": None}

    data = resp.json()
    wf_id = data.get("workflow_id")
    # 정리 — 테스트로 생성한 워크플로우는 채점 직후 삭제
    if wf_id:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client2:
                await client2.delete(
                    f"{N8N_URL}/api/v1/workflows/{wf_id}",
                    headers={"X-N8N-API-KEY": N8N_API_KEY},
                )
        except Exception:
            pass
    if data.get("execution_verified"):
        return {
            "efr_status": "executed",
            "execution_status": data.get("execution_status"),
            "efr_pass": data.get("execution_status") == "success",
            "workflow_id": wf_id,
        }
    return {
        "efr_status": "schema_valid_only",
        "efr_pass": True,  # 스키마 검증(생성) 통과 = 최소 실행가능성 기준 충족
        "note": data.get("execution_note"),
        "workflow_id": wf_id,
    }


# ══════════════════════════════════════════════════════════════════════
# 메인 루프
# ══════════════════════════════════════════════════════════════════════

async def run_one(item: dict) -> dict:
    qid, query, tier_label = item["id"], item["query"], item["tier"]
    log.info("[%s] 시작 (tier=%s): %s", qid, tier_label, query[:60])

    tier1 = await call_tier1_raw(query)
    tier23 = await call_tier23(query, session_id=f"pilot-{qid}")

    wf1 = extract_workflow_json(tier1["text"])
    wf23 = extract_workflow_json(tier23["text"])

    pcr1 = score_pcr(wf1)
    pcr2_raw = score_pcr(wf23)  # Tier2 = 보정 전(raw)
    pcr3_final = score_pcr_final(wf23, tier23["reg_corrections"])  # Tier3 = 보정 후

    sa1 = score_sa(tier1["text"], wf1)
    sa23 = score_sa(tier23["text"], wf23)

    wis1 = score_wis(tier1["text"])
    wis3 = score_wis(tier23["text"])  # SemanticValidator는 Tier3 파이프라인에서만 노출되는 진단이지만, 공정 비교를 위해 Tier1 텍스트에도 동일 채점기를 적용

    rcr = score_rcr(wf23)

    wf23_corrected = apply_corrections(wf23, tier23["reg_corrections"])

    efr1 = await score_efr(wf1)
    efr2_raw = await score_efr(wf23)
    efr3_corrected = await score_efr(wf23_corrected)

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

    for item in BENCHMARK:
        if item["id"] in done_ids:
            continue
        try:
            result = await run_one(item)
        except Exception:
            log.error("[%s] 실패:\n%s", item["id"], traceback.format_exc())
            continue
        with open(RESULTS_PATH, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")

    log.info("전체 벤치마크 실행 완료. 통계 분석 시작.")
    import analyze_pilot  # noqa: E402
    analyze_pilot.run(RESULTS_PATH, REPORT_PATH, STATS_PATH)
    log.info("완료. 리포트: %s", REPORT_PATH)


if __name__ == "__main__":
    asyncio.run(main())
