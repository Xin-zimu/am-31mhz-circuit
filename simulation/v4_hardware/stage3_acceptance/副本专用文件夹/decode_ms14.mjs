// Decode a Multisim .ms14 container to XML without touching the source.
import fs from 'node:fs/promises';
import { explode } from 'file:///D:/ewbwork/node_modules/node-pkware/dist/simple/index.js';
const [input, output] = process.argv.slice(2);
const src = await fs.open(input, 'r');
const dst = await fs.open(output, 'wx');
let pos = 0;
async function read(n) {
  const b = Buffer.alloc(n);
  const r = await src.read(b, 0, n, pos);
  if (r.bytesRead !== n) throw Error('Truncated container');
  pos += n;
  return b;
}
try {
  const head = await read(43);
  const headers = ['MSMCompressedElectronicsWorkbenchXML', 'CompressedElectronicsWorkbenchXML'];
  const h = headers.find(v => head.subarray(0, v.length).toString('ascii') === v);
  if (!h) throw Error('Unknown container: ' + head.subarray(0, 40).toString('ascii'));
  pos = h.length;
  const total = Number((await read(8)).readBigUInt64LE());
  let done = 0, blocks = 0;
  while (done < total) {
    const bh = await read(8);
    const rawSize = bh.readUInt32LE(0), compressedSize = bh.readUInt32LE(4);
    const compressed = await read(compressedSize);
    const raw = Buffer.from(explode(compressed.buffer.slice(compressed.byteOffset, compressed.byteOffset + compressed.byteLength)));
    if (raw.length !== rawSize) throw Error('Block length mismatch');
    await dst.write(raw);
    done += raw.length; blocks++;
  }
  if (done !== total) throw Error('Container size mismatch');
  console.log(JSON.stringify({ input, output, decoded_bytes: done, blocks, header: h }));
} finally { await src.close(); await dst.close(); }
