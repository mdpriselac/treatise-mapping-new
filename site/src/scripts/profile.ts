// Client-side rendering of an uploaded paper's profile, matching papers/[id].astro and
// TreatiseMap.astro (same classes, same shading), from /data/treatise.json.
import { label, sectionLabel, passageUrl, paperUrl, sourceLabel, shadeFor, verdictText } from '../lib/labels';
import { el, link } from './upload';

export interface Treatise {
  books: Record<string, string>;
  themes: { id: string; name: string }[];
  sections: { id: string; book: string; title: string; part: string | null; partTitle: string;
    paras: [string, string, boolean, number][] }[];
}
export interface Profile {
  cites: number; weights: Record<string, number>; sources: Record<string, number>;
  focus: number | null; surprise: number | null; focused?: boolean; surprising?: boolean;
  rare: { paragraph: string; surprise: number }[];
  themes: Record<string, number> | null;
  nearest: { id: string; similarity: number; title: string; author: string; year: number | null }[];
}
export interface UploadCitation {
  text: string; kind: string; source: 'pattern' | 'quote' | 'llm'; context: string; weights: Record<string, number>;
}

let cache: Promise<Treatise> | null = null;
export function loadTreatise(): Promise<Treatise> {
  cache ??= fetch('/data/treatise.json').then((r) => {
    if (!r.ok) throw new Error(String(r.status));
    return r.json();
  });
  cache.catch(() => { cache = null; });
  return cache;
}

/** Paragraph lookups built once per Treatise load. */
const indexes = new WeakMap<Treatise, { order: Map<string, number>; section: Map<string, string>; n: Map<string, number> }>();
function index(t: Treatise) {
  let ix = indexes.get(t);
  if (!ix) {
    ix = { order: new Map(), section: new Map(), n: new Map() };
    for (const s of t.sections) for (const [id, , , n] of s.paras) {
      ix.order.set(id, ix.order.size); ix.section.set(id, s.id); ix.n.set(id, n);
    }
    indexes.set(t, ix);
  }
  return ix;
}

/** Paragraph ids a citation maps to, in Treatise order. */
export function parasOf(t: Treatise, c: UploadCitation) {
  const { order } = index(t);
  return Object.keys(c.weights).sort((a, b) => (order.get(a) ?? 1e9) - (order.get(b) ?? 1e9));
}

/** Same as rangeLabel in lib/data.ts. */
export function rangeLabel(t: Treatise, ids: string[]) {
  if (ids.length === 1) return label(ids[0]);
  const { section } = index(t);
  const secs = new Set(ids.map((i) => section.get(i) ?? i));
  if (secs.size === 1) return `${sectionLabel([...secs][0])} (${ids.length} paragraphs)`;
  return `${label(ids[0])} to ${label(ids[ids.length - 1])} (${ids.length} paragraphs)`;
}

// ---------------------------------------------------------------- pieces
export function tiles(box: HTMLElement, p: Profile) {
  const tile = (v: string, k: string) => {
    const d = el('div', 'tile');
    d.append(el('div', 'v', v), el('div', 'k', k));
    return d;
  };
  box.replaceChildren(
    tile(String(p.cites), 'citations of the Treatise'),
    tile(String(Object.keys(p.weights).length), 'paragraphs reached'),
    tile(p.focus !== null ? `${Math.round(p.focus * 100)}%` : '–', 'focus on the core paragraphs'),
    tile(p.surprise !== null ? p.surprise.toFixed(2) : '–', 'surprise of rarest citation'),
  );
}

export function verdict(p: Profile) {
  return verdictText(p.focus !== null, !!p.focused, !!p.surprising);
}

/** Same as ThemeBar.astro with showKey. */
export function themeBar(box: HTMLElement, t: Treatise, p: Profile) {
  if (!p.themes) {
    box.replaceChildren(el('span', 'muted small', 'Too few citations outside 1.4.6 and the Appendix'));
    return;
  }
  const shares = t.themes.map((th) => p.themes![th.id] ?? 0);
  const desc = t.themes.map((th, i) => `${th.name} ${Math.round(shares[i] * 100)}%`);
  const bar = el('div', 'themebar');
  bar.setAttribute('role', 'img');
  bar.setAttribute('aria-label', desc.join(', '));
  bar.title = desc.join('\n');
  shares.forEach((s, i) => {
    const sp = el('span');
    sp.style.width = `${(s * 100).toFixed(1)}%`;
    sp.style.background = `var(--t${i})`;
    bar.append(sp);
  });
  const key = el('div', 'themekey');
  key.style.marginTop = '.5rem';
  t.themes.forEach((th, i) => {
    const s = el('span');
    const sw = el('span', 'sw');
    sw.style.background = `var(--t${i})`;
    s.append(sw, `${th.name} ${Math.round(shares[i] * 100)}%`);
    key.append(s);
  });
  box.replaceChildren(bar, key);
}

