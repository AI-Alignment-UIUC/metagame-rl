#!/bin/sh
# Log #33: does paying less for deck-out wins move the token pilot toward prizes?
# Two 15-iteration fine-tunes of runs/a4-tok/model_it00249.pt, self-play, identical but for --deckout-win.
for W in 0 1; do
  PYTHONPATH=. .venv/Scripts/python.exe -m rl.train --run runs/deckout-w$W --matchup all --iterations 15 \
    --transitions 4096 --concurrency 48 --inference gpu --model tokens --micro-batch 1024 --amp \
    --init-from runs/a4-tok/model_it00249.pt --snapshot-every 5 --deckout-win $W \
    --eval-every 15 --eval-opponents simplebot --eval-games 400 > runs/deckout-w$W.stdout.log 2>&1
done
