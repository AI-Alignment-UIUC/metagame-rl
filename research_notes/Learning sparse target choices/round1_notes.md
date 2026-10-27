# Round 1 (Evan rows 56, 79): learning a Trainer's target choice when its value is small next to the game's noise

Trigger: A1's result (log #268-#269). A Trainer's target is worth G +0.018 of game result a prompt (SE 0.0066, one
seed), and PPO's per-visit advantage needs a median of about 290k visits to get its sign. Three Haiku lean-readers,
2026-10-26 18:15. Every source was read from its abstract or search snippets only, unless said otherwise. Topics
covered in earlier rounds were skipped: RUDDER, hindsight credit and Gumbel search (`Dense training signals for
Trainer play/`), and the heads and search targets at sub-decisions (`Audit A1 Trainer plateau fixes/`).

## 1. Variance reduction for a low-SNR sub-choice
- **Tucker et al. 2018, "The Mirage of Action-Dependent Baselines"** (ICML; arXiv 1802.10031). Learned
  state-action baselines did not beat state-only ones on standard benchmarks; earlier gains came from implementation
  details. Read here as: the variance is mostly the future's luck, which an action-dependent baseline cannot remove.
- **Other variance reducers** (claimed reductions, no numbers recovered): Q-Prop (Gu 2017), Stein control variates
  (Liu 2018), RELAX (Grathwohl 2018), Expected Policy Gradients (Ciosek & Whiteson 2018, JMLR 2020) and Mean
  Actor-Critic (Allen 2017). The all-action family's bias comes from Q at rarely tried answers, which the
  exploration floor addresses.
- **Paired rollouts:** TRPO's vine (Schulman 2015) branches actions from the same trunk state with common random
  numbers, and PEGASUS (Ng & Jordan 2000) fixes scenarios so comparisons are deterministic. These are the methods
  that remove the future-luck noise from a comparison of answers.
- **Arithmetic (the reader's own, not a source):** paired games to resolve 0.018 at sd 1 is about (1.645/0.018)^2,
  about 8,400. PPO's 290k is 25-35x that, so most of PPO's noise is not the effect's own.

## 2. Target choices in other card and battle agents
- No source on Legends of Code and Magic, Hearthstone or Pokémon Showdown reports, or solves, a credit problem for
  target choices.
  - The LOCM papers (Vieira et al. 2020-2022) were abstract-only; Xi et al. 2023 could not be fetched.
- Nordeus's Heroic Magic Duel picks the action type, then a type-specific target head (snippet). Our pilot already
  factorises the same way, one prompt step at a time.
- Showdown agents (poke-env examples) shape rewards by HP and faints, which is game-specific and excluded here.
  Metamon (Grigsby 2025) trains on human logs, also excluded.

## 3. Policy updates from a Q over all actions that imitate no search answer
- **Muesli** (Hessel 2021): clipped, normalised advantages from a one-step model in an MPO-style (CMPO) policy
  target. It matches MuZero on Atari while acting from the policy alone. The CMPO formula and constants are not
  verified (the PDF did not parse).
- **MPO / V-MPO** (Abdolmaleki 2018; Song 2019): a non-parametric target pi·exp(Q/eta) with a KL trust region;
  V-MPO uses exponentiated advantages of sampled actions.
- **Small gaps:** a 0.018 gap moves exp(Q/eta) only for eta well under 0.018, so per-prompt normalisation of the
  advantage (Muesli) is what makes small gaps register (the reader's inference).
- **Row 60:** these use a Q learned from the agent's own returns, not an oracle's chosen answer.

## What it changed in tonight's queue (proposed to the implementation session about 18:17)
1. ΔG: score each trained pilot on A1's 438 stored prompt states. ΔG is Q-hat of the trained pilot's greedy answer
   minus Q-hat of the start pilot's greedy answer, over prompts. It is a paired, fixed-scenario readout with no
   game-outcome noise.
2. Read a C83 null through q_sd: a flat Q means the update rule was never tested.
3. A conditional CMPO arm, if Q learned but the policy did not follow.
