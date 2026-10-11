#!/bin/sh
# Log #62: the tournament chain after the Dark Dragonair fix and the per-turn cap. Smoke-tests the per-agent
# quotas end to end, then runs N=3, 6, 9 (seed 1) and N=3 seed 2, one after another.
cd "$(dirname "$0")/.."
PYTHONPATH=. .venv/Scripts/python.exe -m rl.tournament --run runs/_smoke-quota --agents 3 \
  --init-from runs/pilot-v2/model_it00349.pt --rounds 1 --games 4 --draft-calls 6 --climb-steps 3 \
  --confirm-games 4 --confirm-min 16 --ppo-iters 2 --agent-transitions 600 --matches-per-agent 8 \
  --eval-every 0 --workers 6 > runs/_smoke-quota.log 2>&1 || { echo "quota smoke run failed" >> runs/tournament_chain.log; exit 1; }
PYTHONPATH=. .venv/Scripts/python.exe -c "
import json
rows = [json.loads(l) for l in open('runs/_smoke-quota/log.jsonl')]
tr = [t for r in rows for t in r.get('train', [])]
assert tr and all(min(t['agent_collected'].values()) >= 600 for t in tr), [t['agent_collected'] for t in tr]
print('quota smoke ok', [t['agent_collected'] for t in tr])
" >> runs/tournament_chain.log 2>&1 || { echo "quota smoke check failed" >> runs/tournament_chain.log; exit 1; }
run() {
  echo "start $1 at $(date)" >> runs/tournament_chain.log
  PYTHONPATH=. .venv/Scripts/python.exe -m rl.tournament --run runs/$1 --agents $2 --seed $3 \
    --init-from runs/pilot-v2/model_it00349.pt --pool full --rounds 20 >> runs/$1.stdout.log 2>&1 \
    || { echo "$1 failed" >> runs/tournament_chain.log; return 1; }
}
run tourn-3 3 1 && run tourn-6 6 1 && run tourn-9 9 1 && run tourn-3-s2 3 2
echo "chain done at $(date)" >> runs/tournament_chain.log
