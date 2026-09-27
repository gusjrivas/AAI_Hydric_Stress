// Projection of aggregate evidence only. No dated predictions are read.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const [sourceDir, destination] = process.argv.slice(2);
if (!sourceDir || !destination) throw new Error('Usage: node scripts/project_retrospective_ui.mjs SOURCE_DIR OUTPUT_JSON');
const read = (name) => {
  const bytes = readFileSync(join(sourceDir, name));
  return { data: JSON.parse(bytes.toString('utf8')), sha256: createHash('sha256').update(bytes).digest('hex') };
};
const summary = read('ui_summary.json');
const metrics = read('metrics.json');
if (summary.data.schema_version !== 'forecast-evidence-ui-summary.v1' ||
    metrics.data.schema_version !== 'ensemble-retrospective-evaluation-metrics.v1') {
  throw new Error('Unknown retrospective evidence schema');
}
const expected = {
  'ui_summary.json': '2b640b360671e03fac9f8223380395667eb8d62df9845d39a2f9f508ce660998',
  'metrics.json': '6a6a31d35196313061aa4363c98d422f4d1446a9f996d7af51cd93f762e67732',
};
if (summary.sha256 !== expected['ui_summary.json'] || metrics.sha256 !== expected['metrics.json']) {
  throw new Error('Canonical aggregate hash mismatch');
}
const horizons = {};
for (const h of ['1', '2', '3']) {
  const s = summary.data.horizons[h];
  const m = metrics.data.horizons[h];
  if (!s || !m || s.support.common_cases !== m.common_cases) throw new Error(`Horizon ${h} differs between sources`);
  horizons[h] = {
    support: s.support,
    metrics: Object.fromEntries(Object.entries(s.metrics).map(([method, row]) => {
      const { reliability_bins: _bins, ...withoutBins } = row;
      return [method, withoutBins];
    })),
    episodes: s.episodes,
    uncertainty: m.uncertainty.comparisons,
  };
}
const projection = {
  schema_version: 'defense-retrospective-aggregate.v1',
  source_sha256: expected,
  period: summary.data.period,
  label: summary.data.label,
  display_probability: summary.data.display_probability,
  limitations: summary.data.limitations,
  horizons,
};
writeFileSync(destination, JSON.stringify(projection, null, 2) + '\n');
