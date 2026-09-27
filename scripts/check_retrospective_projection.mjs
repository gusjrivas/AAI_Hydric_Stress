import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const projected = JSON.parse(readFileSync(resolve(root, 'frontend/public/retrospective-2023.json'), 'utf8'));
assert.equal(projected.schema_version, 'defense-retrospective-aggregate.v1');
assert.deepEqual(Object.keys(projected).sort(), [
  'display_probability', 'horizons', 'label', 'limitations', 'period', 'schema_version', 'source_sha256',
].sort());
assert.equal(projected.display_probability, false);
const sourceDir = process.argv[2];
if (sourceDir) {
  for (const name of ['ui_summary.json', 'metrics.json']) {
    const digest = createHash('sha256').update(readFileSync(resolve(sourceDir, name))).digest('hex');
    assert.equal(digest, projected.source_sha256[name], `${name} hash`);
  }
}
const serialized = JSON.stringify(projected);
assert.doesNotMatch(serialized, /[A-Z]:\\|\.parquet|\.joblib|predictions\.csv|password|api[_-]?key/i);
const rows = (name) => {
  const lines = readFileSync(resolve(root, 'docs/research/tables/ensemble-retrospective-2023', name), 'utf8').trim().split(/\r?\n/);
  const headers = lines.shift().split(',');
  return lines.map((line) => Object.fromEntries(line.split(',').map((value, i) => [headers[i], value])));
};
let checked = 0;
for (const source of rows('classification_metrics.csv')) {
  const target = projected.horizons[source.horizon_days].metrics[source.method];
  assert.ok(target, `${source.horizon_days}/${source.method}`);
  assert.equal(target.n, Number(source.n));
  assert.equal(target.false_alerts, Number(source.fp));
  assert.equal(target.missed_positive_days, Number(source.fn));
  for (const key of ['precision', 'recall', 'f1', 'mcc', 'average_precision', 'brier']) {
    const metric = target[key];
    if (!metric) {
      assert.equal(source[`${key}_status`], 'not_applicable');
      assert.equal(source[`${key}_value`], '');
      continue;
    }
    assert.equal(metric.status, source[`${key}_status`]);
    assert.equal(metric.value, source[`${key}_value`] ? Number(source[`${key}_value`]) : null);
  }
  checked++;
}
for (const source of rows('episode_onset.csv')) {
  const episode = projected.horizons[source.horizon_days].episodes.methods[source.method];
  assert.equal(episode.detected_episodes, Number(source.detected_episodes));
  assert.equal(episode.evaluable_episodes, Number(source.evaluable_episodes));
}
for (const source of rows('paired_mcc_comparisons.csv')) {
  const comparison = projected.horizons[source.horizon_days].uncertainty[source.comparison];
  assert.equal(comparison.status, source.status);
  assert.deepEqual(comparison.delta_mcc_ci95, source.ci95_lower ? [Number(source.ci95_lower), Number(source.ci95_upper)] : null);
}
assert.equal(checked, 18);
console.log(`Projection matches ${checked} method/horizon rows, episode counts and paired MCC intervals.`);
