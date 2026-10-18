import paragraphsJson from '../data/paragraphs.json';
import sectionsJson from '../data/sections.json';
import passagesJson from '../data/passages.json';
import papersJson from '../data/papers.json';
import citationsJson from '../data/citations.json';
import metaJson from '../data/meta.json';

export interface Paragraph {
  id: string; book: string; section: string; sbn: string;
  w: number; n: number; core: boolean; rare: boolean;
}
export interface Section { id: string; book: string; title: string; part: string | null; partTitle: string }
export interface Passage {
  text: string; citers: [string, number][]; rareScore: number | null; rareN: number | null; focusedCiters: string[];
}
export interface Paper {
  id: string; author: string; title: string; year: number | null; venue: string;
  volume: string; issue: string; pages: string; editor: string;
  cites: number; sources: Record<string, number>; weights: Record<string, number>;
  focus: number | null; surprise: number | null; topRare: string[];
  themes: number[] | null; neighbours: { id: string; sim: number }[];
}
export interface Citation {
  text: string; kind: string; source: 'pattern' | 'quote' | 'llm';
  context: string; paras: string[]; precise: boolean;
}

export const paragraphs = paragraphsJson as Paragraph[];
export const sections = sectionsJson as Section[];
export const passages = passagesJson as unknown as Record<string, Passage>;
export const papers = (papersJson as Paper[]).slice().sort(
  (a, b) => a.author.localeCompare(b.author) || (a.year ?? 0) - (b.year ?? 0));
export const citations = citationsJson as unknown as Record<string, Citation[]>;
export const meta = metaJson as {
  themes: { id: string; name: string }[]; books: Record<string, string>; core: string[];
  focusMin: number; surpriseMin: number;
  totals: { papers: number; cites: number; paragraphs: number; cited: number; scored: number };
};

export const paperById = new Map(papers.map((p) => [p.id, p]));
export const paragraphById = new Map(paragraphs.map((p) => [p.id, p]));
export const sectionById = new Map(sections.map((s) => [s.id, s]));
export const maxWeight = Math.max(...paragraphs.map((p) => p.w));

/** "Ainslie 2008" */
export function shortName(p: Paper): string {
  const surname = p.author.split(',')[0].trim();
  return `${surname} ${p.year ?? 'n.d.'}`;
}

/** Display form of a Norton id: T 1.4.6.4, T 1.1.1.1 n2, App. 20, Abs. 10 */
export function label(id: string): string {
  if (id.startsWith('App')) return `App. ${id.slice(4)}`;
  if (id.startsWith('Abs')) return `Abs. ${id.slice(3)}`;
  const m = id.match(/^(.*?)(n\d+)$/);
  return m ? `T ${m[1]} ${m[2]}` : `T ${id}`;
}

export function sectionLabel(id: string): string {
  if (id === '0') return 'Introduction';
  if (id === 'App') return 'Appendix';
  if (id === 'Abs') return 'Abstract';
  return `T ${id}`;
}

export function passageUrl(id: string) { return `/passages/${id}/`; }
export function paperUrl(id: string) { return `/papers/${id}/`; }

export const sourceLabel: Record<string, string> = {
  pattern: 'Citation pattern',
  quote: 'Quote matched to the Treatise',
  llm: 'Checked by model',
};

/** Shade for a weight, as an opacity of the accent colour (log scale). */
export function shade(w: number, max = maxWeight): number {
  if (w <= 0) return 0;
  return 0.12 + 0.88 * (Math.log1p(w) / Math.log1p(max));
}

/** Collapse a run of paragraph ids into a short label for the evidence table. */
export function rangeLabel(ids: string[]): string {
  if (ids.length === 1) return label(ids[0]);
  const secs = new Set(ids.map((i) => paragraphById.get(i)?.section ?? i));
  if (secs.size === 1) return `${sectionLabel([...secs][0])} (${ids.length} paragraphs)`;
  return `${label(ids[0])} to ${label(ids[ids.length - 1])} (${ids.length} paragraphs)`;
}

/** Citations of one paragraph, grouped by paper, with whether the cite was precise. */
export function citationsOf(pid: string) {
  const out: { paper: Paper; cites: Citation[] }[] = [];
  for (const p of papers) {
    const cs = (citations[p.id] ?? []).filter((c) => c.paras.includes(pid));
    if (cs.length) out.push({ paper: p, cites: cs });
  }
  return out;
}

export function isFocused(p: Paper) { return p.focus !== null && p.focus >= meta.focusMin; }
export function isSurprising(p: Paper) { return p.surprise !== null && p.surprise >= meta.surpriseMin; }
