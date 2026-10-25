import type { APIRoute } from 'astro';
import { sections, paragraphs, meta } from '../../lib/data';

// The Treatise's book / part / section / paragraph structure, for drawing the map client-side
// (the upload profile page). Paragraphs are [id, sbn, core, n] with n = corpus papers reaching it.
export const GET: APIRoute = () => {
  const bySection = new Map<string, [string, string, boolean, number][]>();
  for (const p of paragraphs) {
    if (!bySection.has(p.section)) bySection.set(p.section, []);
    bySection.get(p.section)!.push([p.id, p.sbn, p.core, p.n]);
  }
  return new Response(JSON.stringify({
    books: meta.books,
    themes: meta.themes,
    sections: sections.map((s) => ({
      id: s.id, book: s.book, title: s.title, part: s.part, partTitle: s.partTitle,
      paras: bySection.get(s.id) ?? [],
    })),
  }), { headers: { 'content-type': 'application/json' } });
};
