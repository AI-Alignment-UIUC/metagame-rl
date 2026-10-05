// Small seeded PRNG (sfc32) with a copyable state, so a game's randomness can be cloned or
// replayed exactly. Seeds are mixed with splitmix32 so nearby seeds give unrelated streams.
'use strict';

function splitmix32(a) {
  return function () {
    a |= 0; a = a + 0x9e3779b9 | 0;
    let t = a ^ a >>> 16; t = Math.imul(t, 0x21f0aaad);
    t = t ^ t >>> 15; t = Math.imul(t, 0x735a2d97);
    return (t ^ t >>> 15) >>> 0;
  };
}

class Rng {
  constructor(seed = 0) {
    const sm = splitmix32(seed);
    this.s = [sm(), sm(), sm(), sm()];
    for (let i = 0; i < 12; i++) this.u32();
  }

  u32() {
    const s = this.s;
    const t = (s[0] + s[1] | 0) + s[3] | 0;
    s[3] = s[3] + 1 | 0;
    s[0] = s[1] ^ s[1] >>> 9;
    s[1] = s[2] + (s[2] << 3) | 0;
    s[2] = s[2] << 21 | s[2] >>> 11;
    s[2] = s[2] + t | 0;
    return t >>> 0;
  }

  float() { return this.u32() / 4294967296; }

  int(n) { return Math.floor(this.float() * n); }

  // Fisher-Yates over 0..n-1.
  permutation(n) {
    const p = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) {
      const j = this.int(i + 1);
      const t = p[i]; p[i] = p[j]; p[j] = t;
    }
    return p;
  }

  clone() {
    const r = Object.create(Rng.prototype);
    r.s = this.s.slice();
    return r;
  }
}

module.exports = { Rng };
