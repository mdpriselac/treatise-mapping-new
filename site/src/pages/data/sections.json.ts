import type { APIRoute } from 'astro';
import { sections, paragraphs } from '../../lib/data';

export const GET: APIRoute = () =>
  new Response(JSON.stringify({
    sections: sections.map((s) => ({ id: s.id, title: s.title, book: s.book })),
    section: Object.fromEntries(paragraphs.map((p) => [p.id, p.section])),
    sbn: Object.fromEntries(paragraphs.map((p) => [p.id, p.sbn])),
  }), { headers: { 'content-type': 'application/json' } });
