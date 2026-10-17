// Forwards every /api/* request to the FastAPI service, so the browser never
// calls it directly (no CORS, and API_URL is read at request time, not baked
// in at build time).

const UPSTREAM_TIMEOUT_MS = 90_000;

// Headers that describe a single connection or the original encoding, which
// must not be copied across the proxy.
const STRIP_REQUEST_HEADERS = [
  "host",
  "connection",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
  "te",
  "trailer",
  "content-length",
  "accept-encoding",
];
const STRIP_RESPONSE_HEADERS = [
  "connection",
  "keep-alive",
  "transfer-encoding",
  "content-encoding",
  "content-length",
];

async function forward(request, { params }) {
  const apiUrl = process.env.API_URL;
  if (!apiUrl) {
    return Response.json(
      { error: "API_URL is not set on the web server." },
      { status: 500 },
    );
  }

  const { path } = await params;
  const { search } = new URL(request.url);
  const target = new URL(
    `/api/${path.map(encodeURIComponent).join("/")}${search}`,
    apiUrl,
  );

  const headers = new Headers(request.headers);
  STRIP_REQUEST_HEADERS.forEach((name) => headers.delete(name));

  const hasBody = !["GET", "HEAD"].includes(request.method);

  let upstream;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      // Buffer the body: requests are small (GeoJSON, a photo), and this
      // avoids streaming-upload quirks in Node's fetch.
      body: hasBody ? await request.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
    });
  } catch (error) {
    const timedOut = error?.name === "TimeoutError";
    return Response.json(
      {
        error: timedOut
          ? "The ClaimSat API took too long to respond."
          : "Could not reach the ClaimSat API.",
        detail: String(error?.message ?? error),
      },
      { status: timedOut ? 504 : 502 },
    );
  }

  const responseHeaders = new Headers(upstream.headers);
  STRIP_RESPONSE_HEADERS.forEach((name) => responseHeaders.delete(name));

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export {
  forward as GET,
  forward as POST,
  forward as PUT,
  forward as PATCH,
  forward as DELETE,
};
