import sys
p = sys.argv[1] + '/env/runner.js'
s = open(p, encoding='utf-8').read()
old = """      for (const [name, group] of byAgent) {
        const out = await agents[name].act(group.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })));
        const keep = record.has(name);"""
new = """      // Ask every agent at once: with central GPU inference each agent (learner, league snapshots)
      // is a separate request, and awaiting them one by one cost a round trip per agent per step,
      // which is why collection slowed from 7 s to 55 s an iteration as snapshots were added.
      const groups = [...byAgent];
      const outs = await Promise.all(groups.map(([name, group]) =>
        agents[name].act(group.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })))));
      for (let gi = 0; gi < groups.length; gi++) {
        const [name, group] = groups[gi];
        const out = outs[gi];
        const keep = record.has(name);"""
if new in s:
    print("runner already patched")
else:
    assert old in s; s = s.replace(old, new); open(p, 'w', encoding='utf-8').write(s); print("runner patched")
