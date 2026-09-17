/** Client for the duzelt service. */

export type Change = {
  start: number;
  end: number;
  from: string;
  to: string;
};

export type RestoreResult = {
  text: string;
  changes: Change[];
};

export type ServiceInfo = {
  version: string;
  restorer: string;
  max_characters: number;
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const detail = response.status === 429 ? "too many requests" : `request failed (${response.status})`;
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export function restore(text: string): Promise<RestoreResult> {
  return request<RestoreResult>("/v1/restore", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function info(): Promise<ServiceInfo> {
  return request<ServiceInfo>("/v1/info");
}

/**
 * Rebuild the text with some changes turned down.
 *
 * Every change covers the same span in both versions - a restorer may only swap letters
 * for their accented forms - so a rejected change is just the original slice put back.
 */
export function applyChanges(typed: string, changes: Change[], rejected: ReadonlySet<number>): string {
  let result = "";
  let cursor = 0;

  changes.forEach((change, index) => {
    result += typed.slice(cursor, change.start);
    result += rejected.has(index) ? change.from : change.to;
    cursor = change.end;
  });

  return result + typed.slice(cursor);
}
