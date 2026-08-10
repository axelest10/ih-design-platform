(() => {
  const cookie = (name) => document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")[1] || "";

  window.authenticatedFetch = (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    const method = String(options.method || "GET").toUpperCase();
    if (method !== "GET") {
      headers.set("X-CSRFToken", decodeURIComponent(cookie("csrftoken")));
    }
    return fetch(url, { ...options, headers });
  };
})();
