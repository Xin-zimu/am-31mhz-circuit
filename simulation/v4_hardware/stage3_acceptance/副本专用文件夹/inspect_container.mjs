import fs from 'node:fs/promises';
const file = process.argv[2];
const buf = await fs.readFile(file);
const headers = ['MSMCompressedElectronicsWorkbenchXML','CompressedElectronicsWorkbenchXML'];
const h = headers.find(v => buf.subarray(0, v.length).toString('ascii') === v);
let pos = h.length;
const total = Number(buf.readBigUInt64LE(pos)); pos += 8;
const blocks = [];
while (pos < buf.length) {
  const rawSize = buf.readUInt32LE(pos), comp = buf.readUInt32LE(pos+4); pos += 8;
  blocks.push({rawSize, comp});
  pos += comp;
}
console.log(JSON.stringify({file, header:h, total, blocks, endPos: pos, size: buf.length}, null, 1));
