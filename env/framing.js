// Framed binary messages over a worker's stdin/stdout, for central (GPU) inference:
//   [u32 length of the rest][u8 type][payload]
//   type 1 JSON (utf8): commands and replies
//   type 2 inference request (worker -> learner), type 3 inference response (learner -> worker)
// See rl/remote.py for the other side.
'use strict';

const JSON_FRAME = 1, REQUEST = 2, RESPONSE = 3;

function writeFrame(stream, type, payload) {
  const head = Buffer.alloc(5);
  head.writeUInt32LE(payload.length + 1, 0);
  head.writeUInt8(type, 4);
  stream.write(head);
  stream.write(payload);
}

function writeJson(stream, obj) { writeFrame(stream, JSON_FRAME, Buffer.from(JSON.stringify(obj), 'utf8')); }

// Calls onFrame(type, payloadBuffer) for each complete frame read from `stream`.
function readFrames(stream, onFrame) {
  let buf = Buffer.alloc(0);
  stream.on('data', chunk => {
    buf = buf.length ? Buffer.concat([buf, chunk]) : chunk;
    while (buf.length >= 4) {
      const len = buf.readUInt32LE(0);
      if (buf.length < 4 + len) break;
      const type = buf.readUInt8(4);
      const payload = buf.subarray(5, 4 + len);
      buf = buf.subarray(4 + len);
      onFrame(type, Buffer.from(payload));
    }
  });
}

// Packs typed arrays (each padded to 8 bytes) after a JSON header: [u32 header length][header][arrays].
function packArrays(header, arrays) {
  const meta = [];
  let offset = 0;
  for (const [name, arr] of arrays) {
    meta.push({ name, dtype: arr.constructor.name.replace('Array', '').toLowerCase(), offset, length: arr.length });
    offset += arr.byteLength + ((8 - arr.byteLength % 8) % 8);
  }
  const h = Buffer.from(JSON.stringify({ ...header, arrays: meta }), 'utf8');
  const pre = Buffer.alloc(4);
  pre.writeUInt32LE(h.length, 0);
  const pad = Buffer.alloc((8 - (4 + h.length) % 8) % 8);
  const parts = [pre, h, pad];
  for (const [, arr] of arrays) {
    parts.push(Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength));
    const p = (8 - arr.byteLength % 8) % 8;
    if (p) parts.push(Buffer.alloc(p));
  }
  return Buffer.concat(parts);
}

function unpackArrays(buf) {
  const hl = buf.readUInt32LE(0);
  const header = JSON.parse(buf.subarray(4, 4 + hl).toString('utf8'));
  const base = 4 + hl + ((8 - (4 + hl) % 8) % 8);
  const T = { int16: Int16Array, uint8: Uint8Array, int32: Int32Array, float32: Float32Array };
  const out = {};
  for (const m of header.arrays) {
    const C = T[m.dtype];
    const copy = Buffer.from(buf.subarray(base + m.offset, base + m.offset + m.length * C.BYTES_PER_ELEMENT));
    out[m.name] = new C(copy.buffer, copy.byteOffset, m.length);
  }
  return { header, arrays: out };
}

module.exports = { JSON_FRAME, REQUEST, RESPONSE, writeFrame, writeJson, readFrames, packArrays, unpackArrays };
