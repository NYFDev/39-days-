import { createHash } from 'node:crypto';
import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT = process.cwd();
const BASE_URL = 'https://nyfholdings.ca';
const SOURCE_DIR = path.join(ROOT, 'aggregation', 'sources');
const DATA_DIR = path.join(ROOT, 'data');
const SEARCH_INDEX = path.join(ROOT, 'search-index.json');
const SITEMAP = path.join(ROOT, 'sitemap.xml');

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

function array(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function unique(values) {
  return [...new Set(array(values))];
}

function stableId(system, locator) {
  const digest = createHash('sha256').update(`${system}:${locator}`).digest('hex').slice(0, 20);
  return `record:${system}:${digest}`;
}

function assertIngestRecord(record, file) {
  const required = ['id', 'schemaVersion', 'visibility', 'kind', 'source', 'title', 'observedAt', 'status'];
  for (const key of required) {
    if (record[key] === undefined || record[key] === null || record[key] === '') {
      throw new Error(`${file}: record missing ${key}`);
    }
  }
  if (record.schemaVersion !== 2) throw new Error(`${file}: ${record.id} is not schemaVersion 2`);
  if (record.visibility !== 'public') {
    throw new Error(`${file}: ${record.id} is ${record.visibility}; non-public records must never enter the public repository`);
  }
  if (!record.source?.name || !record.source?.type) throw new Error(`${file}: ${record.id} has incomplete source provenance`);
}

function expandOutputs(outputs) {
  const expanded = [];
  for (const output of array(outputs)) {
    if (!output?.surface) continue;
    expanded.push(output);
    if (output.surface === 'newsletter') {
      for (const surface of ['east-corner', 'feed', 'activity']) expanded.push({ ...output, surface });
    }
  }

  const seen = new Set();
  return expanded.filter((output) => {
    const key = `${output.surface}|${output.publishedUrl ?? ''}|${output.slug ?? ''}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function normalizeIngestRecord(record, file) {
  assertIngestRecord(record, file);
  return {
    ...record,
    entities: unique(record.entities),
    geography: unique(record.geography),
    lanes: unique(record.lanes),
    topics: unique(record.topics),
    projects: unique(record.projects),
    outputs: expandOutputs(record.outputs),
    verification: record.verification ?? { state: 'unreviewed', checkedAt: null, notes: '' },
    payload: record.payload ?? {},
    provenance: { derivedFrom: unique([...(record.provenance?.derivedFrom ?? []), file]) },
  };
}

function sitemapDates(xml) {
  const dates = new Map();
  const pattern = /<url>\s*<loc>([^<]+)<\/loc>(?:\s*<lastmod>([^<]+)<\/lastmod>)?/g;
  for (const match of xml.matchAll(pattern)) dates.set(match[1], match[2] ?? null);
  return dates;
}

function laneFromSection(section) {
  const text = String(section ?? '').toLowerCase();
  if (text.includes('39 days') || text.includes('living record')) return ['39-days', 'record'];
  if (text.includes('editorial') || text.includes('newsletter') || text.includes('publishing')) {
    return ['enterprise', 'capital', 'culture', 'record'];
  }
  if (text.includes('operation') || text.includes('deployment')) return ['operations', 'record'];
  return ['record'];
}

function routeRecords(searchEntries, routeDates) {
  return searchEntries.map((entry) => {
    const publishedUrl = new URL(entry.url, BASE_URL).href;
    const observedAt = entry.lastModified ?? routeDates.get(publishedUrl) ?? '2026-08-14';
    return {
      id: stableId('repository', `search-index:${entry.url}`),
      schemaVersion: 2,
      visibility: 'public',
      kind: 'artifact',
      source: {
        name: 'NYF Holdings repository',
        type: 'repository',
        canonicalUrl: publishedUrl,
        externalId: `search-index:${entry.url}`,
        publishedAt: observedAt,
        retrievedAt: null,
      },
      title: entry.title,
      summary: entry.description ?? '',
      context: `Public ${entry.section ?? 'site'} artifact in the NYF record.`,
      observedAt,
      entities: ['NYF Holdings'],
      geography: [],
      lanes: laneFromSection(entry.section),
      topics: unique(entry.keywords),
      projects: [],
      status: 'published',
      verification: {
        state: 'verified',
        checkedAt: null,
        notes: 'Canonical route is present in the public search inventory.',
      },
      outputs: [{ surface: 'site', slug: entry.url, publishedUrl }],
      payload: { section: entry.section ?? null },
      provenance: { derivedFrom: ['search-index.json'] },
    };
  });
}

function mergeRecord(existing, incoming) {
  if (!existing) return incoming;
  const existingUrl = existing.source?.canonicalUrl ?? null;
  const incomingUrl = incoming.source?.canonicalUrl ?? null;
  if (existingUrl && incomingUrl && existingUrl !== incomingUrl) {
    throw new Error(`record id collision: ${existing.id} points to both ${existingUrl} and ${incomingUrl}`);
  }

  const outputMap = new Map();
  for (const output of [...array(existing.outputs), ...array(incoming.outputs)]) {
    const key = `${output.surface}|${output.publishedUrl ?? ''}|${output.slug ?? ''}`;
    outputMap.set(key, output);
  }

  return {
    ...existing,
    source: {
      ...existing.source,
      retrievedAt: incoming.source?.retrievedAt ?? existing.source?.retrievedAt ?? null,
    },
    summary: existing.summary || incoming.summary || '',
    context: existing.context || incoming.context || '',
    entities: unique([...array(existing.entities), ...array(incoming.entities)]),
    geography: unique([...array(existing.geography), ...array(incoming.geography)]),
    lanes: unique([...array(existing.lanes), ...array(incoming.lanes)]),
    topics: unique([...array(existing.topics), ...array(incoming.topics)]),
    projects: unique([...array(existing.projects), ...array(incoming.projects)]),
    outputs: [...outputMap.values()],
    payload: { ...(existing.payload ?? {}), ...(incoming.payload ?? {}) },
    provenance: {
      derivedFrom: unique([
        ...array(existing.provenance?.derivedFrom),
        ...array(incoming.provenance?.derivedFrom),
      ]),
    },
  };
}

function mergeRecords(records) {
  const byIdentity = new Map();
  for (const record of records) {
    const identity = record.source?.canonicalUrl ? `url:${record.source.canonicalUrl}` : `id:${record.id}`;
    byIdentity.set(identity, mergeRecord(byIdentity.get(identity), record));
  }

  const ids = new Set();
  const merged = [...byIdentity.values()];
  for (const record of merged) {
    if (ids.has(record.id)) throw new Error(`duplicate record id after merge: ${record.id}`);
    ids.add(record.id);
  }
  return merged;
}

function compactRecord(record) {
  return {
    id: record.id,
    kind: record.kind,
    title: record.title,
    summary: record.summary ?? '',
    observedAt: record.observedAt,
    source: record.source?.name ?? null,
    sourceUrl: record.source?.canonicalUrl ?? null,
    lanes: array(record.lanes),
    topics: array(record.topics),
    geography: array(record.geography),
    outputs: array(record.outputs),
  };
}

function generationTime(records) {
  const values = records.flatMap((record) => [
    record.source?.retrievedAt,
    record.source?.publishedAt,
    record.observedAt,
    ...array(record.outputs).map((output) => output.publishedAt),
  ]).filter(Boolean);
  const parsed = values.map((value) => Date.parse(value)).filter(Number.isFinite);
  return parsed.length ? new Date(Math.max(...parsed)).toISOString() : '1970-01-01T00:00:00.000Z';
}

async function writeJson(file, payload) {
  const text = `${JSON.stringify(payload, null, 2)}\n`;
  const current = await fs.readFile(file, 'utf8').catch(() => null);
  if (current !== text) await fs.writeFile(file, text);
}

const sourceFiles = await walk(SOURCE_DIR);
const sourceRecords = [];
for (const file of sourceFiles) {
  const parsed = JSON.parse(await fs.readFile(file, 'utf8'));
  const batch = Array.isArray(parsed) ? parsed : [parsed];
  const relative = path.relative(ROOT, file);
  for (const record of batch) sourceRecords.push(normalizeIngestRecord(record, relative));
}

const searchEntries = JSON.parse(await fs.readFile(SEARCH_INDEX, 'utf8'));
if (!Array.isArray(searchEntries)) throw new Error('search-index.json must contain an array');
const routeDates = sitemapDates(await fs.readFile(SITEMAP, 'utf8'));
const records = mergeRecords([...sourceRecords, ...routeRecords(searchEntries, routeDates)])
  .sort((a, b) => String(b.observedAt).localeCompare(String(a.observedAt)) || a.id.localeCompare(b.id));
const publicRecords = records.filter((record) => record.visibility === 'public' && record.status === 'published');
const generatedAt = generationTime(publicRecords);

await fs.mkdir(DATA_DIR, { recursive: true });
await writeJson(path.join(DATA_DIR, 'records.json'), {
  schemaVersion: 2,
  generatedAt,
  count: publicRecords.length,
  records: publicRecords,
});
await writeJson(path.join(DATA_DIR, 'public-index.json'), {
  schemaVersion: 2,
  generatedAt,
  count: publicRecords.length,
  records: publicRecords.map(compactRecord),
});
await writeJson(path.join(DATA_DIR, 'public-records.json'), {
  schemaVersion: 2,
  generatedAt,
  count: publicRecords.length,
  records: publicRecords,
});

console.log(`NYF aggregation: ${sourceRecords.length} ingested sources + ${searchEntries.length} public routes = ${publicRecords.length} canonical public records.`);
