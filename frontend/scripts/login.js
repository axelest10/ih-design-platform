(() => {
  const form = document.getElementById("login-form");
  const email = document.getElementById("email");
  const button = document.getElementById("submit-button");
  const notice = document.getElementById("auth-notice");

  const showNotice = (message, type) => {
    notice.textContent = message;
    notice.className = `auth-notice auth-notice--${type}`;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    button.disabled = true;
    button.textContent = "Enviando…";
    showNotice("Estamos preparando tu enlace de acceso.", "pending");

    try {
      const response = await fetch("/api/v1/auth/magic-link/request/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.value.trim() }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "No fue posible enviar el enlace de acceso.");

      showNotice(
        "Revisa tu correo. El enlace expira pronto y solo puede utilizarse una vez.",
        "success",
      );
      button.textContent = "Enviar otro enlace";
    } catch (error) {
      showNotice(error.message, "error");
      button.textContent = "Intentar de nuevo";
    } finally {
      button.disabled = false;
    }
  });
})();
