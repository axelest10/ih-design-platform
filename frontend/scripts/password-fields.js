(() => {
  const setup = (root = document) => {
    root.querySelectorAll("[data-password-toggle]").forEach((button) => {
      if (button.dataset.passwordToggleReady === "true") return;
      button.dataset.passwordToggleReady = "true";
      button.addEventListener("click", () => {
        const inputs = passwordInputs(button);
        const shouldShow = inputs.some((input) => input.type === "password");
        setVisible(button, shouldShow);
      });
    });
  };

  const passwordInputs = (button) => button.dataset.passwordToggle
    .split(",")
    .map((id) => document.getElementById(id.trim()))
    .filter(Boolean);

  const setVisible = (button, visible) => {
    passwordInputs(button).forEach((input) => {
      input.type = visible ? "text" : "password";
    });
    button.setAttribute("aria-pressed", String(visible));
    button.textContent = visible ? "Ocultar contraseñas" : "Mostrar contraseñas";
  };

  const valuesMatch = (form, passwordName, confirmationName) => (
    form.elements[passwordName]?.value === form.elements[confirmationName]?.value
  );

  const hide = (root) => {
    root.querySelectorAll("[data-password-toggle]").forEach((button) => setVisible(button, false));
  };

  window.IHPasswordFields = { hide, setup, valuesMatch };
})();
