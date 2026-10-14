// Encode a Multisim .ms14 container: PKWare implode (ASCII, large dict), 900000-byte chunks.
import fs from 'node:fs/promises';
import { implode } from 'file:///D:/ewbwork/node_modules/node-pkware/dist/simple/index.js';

const [inputXml, output] = process.argv.slice(2);
const xml = await fs.readFile(inputXml);
const CHUNK = 900000;
const header = 'MSMCompressedElectronicsWorkbenchXML';
const parts = [];
for (let off = 0; off < xml.length; off += CHUNK) parts.push(xml.subarray(off, Math.min(off + CHUNK, xml.length)));

const blocks = parts.map(p => {
  const c = Buffer.from(implode(p.buffer.slice(p.byteOffset, p.byteOffset + p.byteLength), 'ascii', 'large'));
  return { rawSize: p.length, compressed: c };
});

const head = Buffer.from(header, 'ascii');
const total = Buffer.alloc(8); total.writeBigUInt64LE(BigInt(xml.length));
const out = [head, total];
for (const b of blocks) {
  const bh = Buffer.alloc(8);
  bh.writeUInt32LE(b.rawSize, 0);
  bh.writeUInt32LE(b.compressed.length, 4);
  out.push(bh, b.compressed);
}
const buf = Buffer.concat(out);
await fs.writeFile(output, buf);
console.log(JSON.stringify({ output, xmlBytes: xml.length, blocks: blocks.length, containerBytes: buf.length,
                             compressed: blocks.map(b => b.compressed.length) }));
