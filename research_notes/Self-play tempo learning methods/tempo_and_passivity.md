# Self-play passivity, stalling and tempo: notes for the Pokemon TCG pilot

Evidence tags: [read] = page text fetched and checked; [abstract] = only the arXiv abstract was readable; [snippet] = search-result text only, not opened; [secondary] = a blog or forum post, not the primary source. Budget was ~12 tool calls, so this is thin. Full papers (AlphaZero, AlphaStar Nature, KataGo, OpenAI Five) were not readable through the fetch tool.

## Key question 1: documented passivity, turtling, stalling or draw-seeking

### Takeaway
I found no clean, documented case of a self-play agent that learned to stall for a draw and was then fixed by a named method. The closest documented items are (a) AlphaStar's league, which the authors say discarded early risky rush strategies as training went on, and (b) KataGo's and Leela's draw/contempt settings, which show engines treating draws and risky-but-slim wins as a distortion they must correct by hand.

### Cited Findings
- AlphaStar's league: new agents were branched from existing ones, older agents were kept as frozen competitors, and "each agent has its own learning objective" to encourage diversity. "These risky strategies were discarded as training progressed." [DeepMind AlphaStar blog, read](https://deepmind.google/discover/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/)
- The same page says agents learn "from the game outcomes against competitors", i.e. outcome-based reward. It does not say whether shaped reward was used. [DeepMind AlphaStar blog, read]
- KataGo's developer distinguishes a self-play winrate from a fair-game points measure. He notes the self-play winrate "can drop sharply when the bot plans a risky move for slim winning chances", which distorts the estimate. [lightvector, lifein19x19 forum, secondary](https://lifein19x19.com/viewtopic.php?p=251740)
- KataGo's draw handling is a configurable value: `drawEquivalentWinsForWhite` (default 0.5 in the forum post's account; the post discusses 0.75 as an example). [lightvector, lifein19x19 forum, secondary](https://lifein19x19.com/viewtopic.php?p=251740) — the forum post itself was not fully read, so treat the exact default as unverified.
- Leela Chess Zero's contempt setting "discourages early draws against weaker opponents and encourages draws against stronger ones." [Chess Programming Wiki, snippet](https://chessprogramming.org/Contempt_Factor). A TalkChess thread reports an Elo-gap cap (420) added because a large rating gap made Leela overconfident. [TalkChess p=942177, secondary, opinion-level evidence]
- Self-play collapse: a 2026 arXiv paper reports that in Kuhn poker a Q-learning agent converged to a deterministic exploitative strategy within a few episodes. [arXiv 2605.16315, snippet, not opened]
- A Minimax Exploiter paper states that a +1/0/-1 terminal reward is suboptimal in adversarial games because the agent learns that an action was bad only at episode end. [arXiv 2311.17190, snippet, not opened]
- DeepNash (Stratego): the abstract says R-NaD "converges to an approximate Nash equilibrium, instead of 'cycling' around it, by directly modifying the underlying multi-agent learning dynamics", and that the method is model-free and search-free. [arXiv 2206.15378, abstract]. The abstract does not describe the regularizer, and I found no passivity claim in it.

### Inferences
- The documented failure mode in these sources is not "passive for a clock". It is cycling or collapse onto a narrow exploiting policy (PSRO and self-play literature), plus draw-value distortions in engines. A stall-to-clock failure in a pilot is closer to a reward-design problem (the clock/turn-limit outcome has a value) than to a documented self-play phenomenon.

### Gaps
- No primary-source account found of AlphaStar's "main exploiter" mechanism or its effect; the Nature paper was blocked (redirect to login).
- No paper found that reports a self-play agent turtling in a card game with a turn limit.

## Key question 2: game length and draws in AlphaZero, MuZero and MCTS self-play

### Takeaway
The draw and resignation rules of AlphaZero were not read in full, so I cannot cite their exact effects. What I can cite is that engines have had to add explicit draw-value knobs (KataGo drawEquivalentWins, Leela contempt) because the default treatment of draws biases play.

### Cited Findings
- KataGo: draw value is a parameter, so a draw can be valued as a fraction of a win (lightvector forum example: 0.75 for white). [secondary, see above]
- Leela contempt changes the win/draw/loss output by rating gap, and is capped in practice (forum report). [secondary, opinion-level]
- KataGo's arXiv abstract claims "a 50x reduction in computation over comparable methods" for self-play learning in Go, which is a speed claim, not a passivity claim. [arXiv 1902.10565, abstract]

### Inferences
- A draw-value below a win (contempt-style) is the one documented lever that makes an engine prefer a win over a safe draw without changing the win criterion. It is a value-target change, not a reward-discount change.

### Gaps
- AlphaZero's resignation threshold and its false-positive check: not verified (the arXiv page was abstract only).
- MuZero's handling of game length: not checked.

## Key question 3: objectives that reward winning sooner without changing what a win is

### Takeaway
The discount and per-turn penalty families are the main documented options. A fixed per-step cost is the cleanest "faster win" lever in the RL literature, but it is close to the per-turn discount already tested in the target system, so it needs a different form to be informative.

### Cited Findings
- A per-step penalty induces faster learning than a goal reward (tabular Q-learning). [arXiv 2205.15400, snippet, not opened]
- A fixed -1 per step with termination at the goal learns higher-quality policies than dense reward, per a 2024 paper. [snippet, not opened; the paper link came from the search results]
- OpenAI Five: the abstract confirms a 10-month scaled PPO self-play system with reward shaping and exploration heuristics. A secondary blog says gamma was annealed from 0.998 to 0.9997. [arXiv 1912.06680, abstract; the gamma values are secondary and unverified]

### Inferences
- A per-own-turn cost applied to all trajectories (win, loss, draw) moves the value of a win-on-turn-n down by n*c. This differs from a discount, which also scales the terminal reward. Whether it helps needs a test, because the discount sweep already showed no effect in the target system.

### Gaps
- Known failure mode of time penalties (a shaped cost that the agent can dodge by a draw or a resignation): found as a general warning in search results, not from a primary paper.

## Key question 4: opponent populations and leagues

### Takeaway
League training (AlphaStar) and best-response populations (PSRO) are the documented way to stop a population settling on one narrow equilibrium, but none of the sources I read shows that they specifically punish slow play.

### Cited Findings
- AlphaStar: the final agent is drawn from the Nash distribution of league members, described as "the least exploitable set of complementary competitors." Agents must "perform well against the strongest strategies" and "not forget how to defeat earlier ones." [DeepMind AlphaStar blog, read]
- PSRO: trains approximate best responses to mixtures of policies and computes meta-strategies by empirical game theory; generalizes fictitious play and double oracle. Evaluated on gridworld coordination and poker. [arXiv 1711.00832, abstract]
- Learning to Beat ByteRL: the state-of-the-art LOCM/Hearthstone agent is "highly exploitable", and the authors call the results "preliminary". [arXiv 2404.16689, abstract]

### Inferences
- A league containing an early, fast-attacking past self will punish a slow current policy, provided the fast past self was trained by the same self-play process and not scripted. This is an inference from the AlphaStar "risky strategies were discarded" observation; it is not demonstrated for a clock-limited card game.

### Gaps
- Whether the league's exploiters target passivity specifically: not verified.

## Key question 5: card-game AIs that learned aggressive or tempo play without hand-built heuristics or human data

### Takeaway
I found no card-game paper that clearly shows tempo or aggression emerging from pure self-play with no human data or heuristics. Most LOCM and Hearthstone work uses supervised learning, MCTS with learned evaluators, or heuristic features.

### Cited Findings
- Hearthstone MCTS with supervised learning: uses learned state evaluation, so it relies on game data. [arXiv 1808.04794, snippet]
- LOCM 2021 winner used two networks, one per side, trained by self-play during the draft stage. [secondary via arXiv 2404.16689 search summary]
- Competition overview of LOCM across five years. [arXiv 2305.11814, snippet]
- Xi et al. (LOCM end-to-end policy with optimistic smooth fictitious play, arXiv 2303.04096) is listed in the overview's references; I did not open it, so I cannot say what it reports.

### Gaps
- No verified card-game self-play agent with tempo-specific results. Xi et al. is the first thing to read.

## Proposals for the pilot (2-3), each with a falsifier

Each is tested against the ground truth (turns-to-six-Prizes, and a second seed), and none of them is one of the already-tried items (discount sweep, forced Trainer exploration, 1-2 turn search, oracle timing, persistent prize shaping, PlusPower branching, prize margin in deck selection).

1. **Fixed per-own-turn cost on every trajectory (win, loss and draw alike), not a discount.** Mechanism: a win on turn n loses n*c, so stalling costs even when the outcome is eventually a win; the terminal reward is unchanged. Evidence: the step-penalty results above ([snippet] 2205.15400; a 2024 -1 per-step result, [snippet]). Falsifier: turns-to-six-Prizes does not drop on a second seed, or win rate falls. It also fails if it only moves the draw rate, since a draw would then be cheaper than a loss.

2. **Turn-limit outcome valued below a win (draw-equivalent value).** Mechanism: a KataGo-style drawEquivalentWins parameter lowers the value of the clock result relative to a Prize win, so the agent is not indifferent between a win and a clock-draw. Evidence: KataGo's draw parameter and Leela's contempt, both [secondary]. Falsifier: the draw rate and the 41-45% no-payable-attack turns do not move, or the scripted-baseline comparison shows no change in turns-to-win.

3. **League member trained to exploit the current policy's slow play (main-exploiter style), with no scripted teacher.** Mechanism: an exploiter is trained by self-play against the current agent's frozen snapshots, so it learns whatever beats slow play, and the main agent must then beat it. Evidence: AlphaStar's league and the "risky strategies were discarded" observation [read]; the main-exploiter details were not verified. Falsifier: the exploiter does not converge to a faster line (its own Prize rate stays flat), or the main agent's tempo does not change against it.

## Source list
- DeepMind AlphaStar blog (read): https://deepmind.google/discover/blog/alphastar-mastering-the-real-time-strategy-game-starcraft-ii/
- lightvector, lifein19x19 forum (secondary): https://lifein19x19.com/viewtopic.php?p=251740
- Chess Programming Wiki, Contempt Factor (snippet): https://chessprogramming.org/Contempt_Factor
- DeepNash arXiv 2206.15378 (abstract): https://arxiv.org/abs/2206.15378
- PSRO arXiv 1711.00832 (abstract): https://arxiv.org/abs/1711.00832
- ByteRL exploitability arXiv 2404.16689 (abstract): https://arxiv.org/abs/2404.16689
- KataGo arXiv 1902.10565 (abstract): https://arxiv.org/abs/1902.10565
- OpenAI Five arXiv 1912.06680 (abstract): https://arxiv.org/abs/1912.06680
- AlphaZero arXiv 1712.01815 (abstract only, no draw content read): https://arxiv.org/abs/1712.01815
- LOCM competition overview arXiv 2305.11814 (snippet): https://arxiv.org/abs/2305.11814
- Minimax Exploiter arXiv 2311.17190 (snippet): https://arxiv.org/abs/2311.17190
- Self-play collapse arXiv 2605.16315 (snippet): https://arxiv.org/pdf/2605.16315
- Designing Rewards for Fast Learning arXiv 2205.15400 (snippet): https://arxiv.org/pdf/2205.15400
- Hearthstone MCTS + supervised learning arXiv 1808.04794 (snippet): https://arxiv.org/pdf/1808.04794
