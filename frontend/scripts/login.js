(() => {
  const form = document.getElementById("login-form");
  const password = document.getElementById("password");
  const button = document.getElementById("submit-button");
  const notice = document.getElementById("auth-notice");

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
      const response = await fetch("/api/v1/auth/site-access/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password: password.value }),
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) throw new Error("Contraseña incorrecta.");
      if (response.status === 503) {
        throw new Error("El acceso no está configurado — contacta al administrador.");
      }
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
})();
