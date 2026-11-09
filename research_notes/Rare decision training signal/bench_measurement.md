# The report's deciding check, measured on the bench (research session, 2026-10-27 14:25 by `date`; CPU only, from runs/probe/BENCH/O_B.json and its raw probes)

- **Data:** O_B, 259 own-Trainer prompts from the start pilot's P × P games, m 256, CRN; 3.55 answers on average.
  Paired-outcome discordance q: mean 0.296, median 0.304. On the bench the multiplier from pairing is smaller than on
  the lists (0.20).
- **Vine (K 8 re-deals, every answer, to game end):** per-state SE of the taken answer's seed-centred advantage,
  median 0.113, at about 28 rollouts a state.
- **PPO single visit (O_B's own readout):** sd(realized GAE − A*) pooled 0.30-0.35. Median n* (visits for an 80% sign
  on A*, assuming GAE is unbiased):

  | Prompt | n* (visits) | Games |
  |---|---|---|
  | Computer Search | 2,612 | about 531 |
  | Named five | 5,763 | |
  | All prompts | 9,287 | |
  | Energy Retrieval | 2,283 | |
  | Energy Removal | 27,762 | |
  | Super Energy Removal | 94,628 | |
  | Gust | 232,890 | |

- **Information per rollout, 1 / (variance × cost):** vine about 1 / (0.113² × 28) ≈ 2.8; PPO about 1 / 0.32² ≈ 9.8.
  If GAE is unbiased, PPO carries about 3.5x more information per rollout. So the report's top method fails its own
  deciding check on the bench.
- **Bias caveat:** rho_A (one realized GAE against A*) is −0.03 (Pearson) and −0.11 (Spearman) on Computer Search,
  n 96. That can't settle bias: with sd 0.32 and |A*| about 0.02, an unbiased estimator would correlate only about
  0.06.
- **What decides it:** arm 0 saw about 10,000 Computer Search fetches, about 4x n*. If its pilots improved
  Computer Search answers (ΔG_B > 0), PPO's credit works there. If not, PPO's credit at prompts is biased, the critic
  being the likely source, since GAE bootstraps V after about 20 steps.
- **O_B also shows Computer Search answers matter:** G (the held-out best answer minus the pilot's greedy) is +0.066
  (SE 0.012) per Computer Search prompt.
