#!/bin/sh
# Log #34: the three builder designs of log #27, same cold start (seed 3: the same 16 random decks),
# same pilot, same budget: 8 PSRO iterations, 4 new decks each, 120 s of search per iteration,
# 48 games per pair.
for B in games model value; do
  PYTHONPATH=. .venv/Scripts/python.exe -m rl.psro --run runs/cmp-$B --policy runs/deckout-w0/model_it00014.pt \
    --init cold:16 --iterations 8 --games 48 --new 4 --builder $B --search-seconds 120 --seed 3 \
    > runs/cmp-$B.stdout.log 2>&1
done
