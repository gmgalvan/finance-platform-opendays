// Trazas desde el navegador, sin librerías.
//
// tracedFetch() funciona como fetch(), pero además:
//   1. Crea un identificador de traza y lo envía a la API en el encabezado
//      W3C "traceparent". Nginx y la API continúan esa misma traza.
//   2. Mide cuánto tarda la solicitud vista por el usuario.
//   3. Envía ese span a Jaeger en formato OTLP/JSON a través de Nginx (/v1/traces).
//
// Si Jaeger no está disponible, el envío falla en silencio y la app sigue igual.

(function () {
  const SERVICE_NAME = "finance-web";
  const COLLECTOR_URL = "/v1/traces";

  function randomHex(byteCount) {
    const bytes = new Uint8Array(byteCount);
    crypto.getRandomValues(bytes);
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  }

  function nowUnixNano() {
    const microseconds = Math.round((performance.timeOrigin + performance.now()) * 1000);
    return (BigInt(microseconds) * 1000n).toString();
  }

  function attribute(key, value) {
    const typed = typeof value === "number" ? { intValue: value } : { stringValue: String(value) };
    return { key, value: typed };
  }

  function exportSpan(span) {
    const body = JSON.stringify({
      resourceSpans: [
        {
          resource: { attributes: [attribute("service.name", SERVICE_NAME)] },
          scopeSpans: [{ scope: { name: SERVICE_NAME }, spans: [span] }],
        },
      ],
    });
    fetch(COLLECTOR_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {});
  }

  async function tracedFetch(spanName, url, options = {}) {
    const traceId = randomHex(16);
    const spanId = randomHex(8);
    const headers = new Headers(options.headers || {});
    headers.set("traceparent", `00-${traceId}-${spanId}-01`);

    const method = (options.method || "GET").toUpperCase();
    const startTimeUnixNano = nowUnixNano();
    const attributes = [
      attribute("http.request.method", method),
      attribute("url.path", new URL(url, window.location.href).pathname),
      attribute("page", window.location.pathname),
    ];
    let status = { code: 1 };

    try {
      const response = await fetch(url, { ...options, headers });
      attributes.push(attribute("http.response.status_code", response.status));
      if (response.status >= 500) {
        status = { code: 2, message: `HTTP ${response.status}` };
      }
      return response;
    } catch (error) {
      status = { code: 2, message: error.message };
      throw error;
    } finally {
      exportSpan({
        traceId,
        spanId,
        name: spanName,
        kind: 3,
        startTimeUnixNano,
        endTimeUnixNano: nowUnixNano(),
        attributes,
        status,
      });
    }
  }

  window.tracedFetch = tracedFetch;
})();
