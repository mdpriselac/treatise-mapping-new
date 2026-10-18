import * as Plot from '@observablehq/plot';

export interface SlimPaper {
  id: string; name: string; title: string; year: number | null; cites: number;
  focus: number | null; surprise: number | null; themes: number[] | null;
  weights: Record<string, number>;
}

let cache: Promise<SlimPaper[]> | null = null;
export function loadPapers() {
  cache ??= fetch('/data/papers.json').then((r) => r.json());
  return cache;
}

/** Resolve a CSS custom property, since Plot needs literal colours. */
export function css(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Nudge labels apart vertically (in data units) when their dots sit close together. */
function spread(points: SlimPaper[]) {
  const out = points.map((p) => ({ ...p, ly: p.surprise! })).sort((a, b) => b.ly - a.ly);
  for (let i = 1; i < out.length; i++) {
    for (let j = 0; j < i; j++) {
      if (Math.abs(out[i].focus! - out[j].focus!) < 0.12 && out[j].ly - out[i].ly < 0.13) out[i].ly = out[j].ly - 0.13;
    }
  }
  return out;
}

/** Focus × surprise scatter of the papers with 10+ citations. */
export function scatter(el: HTMLElement, papers: SlimPaper[], opts: { highlight?: string; focusMin: number; surpriseMin: number }) {
  const data = papers.filter((p) => p.focus !== null && p.surprise !== null);
  const { highlight, focusMin, surpriseMin } = opts;
  const quad = (p: SlimPaper) => p.focus! >= focusMin && p.surprise! >= surpriseMin;
  const width = Math.min(el.clientWidth || 720, 900);
  const ink3 = css('--ink-3'), accent = css('--accent'), blue = css('--accent-2'), rule = css('--rule');
  const chart = Plot.plot({
    width, height: Math.max(320, Math.min(460, width * 0.6)),
    marginLeft: 48, marginBottom: 44, marginRight: 16,
    style: { background: 'transparent', color: css('--ink-2'), fontSize: '12px' },
    x: { label: 'Focus: share of citations on the 15 core paragraphs →', domain: [0, 1], tickFormat: '.0%', grid: true },
    y: { label: '↑ Surprise of rarest precise citation', grid: true },
    marks: [
      Plot.rect([0], { x1: focusMin, x2: 1, y1: surpriseMin, y2: Math.max(...data.map((d) => d.surprise!)) + 0.3, fill: accent, fillOpacity: 0.06 }),
      Plot.ruleX([focusMin], { stroke: rule, strokeDasharray: '4,3' }),
      Plot.ruleY([surpriseMin], { stroke: rule, strokeDasharray: '4,3' }),
      Plot.dot(data, {
        x: 'focus', y: 'surprise', r: (d: SlimPaper) => 2.5 + Math.sqrt(d.cites) / 2,
        fill: (d: SlimPaper) => (d.id === highlight ? blue : quad(d) ? accent : ink3),
        fillOpacity: (d: SlimPaper) => (highlight && d.id !== highlight ? 0.35 : 0.8),
        stroke: css('--surface'), strokeWidth: 0.8,
        href: (d: SlimPaper) => `/papers/${d.id}/`,
        title: (d: SlimPaper) => `${d.name}: ${d.title}\nfocus ${Math.round(d.focus! * 100)}%, surprise ${d.surprise!.toFixed(2)}, ${d.cites} citations`,
      }),
      Plot.text(spread(data.filter((d) => (highlight ? d.id === highlight : quad(d)))), {
        x: 'focus', y: 'ly', text: 'name', dx: 7, textAnchor: 'start', fontSize: 11,
        fill: highlight ? blue : accent, stroke: css('--bg'), strokeWidth: 3, paintOrder: 'stroke',
      }),
    ],
  });
  el.replaceChildren(chart);
}
