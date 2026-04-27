// Spotify-inspired palette. Body text reads on near-black; green for accents,
// underlines, and data marks. We use a small auxiliary palette for the
// over/under-confident comparisons so colour itself becomes a quick legend.

export const palette = {
  bg: '#0d0d0d',
  bgAlt: '#161616',
  surface: '#1f1f1f',
  ink: '#e8e8e3',
  inkSoft: '#a7a7a2',
  rule: '#2a2a2a',
  green: '#1db954',
  greenSoft: '#1ed760',
  greenDim: '#147a37',
  // Comparison hues — reachable from a colourblind-friendly set on dark bg
  wellCalibrated: '#1db954',
  overConfident: '#ff7a59',
  underConfident: '#7ab7ff',
  // Calibration methods get their own distinct hues so raw/platt/isotonic
  // never get confused on a single chart
  raw: '#ff7a59',
  platt: '#1ed760',
  isotonic: '#f4b942',
  diagonal: '#a7a7a2'
};

export const fonts = {
  serif: '"Fraunces", "Iowan Old Style", Georgia, serif',
  sans: '"Inter", system-ui, sans-serif',
  mono: '"JetBrains Mono", ui-monospace, monospace'
};
