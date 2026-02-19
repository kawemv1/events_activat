const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY in .env.local');
}

const headers = {
  apikey: SUPABASE_ANON_KEY,
  Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
  'Content-Type': 'application/json',
};

export async function supabaseGet<T>(table: string, query: string = ''): Promise<T[]> {
  const url = `${SUPABASE_URL}/rest/v1/${table}${query ? '?' + query : ''}`;
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new Error(`Supabase GET ${table} failed: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

export async function supabasePost<T>(table: string, data: Record<string, unknown>): Promise<T[]> {
  const url = `${SUPABASE_URL}/rest/v1/${table}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { ...headers, Prefer: 'return=representation' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase POST ${table} failed: ${response.status} ${text}`);
  }
  return response.json();
}

export async function supabasePatch<T>(table: string, data: Record<string, unknown>, query: string = ''): Promise<T[]> {
  const url = `${SUPABASE_URL}/rest/v1/${table}${query ? '?' + query : ''}`;
  const response = await fetch(url, {
    method: 'PATCH',
    headers: { ...headers, Prefer: 'return=representation' },
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase PATCH ${table} failed: ${response.status} ${text}`);
  }
  return response.json();
}

export async function supabaseDelete(table: string, query: string): Promise<void> {
  const url = `${SUPABASE_URL}/rest/v1/${table}${query ? '?' + query : ''}`;
  const response = await fetch(url, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Supabase DELETE ${table} failed: ${response.status} ${text}`);
  }
}

export async function supabaseRpc<T>(fn: string, params: Record<string, unknown> = {}): Promise<T> {
  const url = `${SUPABASE_URL}/rest/v1/rpc/${fn}`;
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });
  if (!response.ok) {
    throw new Error(`Supabase RPC ${fn} failed: ${response.status}`);
  }
  return response.json();
}
