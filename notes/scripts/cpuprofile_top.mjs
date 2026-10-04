import fs from 'fs';

const file = process.argv[2];
const p = JSON.parse(fs.readFileSync(file, 'utf8'));

// self time per node id, from the sample/timeDelta streams
const selfUs = new Map();
for (let i = 0; i < p.samples.length; i++) {
  const id = p.samples[i];
  const dt = p.timeDeltas[i] || 0;
  selfUs.set(id, (selfUs.get(id) || 0) + dt);
}

const byId = new Map(p.nodes.map(n => [n.id, n]));
const label = n => {
  const f = n.callFrame;
  const url = (f.url || '').replace(/^file:\/\/\//, '').replace(/.*[\\/]ryuu-play[\\/]/, '');
  const name = f.functionName || '(anonymous)';
  return `${name}  @ ${url || 'native'}:${f.lineNumber + 1}`;
};

// aggregate self time by function identity (name+url+line), summing all call-tree nodes
const agg = new Map();
let total = 0;
for (const [id, us] of selfUs) {
  const n = byId.get(id);
  if (!n) continue;
  const k = label(n);
  agg.set(k, (agg.get(k) || 0) + us);
  total += us;
}

// also roll up by source file
const byFile = new Map();
for (const [k, us] of agg) {
  const f = k.split('@ ')[1] || 'native';
  const file = f.split(':')[0];
  byFile.set(file, (byFile.get(file) || 0) + us);
}

const ms = us => (us / 1000).toFixed(0).padStart(6);
const pct = us => ((100 * us) / total).toFixed(1).padStart(5);

console.log(`total sampled: ${(total / 1e6).toFixed(2)} s\n`);
console.log('=== self time by function (top 25) ===');
[...agg].sort((a, b) => b[1] - a[1]).slice(0, 25)
  .forEach(([k, us]) => console.log(`${ms(us)} ms ${pct(us)}%  ${k}`));

console.log('\n=== self time by file (top 20) ===');
[...byFile].sort((a, b) => b[1] - a[1]).slice(0, 20)
  .forEach(([k, us]) => console.log(`${ms(us)} ms ${pct(us)}%  ${k}`));
