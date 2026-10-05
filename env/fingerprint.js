// Canonical text of a whole game state, for comparing two states (or two runs) exactly.
// Cards are named by fullName plus an identity index from `cardIds`, so a card that moves or
// swaps places shows up; pass the same map when comparing states that share card objects.
'use strict';
const { C } = require('./engine.js');

function fingerprint(state, cardIds = new Map()) {
  const out = [];
  const path = new Set();
  const walk = v => {
    if (v === null || v === undefined || typeof v !== 'object') { out.push(typeof v === 'function' ? 'fn' : JSON.stringify(v)); return; }
    if (v instanceof C.Card) {
      if (!cardIds.has(v)) cardIds.set(v, cardIds.size);
      out.push(`<${v.fullName}#${cardIds.get(v)}>`);
      return;
    }
    if (path.has(v)) { out.push('cycle'); return; }
    path.add(v);
    if (Array.isArray(v)) { out.push('['); v.forEach(walk); out.push(']'); }
    else { out.push('{'); for (const k of Object.keys(v).sort()) { out.push(k + ':'); walk(v[k]); } out.push('}'); }
    path.delete(v);
  };
  walk(state);
  return out.join(',');
}

// Exact structural equality of two states (same result as comparing their fingerprints), with
// an early exit at the first difference. Cards compare by identity: both states must share them.
function sameState(a, b) {
  const eq = (x, y) => {
    if (x === y) return true;
    if (x === null || y === null || typeof x !== 'object' || typeof y !== 'object') {
      return typeof x === 'function' && typeof y === 'function' ? true : x === y;
    }
    if (x instanceof C.Card || y instanceof C.Card) return false;
    const ax = Array.isArray(x), ay = Array.isArray(y);
    if (ax !== ay) return false;
    if (ax) {
      if (x.length !== y.length) return false;
      for (let i = 0; i < x.length; i++) if (!eq(x[i], y[i])) return false;
      return true;
    }
    const kx = Object.keys(x), ky = Object.keys(y);
    if (kx.length !== ky.length) return false;
    for (const k of kx) {
      if (!Object.prototype.hasOwnProperty.call(y, k)) return false;
      if (!eq(x[k], y[k])) return false;
    }
    return true;
  };
  return eq(a, b);
}

module.exports = { fingerprint, sameState };
