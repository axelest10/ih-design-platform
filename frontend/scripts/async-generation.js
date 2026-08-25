(() => {
  const parseResponse = async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "No pudimos consultar el estado de la generación.");
    }
    return payload;
  };

  const waitForResult = async (initialResult, options = {}) => {
    if (!initialResult?.status_url) return initialResult;

    const request = options.request || globalThis.window?.authenticatedFetch;
    const wait = options.wait || ((milliseconds) => new Promise(
      (resolve) => globalThis.setTimeout(resolve, milliseconds),
    ));
    const intervalMs = options.intervalMs ?? 1000;
    const maxPolls = options.maxPolls ?? 300;
    const onProgress = options.onProgress || (() => {});
    const statusUrl = initialResult.status_url;

    if (typeof request !== "function") {
      throw new Error("No pudimos consultar el estado de la generación.");
    }

    for (let poll = 0; poll < maxPolls; poll += 1) {
      if (poll > 0) await wait(intervalMs);
      const job = await parseResponse(await request(statusUrl));
      onProgress(job);

      if (job.status === "succeeded") {
        if (!job.result || typeof job.result !== "object") {
          throw new Error("La generación terminó sin devolver el diseño.");
        }
        return job.result;
      }
      if (job.status === "failed") {
        throw new Error(job.error || "No pudimos generar el diseño.");
      }
      if (!["queued", "processing"].includes(job.status)) {
        throw new Error("La generación devolvió un estado desconocido.");
      }
    }

    throw new Error("La generación tardó demasiado. Intenta de nuevo.");
  };

  const api = { waitForResult };
  if (typeof window !== "undefined") window.IHAsyncGeneration = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})();