export function rareList(ul: HTMLElement, t: Treatise, p: Profile) {
  const { n } = index(t);
  ul.replaceChildren(...p.rare.map((r) => {
    const li = el('li');
    const k = n.get(r.paragraph) ?? 0;
    li.append(link(passageUrl(r.paragraph), label(r.paragraph)), ' ',
      el('span', 'muted small', `surprise ${r.surprise.toFixed(2)} · ${k === 0 ? 'no corpus paper reaches it' : k === 1 ? '1 corpus paper reaches it' : `${k} corpus papers reach it`}`));
    return li;
  }));
}

export function nearestList(ul: HTMLElement, p: Profile) {
  ul.replaceChildren(...p.nearest.map((q) => {
    const li = el('li');
    const surname = q.author.split(',')[0].trim();
    li.append(link(paperUrl(q.id), `${surname} ${q.year ?? 'n.d.'}`), ' ',
      el('span', 'muted small', `similarity ${q.similarity.toFixed(2)}`), el('br'), el('span', 'small', q.title));
    return li;
  }));
}

/** Client-side TreatiseMap: same DOM, classes and shading as TreatiseMap.astro. */
export function treatiseMap(box: HTMLElement, t: Treatise, weights: Record<string, number>, onlyCited = true) {
  const w = (pid: string) => weights[pid] ?? 0;
  let max = 0;
  for (const s of t.sections) for (const [id] of s.paras) max = Math.max(max, w(id));
  const fmt = (x: number) => (x >= 10 ? x.toFixed(0) : x.toFixed(1));
  const tip = (pid: string, sbn: string) => {
    const x = w(pid);
    return `${label(pid)}${sbn ? ` · SBN ${sbn}` : ''} · ${x ? `${fmt(x)} cite weight` : 'not cited'}`;
  };

  const root = el('div', 'tmap');
  root.dataset.max = String(max);
  let book: string | null = null, part: string | null | undefined, section: HTMLElement | null = null;
  for (const sec of t.sections) {
    const total = sec.paras.reduce((s, [id]) => s + w(id), 0);
    if (onlyCited && total === 0) continue;
    if (!section || sec.book !== book) {
      book = sec.book; part = undefined;
      section = el('section');
      section.append(el('div', 'book', t.books[sec.book] ?? sec.book));
      root.append(section);
    }
    if (sec.part !== part) {
      part = sec.part;
      if (sec.part) section.append(el('div', 'part', `Part ${sec.part.split('.')[1]}: ${sec.partTitle}`));
    }
    const row = el('div', 'row');
    const lbl = el('div', 'lbl');
    lbl.title = `${sectionLabel(sec.id)} ${sec.title}`;
    if (sec.part) lbl.append(el('b', '', sec.id), ` ${sec.title}`);
    const cells = el('div', 'cells');
    for (const [id, sbn, core] of sec.paras) {
      const a = shadeFor(w(id), max);
      const c = link(passageUrl(id), '', ['c', /n\d+$/.test(id) ? 'note' : '', core ? 'core' : ''].join(' ').trim());
      c.dataset.id = id;
      c.title = tip(id, sbn);
      c.setAttribute('aria-label', tip(id, sbn));
      if (a) c.style.background = `rgba(var(--accent-rgb), ${a.toFixed(3)})`;
      cells.append(c);
    }
    row.append(lbl, cells);
    section.append(row);
  }
  box.replaceChildren(root);
}

function marked(ctx: string, text: string) {
  const j = ctx.indexOf(text);
  return j < 0 ? [ctx, '', ''] : [ctx.slice(0, j), text, ctx.slice(j + text.length)];
}

/** The evidence table, one checkbox per citation. onToggle gets the full excluded list. */
export function evidence(tbody: HTMLElement, t: Treatise, cites: UploadCitation[], excluded: number[],
                         onToggle: (excluded: number[], box: HTMLInputElement) => void) {
  const off = new Set(excluded);
  const boxes: HTMLInputElement[] = [];
  tbody.replaceChildren(...cites.map((c, i) => {
    const tr = el('tr');
    tr.classList.toggle('off', off.has(i));
    const use = el('td', 'use');
    const box = el('input');
    box.type = 'checkbox';
    box.checked = !off.has(i);
    box.setAttribute('aria-label', `Count the citation “${c.text}”`);
    box.title = 'Untick if this isn’t a citation of the Treatise';
    box.addEventListener('change', () => {
      tr.classList.toggle('off', !box.checked);
      onToggle(boxes.flatMap((b, k) => (b.checked ? [] : [k])), box);
    });
    boxes.push(box);
    use.append(box);

    const as = el('td');
    as.append(el('span', 'mono', c.text), el('br'), el('span', `badge ${c.source}`, sourceLabel[c.source] ?? c.source));

    const ids = parasOf(t, c);
    const maps = el('td', 'small');
    if (ids.length) maps.append(link(passageUrl(ids[0]), ids.length === 1 ? label(ids[0]) : rangeLabel(t, ids)));

    const [a, b, z] = marked(c.context, c.text);
    const ctx = el('td', 'snippet small');
    ctx.append(`…${a}`, el('mark', '', b), `${z}…`);
    tr.append(use, as, maps, ctx);
    return tr;
  }));
  return boxes;
}
