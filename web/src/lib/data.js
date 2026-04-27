import { base } from '$app/paths';

const cache = new Map();

async function fetchJson(name) {
  if (cache.has(name)) return cache.get(name);
  const res = await fetch(`${base}/data/${name}`);
  if (!res.ok) throw new Error(`Failed to load ${name}: ${res.status}`);
  const json = await res.json();
  cache.set(name, json);
  return json;
}

export const loadHoldout = () => fetchJson('holdout.json');
export const loadReliability = () => fetchJson('reliability.json');
export const loadMetrics = () => fetchJson('metrics.json');
export const loadCalibrated = () => fetchJson('calibrated.json');
export const loadSampleRows = () => fetchJson('sample_rows.json');
