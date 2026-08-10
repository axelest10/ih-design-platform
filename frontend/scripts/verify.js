(() => {
  const title = document.getElementById("verify-title");
  const status = document.getElementById("verify-status");
  const retryLink = document.getElementById("retry-link");
  const token = new URLSearchParams(window.location.search).get("token");

  const showError = (message) => {
    title.textContent = "No pudimos iniciar tu sesión.";
    status.textContent = message;
    status.classList.add("auth-intro--error");
    retryLink.hidden = false;
  };

  if (!token) {
    showError("El enlace no incluye un token de acceso. Pide un enlace nuevo.");
    return;
  }

  fetch(`/api/v1/auth/magic-link/verify/?token=${encodeURIComponent(token)}`)
    .then(async (response) => {
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "El enlace no es válido o ya expiró.");
      return body;
    })
    .then(() => {
      title.textContent = "Sesión iniciada.";
      status.textContent = "Te llevamos al panel de diseño…";
      window.location.href = "/panel.html";
    })
    .catch((error) => showError(error.message));
})();
