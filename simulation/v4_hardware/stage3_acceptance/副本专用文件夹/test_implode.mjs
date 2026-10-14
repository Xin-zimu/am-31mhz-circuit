import fs from 'node:fs/promises';
import { implode, explode } from 'file:///D:/ewbwork/node_modules/node-pkware/dist/simple/index.js';
const [xmlPath] = process.argv.slice(2);
const xml = await fs.readFile(xmlPath);
const CHUNK = 900000;
for (const ct of ['ascii','binary']) {
  for (const ds of ['large','medium','small']) {
    const outs = [];
    for (let off = 0; off < xml.length; off += CHUNK) {
      const p = xml.subarray(off, Math.min(off + CHUNK, xml.length));
      const c = Buffer.from(implode(p.buffer.slice(p.byteOffset, p.byteOffset + p.byteLength), ct, ds));
      // verify we can explode it back identically
      const back = Buffer.from(explode(c.buffer.slice(c.byteOffset, c.byteOffset + c.byteLength)));
      outs.push({ comp: c.length, ok: back.equals(Buffer.from(p)) });
    }
    console.log(ct, ds, JSON.stringify(outs.map(o=>o.comp)), 'allOk=' + outs.every(o=>o.ok));
  }
}
