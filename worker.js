async function proxyRequest(request, UPSTREAM_URL, url) {
    const upstreamUrl = new URL(url.pathname + url.search, UPSTREAM_URL);
    const newHeaders = new Headers(request.headers);
    newHeaders.set("Host", upstreamUrl.host);

    // Clean Cloudflare internal headers to avoid upstream confusion
    ["cf-connecting-ip", "cf-ray", "cf-visitor", "x-forwarded-for", "x-real-ip"].forEach(h => newHeaders.delete(h));

    const init = {
        method: request.method,
        headers: newHeaders,
        redirect: "follow"
    };

    // Note: We don't support POST racing because the body stream can only be consumed once.
    // For GET/HEAD (downloads), request.body is null, so this is safe.

    try {
        const response = await fetch(upstreamUrl.toString(), init);

        // Return 200 or 206 (Partial Content) as success
        if (response.ok || response.status === 206) {
            const modifiedResponse = new Response(response.body, response);
            modifiedResponse.headers.set("Access-Control-Allow-Origin", "*");
            modifiedResponse.headers.set("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS");
            modifiedResponse.headers.set("Access-Control-Allow-Headers", "*");
            return modifiedResponse;
        }
    } catch (e) {
        // Log error and fall through so Promise.any can wait for others
        console.error(`Fetch to ${UPSTREAM_URL} failed:`, e.message);
    }
    throw new Error(`Backend ${UPSTREAM_URL} failed or returned error`);
}

export default {
    async fetch(request, env) {
        const url = new URL(request.url);
        const BACKENDS = [
            "https://vickydmt-tg-stream.hf.space",
            "https://vickydmt-tg-stream1.hf.space",
            "https://vickydmt-tg-stream2.hf.space",
        ];

        // For non-download requests (like /watch), just pick one randomly
        if (!url.pathname.startsWith("/dl/")) {
            const UPSTREAM_URL = BACKENDS[Math.floor(Math.random() * BACKENDS.length)];
            try {
                return await proxyRequest(request, UPSTREAM_URL, url);
            } catch (e) {
                // Try any other one if the first choice fails
                const fallback = BACKENDS.find(b => b !== UPSTREAM_URL);
                return await proxyRequest(request, fallback, url);
            }
        }

        /**
         * RACING STRATEGY:
         * We fire requests to ALL backends at once. Use the one that responds FIRST with success.
         * This ensures an instant start even if 2/3 backends are down.
         * We removed the .abort() call because it was killing the 'winner' response stream in some cases.
         */
        const promises = BACKENDS.map((BACKEND) => proxyRequest(request, BACKEND, url));

        try {
            return await Promise.any(promises);
        } catch (e) {
            // This happens if ALL backends failed
            return new Response("All backends are currently unreachable. The bot might be down or stuck in a 'Flood Wait'. Please check your spaces.", {
                status: 502,
                headers: { "Content-Type": "text/plain" }
            });
        }
    },
};
