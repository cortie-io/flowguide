#!/bin/bash
# GPT-4o 재실행(run_full.py)이 끝나면 자동으로 DRR + Gemini를 동시에 시작한다.
# run_full.py는 이미 별도 백그라운드 프로세스로 실행 중이므로 건드리지 않고,
# 완료 신호(리포트 파일 생성)만 폴링한다.
set -e
cd /home/ubuntu/flowguide

REPORT="/home/ubuntu/flowguide/eval/full_report.md"
LOG="/home/ubuntu/flowguide/eval/chain_after_full.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') [chain] GPT-4o 재실행 완료 대기 시작 (report: $REPORT)" >> "$LOG"

# full_run.py의 PID를 찾아 그 프로세스가 끝날 때까지 대기(가장 확실한 신호).
PID=$(pgrep -f "python3 eval/run_full.py" | head -1)
if [ -n "$PID" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [chain] run_full.py PID=$PID 감시 중" >> "$LOG"
    while kill -0 "$PID" 2>/dev/null; do
        sleep 20
    done
fi

# 리포트 파일이 실제로 생성될 때까지 추가 대기(분석 단계까지 완전히 끝났는지 확인)
for i in $(seq 1 30); do
    if [ -f "$REPORT" ]; then
        break
    fi
    sleep 10
done

echo "$(date '+%Y-%m-%d %H:%M:%S') [chain] GPT-4o 재실행 완료 확인. DRR + Gemini 동시 시작." >> "$LOG"

rm -f eval/drr_results.jsonl eval/drr_report.md eval/drr_stats.json eval/drr_run.log
nohup python3 eval/run_drr.py > eval/drr_run.log 2>&1 < /dev/null &
disown

rm -f eval/full_gemini_results.jsonl eval/full_gemini_report.md eval/full_gemini_stats.json eval/full_gemini_run.log
nohup python3 eval/run_full_gemini.py > eval/full_gemini_run.log 2>&1 < /dev/null &
disown

echo "$(date '+%Y-%m-%d %H:%M:%S') [chain] DRR·Gemini 둘 다 백그라운드로 시작됨" >> "$LOG"
