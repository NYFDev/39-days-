import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const SOURCE_DIR = path.join(ROOT, 'aggregation', 'sources');
const DATA_DIR = path.join(ROOT, 'data');

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...await walk(full));
    else if (entry.isFile() && entry.name.endsWith('.json')) out.push(full);
  }
  return out.sort();
}

function assertRecord(record, file) {
  const required = ['id', 'schemaVersion', 'visibility', 'kind', 'source', 'title', 'observedAt', 'status'];
  for (const key of required) {
    if (record[key] === undefined || record[key] === null || record[key] === '') {
      throw new Error(`${file}: record missing ${key}`);
    }
  }
  if (record.schemaVersion !== 2) throw new Error(`${file}: ${record.id} is not schemaVersion 2`);
  if (!['public', 'internal', 'private'].includes(record.visibility)) throw new Error(`${file}: ${record.id} has invalid visibility`);
  if (!record.source?.name || !record.source?.type) throw new Error(`${file}: ${record.id} has incomplete source provenance`);
}

const files = await walk(SOURCE_DIR);
const records = [];
for (const file of files) {
  const parsed = JSON.parse(await fs.readFile(file, 'utf8'));
  const batch = Array.isArray(parsed) ? parsed : [parsed];
  for (const record of batch) {
    assertRecord(record, path.relative(ROOT, file));
    records.push(record);
  }
}

const ids = new Set();
const urls = new Map();
for (const record of records) {
  if (ids.has(record.id)) throw new Error(`duplicate record id: ${record.id}`);
  ids.add(record.id);

  const url = record.source?.canonicalUrl;
  if (url) {
    if (urls.has(url)) throw new Error(`duplicate canonical URL: ${url} (${urls.get(url)} and ${record.id})`);
    urls.set(url, record.id);
  }
}

const publicRecords = records
  .filter(record => record.visibility === 'public')
  .sort((a, b) => String(b.observedAt).localeCompare(String(a.observedAt)) || a.id.localeCompare(b.id));

const publicIndex = publicRecords.map(record => ({
  id: record.id,
  kind: record.kind,
  title: record.title,
  observedAt: record.observedAt,
  source: record.source.name,
  sourceUrl: record.source.canonicalUrl ?? null,
  lanes: record.lanes ?? [],
  topics: record.topics ?? [],
  geography: record.geography ?? [],
  outputs: record.outputs ?? []
}));

await fs.mkdir(DATA_DIR, { recursive: true });
await fs.writeFile(path.join(DATA_DIR, 'records.json'), JSON.stringify({
  schemaVersion: 2,
  generatedAt: new Date().toISOString(),
  count: publicRecords.length,
  records: publicRecords
}, null, 2) + '\n');
await fs.writeFile(path.join(DATA_DIR, 'public-index.json'), JSON.stringify({
  schemaVersion: 2,
  generatedAt: new Date().toISOString(),
  count: publicIndex.length,
  records: publicIndex
}, null, 2) + '\n');

console.log(`NYF aggregation: ${records.length} canonical records, ${publicRecords.length} public records, ${files.length} source batches.`);
