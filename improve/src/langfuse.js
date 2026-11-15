// Read-only Langfuse public API client (zero dependencies). The runtime reads
// every harness session from Langfuse observations: this instance has no
// sessions or traces endpoint, so everything goes through
// /api/public/v2/observations with cursor paging.

const PAGE_LIMIT = 1000;
const RETRIES = 4;

/** Base URL and keys from the same variables `review-queue` uses. */
export function langfuseConfig(env = process.env) {
  const missing = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"].filter((name) => !env[name]);
  if (missing.length) throw new Error(`${missing.join(", ")} not set: the improvement runtime reads sessions from Langfuse`);
  return { baseUrl: env.LANGFUSE_BASE_URL, publicKey: env.LANGFUSE_PUBLIC_KEY, secretKey: env.LANGFUSE_SECRET_KEY };
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * `fetch` is injectable for tests; `retryDelayMs` scales the backoff between
 * retries of 429 and 5xx responses and network errors.
 */
export function langfuseClient({ baseUrl, publicKey, secretKey, fetch: fetchImpl = globalThis.fetch, retryDelayMs = 500 } = langfuseConfig()) {
  const base = String(baseUrl).replace(/\/+$/, "");
  const auth = `Basic ${Buffer.from(`${publicKey}:${secretKey}`).toString("base64")}`;

  async function get(pathname, query = {}) {
    const url = new URL(base + pathname);
    for (const [key, value] of Object.entries(query)) if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    for (let attempt = 0; ; attempt += 1) {
      let response;
      try {
        response = await fetchImpl(url, { headers: { Authorization: auth, Accept: "application/json" } });
      } catch (err) {
        if (attempt < RETRIES) { await sleep(retryDelayMs * 2 ** attempt); continue; }
        throw new Error(`Langfuse unreachable at ${base}: ${err.message}`);
      }
      if ((response.status === 429 || response.status >= 500) && attempt < RETRIES) {
        await sleep(retryDelayMs * 2 ** attempt);
        continue;
      }
      const text = await response.text();
      if (!response.ok) throw new Error(`Langfuse ${pathname} returned ${response.status}: ${text.slice(0, 300)}`);
      try {
        return JSON.parse(text);
      } catch {
        throw new Error(`Langfuse ${pathname} returned non-JSON`);
      }
    }
  }

  /** Every observation matching `query`, across all cursor pages. */
  async function observations(query = {}) {
    const out = [];
    let cursor;
    do {
      const page = await get("/api/public/v2/observations", { limit: PAGE_LIMIT, ...query, cursor });
      if (!Array.isArray(page?.data)) throw new Error("Langfuse observations page has no data array");
      out.push(...page.data);
      cursor = page.meta?.cursor || undefined;
    } while (cursor);
    return out;
  }

  return { observations };
}
