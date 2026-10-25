// Pure display helpers shared by the build (lib/data.ts) and client scripts, so the
// browser bundle doesn't pull in the corpus JSON.

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
  manual: 'Read by hand',
};

/** Shade for a weight, as an opacity of the accent colour (log scale). */
export function shadeFor(w: number, max: number): number {
  if (w <= 0) return 0;
  return 0.12 + 0.88 * (Math.log1p(w) / Math.log1p(max));
}

/** One-line verdict on a paper's profile; null when it has no focus score. */
export function verdictText(hasFocus: boolean, focused: boolean, surprising: boolean): string | null {
  if (!hasFocus) return null;
  if (focused && surprising) return 'Focused on personal identity, and cites something almost nobody else does.';
  if (focused) return 'Focused on personal identity, mostly through the passages everyone cites.';
  if (surprising) return 'Ranges beyond the core passages and cites something rare.';
  return 'Ranges beyond the core passages, through commonly cited ones.';
}
