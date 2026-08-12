(() => {
  const form = document.getElementById("login-form");
  const username = document.getElementById("username");
  const password = document.getElementById("password");
  const button = document.getElementById("submit-button");
  const notice = document.getElementById("auth-notice");
  const resetRequestForm = document.getElementById("password-reset-request-form");
  const resetConfirmForm = document.getElementById("password-reset-confirm-form");
  const resetToken = new URLSearchParams(window.location.hash.slice(1)).get("reset");

  const json = async (response) => response.json().catch(() => ({}));

  const showNotice = (message, type) => {
    notice.textContent = message;
    notice.className = `auth-notice auth-notice--${type}`;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = "Entrando…";
    showNotice("Verificando el acceso…", "pending");

    try {
      const response = await window.authenticatedFetch("/api/v1/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.value.trim(), password: password.value }),
      });
      const body = await json(response);
      if (response.status === 401) throw new Error("Usuario o contraseña incorrectos.");
      if (response.status === 429) throw new Error("Demasiados intentos, espera un momento.");
      if (!response.ok) throw new Error(body.detail || "No fue posible iniciar sesión.");

      window.location.href = "/panel.html";
    } catch (error) {
      showNotice(error.message, "error");
      button.textContent = "Intentar de nuevo";
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById("forgot-password-toggle").addEventListener("click", () => {
    resetRequestForm.hidden = !resetRequestForm.hidden;
    if (!resetRequestForm.hidden) document.getElementById("reset-email").focus();
  });

  resetRequestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await window.authenticatedFetch("/api/v1/auth/password-reset/request/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: document.getElementById("reset-email").value.trim() }),
    });
    const body = await json(response);
    showNotice(body.detail || "Revisa tu correo para continuar.", response.ok ? "success" : "error");
  });

  if (resetToken) {
    form.hidden = true;
    document.getElementById("forgot-password-toggle").hidden = true;
    resetConfirmForm.hidden = false;
    history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
  }

  resetConfirmForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const newPassword = document.getElementById("reset-new-password").value;
    const confirmation = document.getElementById("reset-new-password-confirmation").value;
    if (newPassword !== confirmation) {
      showNotice("Las contraseñas nuevas no coinciden.", "error");
      return;
    }
    const response = await window.authenticatedFetch("/api/v1/auth/password-reset/confirm/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: resetToken, new_password: newPassword }),
    });
    const body = await json(response);
    showNotice(body.detail || "No fue posible actualizar la contraseña.", response.ok ? "success" : "error");
    if (response.ok) {
      resetConfirmForm.hidden = true;
      form.hidden = false;
    }
  });

  fetch("/api/v1/me/").then(json).then((body) => {
    if (body.authenticated) window.location.replace("/panel.html");
  }).catch(() => {});
})();
