import fs from 'node:fs/promises';
import { implode } from 'file:///D:/ewbwork/node_modules/node-pkware/dist/simple/index.js';
const [inputXml, output, ct, ds] = process.argv.slice(2);
const xml = await fs.readFile(inputXml);
const CHUNK = 900000;
const parts = [];
for (let off = 0; off < xml.length; off += CHUNK) parts.push(xml.subarray(off, Math.min(off + CHUNK, xml.length)));
const blocks = parts.map(p => ({ rawSize: p.length, compressed: Buffer.from(implode(p.buffer.slice(p.byteOffset, p.byteOffset+p.byteLength), ct, ds)) }));
const out = [Buffer.from('MSMCompressedElectronicsWorkbenchXML','ascii')];
const total = Buffer.alloc(8); total.writeBigUInt64LE(BigInt(xml.length)); out.push(total);
for (const b of blocks) { const bh = Buffer.alloc(8); bh.writeUInt32LE(b.rawSize,0); bh.writeUInt32LE(b.compressed.length,4); out.push(bh, b.compressed); }
await fs.writeFile(output, Buffer.concat(out));
console.log(JSON.stringify({output, ct, ds, sizes: blocks.map(b=>b.compressed.length)}));
