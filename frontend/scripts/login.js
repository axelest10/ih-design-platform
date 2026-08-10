(() => {
  const form = document.getElementById("login-form");
  const username = document.getElementById("username");
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
      const response = await fetch("/api/v1/auth/login/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.value.trim(), password: password.value }),
      });
      const body = await response.json().catch(() => ({}));
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
})();
