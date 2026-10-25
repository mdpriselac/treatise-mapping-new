import paragraphsJson from '../data/paragraphs.json';
import sectionsJson from '../data/sections.json';
import passagesJson from '../data/passages.json';
import papersJson from '../data/papers.json';
import citationsJson from '../data/citations.json';
import metaJson from '../data/meta.json';
import { label, sectionLabel, shadeFor } from './labels';

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
  text: string; kind: string; source: 'pattern' | 'quote' | 'llm' | 'manual';
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

export { label, sectionLabel, passageUrl, paperUrl, sourceLabel, verdictText } from './labels';

/** Shade for a weight, as an opacity of the accent colour (log scale). */
export function shade(w: number, max = maxWeight): number {
  return shadeFor(w, max);
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
