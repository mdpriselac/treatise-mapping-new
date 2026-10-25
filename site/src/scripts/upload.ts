// Sign-in, API calls and small DOM helpers shared by /upload/ and /upload/view/.
// The Google ID token lives in sessionStorage only: it goes when the tab closes.

export const API = String(import.meta.env.PUBLIC_UPLOAD_API ?? '').replace(/\/+$/, '');
const CLIENT_ID = String(import.meta.env.PUBLIC_GOOGLE_CLIENT_ID ?? '');
export const uploadsOpen = Boolean(API && CLIENT_ID && CLIENT_ID !== 'PENDING');

export const MAX_BYTES = 25 * 1024 * 1024;
export const ID_RE = /^[A-Za-z0-9_-]{16,64}$/;

/** Build a DOM node without HTML strings. */
export function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls = '', text = ''): HTMLElementTagNameMap[K] {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text) n.textContent = text;
  return n;
}

export function link(href: string, text: string, cls = '') {
  const a = el('a', cls, text);
  a.href = href;
  return a;
}

/** Show a message (or clear it with ''). */
export function say(box: HTMLElement, text: string, error = false) {
  box.textContent = text;
  box.classList.toggle('err', error);
  box.hidden = !text;
}

export const statusLabel: Record<string, string> = {
  awaiting_file: 'Waiting for the file',
  queued: 'Queued',
  checking: 'Checking the file',
  parsing: 'Reading the PDF',
  citations: 'Finding citations',
  profile: 'Comparing with the corpus',
  done: 'Done',
  rejected: 'Rejected',
  failed: 'Failed',
};

/** "24 November 2026" from an ISO string or Unix seconds. */
export function longDate(v: string | number) {
  const d = typeof v === 'number' ? new Date(v * 1000) : new Date(v);
  return isNaN(+d) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

// ---------------------------------------------------------------- token
const KEY = 'tm-upload-id-token';

function claims(t: string): { exp?: number; email?: string } | null {
  try {
    const b = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(b), (c) => c.charCodeAt(0))));
  } catch {
    return null;
  }
}

function read(): string | null {
  try { return sessionStorage.getItem(KEY); } catch { return memory; }
}
let memory: string | null = null;
function write(t: string | null) {
  memory = t;
  try { t ? sessionStorage.setItem(KEY, t) : sessionStorage.removeItem(KEY); } catch { /* memory only */ }
}

/** The current ID token, if it has at least a minute left. */
export function token(): string | null {
  const t = read();
  const c = t ? claims(t) : null;
  if (!t || !c?.exp || c.exp * 1000 < Date.now() + 60_000) return null;
  return t;
}

// ---------------------------------------------------------------- Google Identity Services
interface Gis {
  accounts: { id: {
    initialize(o: { client_id: string; callback: (r: { credential: string }) => void; auto_select?: boolean; context?: string }): void;
    renderButton(el: HTMLElement, o: Record<string, string | number>): void;
    disableAutoSelect(): void;
  } };
}
let gis: Promise<Gis> | null = null;
let onCredential: (t: string) => void = () => {};

function loadGis(): Promise<Gis> {
  gis ??= new Promise<Gis>((resolve, reject) => {
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.onload = () => {
      const g = (window as unknown as { google?: Gis }).google;
      if (!g) return reject(new Error('no google'));
      g.accounts.id.initialize({
        client_id: CLIENT_ID, context: 'signin',
        callback: (r) => { if (r.credential) { write(r.credential); onCredential(r.credential); } },
      });
      resolve(g);
    };
    s.onerror = () => { gis = null; reject(new Error('load failed')); };
    document.head.append(s);
  });
  return gis;
}

/**
 * Render the sign-in box. Calls onIn once a valid token exists (straight away if one is
 * already in this tab), and onOut when the person signs out or needs to sign in again.
 * Returns expired(message), for when the API answers 401.
 */
export function signIn(box: HTMLElement, onIn: (email: string) => void, onOut: () => void = () => {}) {
  const signedIn = (t: string) => {
    const who = el('span', '', 'Signed in as ');
    who.append(el('strong', '', claims(t)?.email ?? 'your Google account'));
    const out = el('button', 'link', 'Sign out');
    out.type = 'button';
    out.addEventListener('click', () => {
      write(null);
      gis?.then((g) => g.accounts.id.disableAutoSelect()).catch(() => {});
      prompt('');
      onOut();
    });
    const line = el('div', 'signedin');
    line.append(who, out);
    box.replaceChildren(line);
    onIn(claims(t)?.email ?? '');
  };

  const prompt = (message: string) => {
    const p = el('p', message ? 'msg err' : 'msg', message || 'Sign in with any Google account to continue.');
    p.style.marginTop = '0';
    const btn = el('div', 'gsi-button');
    box.replaceChildren(p, btn);
    onCredential = signedIn;
    loadGis().then((g) => {
      g.accounts.id.renderButton(btn, { type: 'standard', theme: 'outline', size: 'large', text: 'signin_with', shape: 'rectangular' });
    }).catch(() => {
      btn.replaceChildren(el('span', 'msg err', 'Google sign-in couldn’t load. Check that nothing is blocking accounts.google.com, then reload the page.'));
    });
  };

  if (!uploadsOpen) {
    box.replaceChildren(el('p', 'msg', 'Uploads aren’t open yet. Please check back soon.'));
    return { expired: () => {} };
  }
  const t = token();
  if (t) signedIn(t); else prompt('');
  return {
    expired(message = 'Your sign-in has expired; please sign in again.') {
      write(null);
      prompt(message);
      onOut();
    },
  };
}

// ---------------------------------------------------------------- API
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function detail(r: Response): Promise<string> {
  try {
    const j = await r.json();
    if (typeof j.detail === 'string') return j.detail;
    if (Array.isArray(j.detail)) return j.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ');
  } catch { /* not JSON */ }
  return `The upload service answered with an error (${r.status}).`;
}

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const t = token();
  if (!t) throw new ApiError(401, 'Your sign-in has expired; please sign in again.');
  const headers: Record<string, string> = { Authorization: `Bearer ${t}` };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let r: Response;
  try {
    r = await fetch(API + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch {
    throw new ApiError(0, 'Couldn’t reach the upload service. Check your connection and try again.');
  }
  if (!r.ok) throw new ApiError(r.status, await detail(r));
  return r.json() as Promise<T>;
}

/** PUT the file to the signed upload URL with exactly the headers the API gave. */
export async function putFile(url: string, headers: Record<string, string>, file: File) {
  let r: Response;
  try {
    r = await fetch(url, { method: 'PUT', headers, body: file });
  } catch {
    throw new ApiError(0, 'The file couldn’t be sent. Check your connection and try again.');
  }
  if (!r.ok) throw new ApiError(r.status, `The file couldn’t be stored (error ${r.status}). Please try again.`);
}
