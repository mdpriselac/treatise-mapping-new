import type { APIRoute } from 'astro';
import { papers, shortName } from '../../lib/data';

// Slim copy of the paper data for client-side charts and filters.
export const GET: APIRoute = () =>
  new Response(JSON.stringify(papers.map((p) => ({
    id: p.id, name: shortName(p), title: p.title, year: p.year, cites: p.cites,
    focus: p.focus, surprise: p.surprise, themes: p.themes, weights: p.weights,
  }))), { headers: { 'content-type': 'application/json' } });
