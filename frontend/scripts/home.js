(() => {
  const sidebar = document.querySelector("#sidebar");
  const menuToggle = document.querySelector("#menu-toggle");
  const toast = document.querySelector("#toast");
  let toastTimer;

  const showToast = (message) => {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add("toast--visible");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("toast--visible"), 2600);
  };

  menuToggle?.addEventListener("click", () => {
    sidebar?.classList.toggle("sidebar--open");
  });

  document.querySelectorAll("[data-toast]").forEach((element) => {
    element.addEventListener("click", (event) => {
      const href = element.getAttribute("href") || "";
      if (href.startsWith("#")) {
        event.preventDefault();
        document.querySelector(href)?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      showToast(element.dataset.toast);
    });
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((navItem) => {
        navItem.classList.remove("nav-item--active");
        navItem.removeAttribute("aria-current");
      });
      item.classList.add("nav-item--active");
      item.setAttribute("aria-current", "page");
      sidebar?.classList.remove("sidebar--open");
    });
  });

  document.querySelector("#country-filter")?.addEventListener("change", (event) => {
    const label = event.target.options[event.target.selectedIndex].text;
    showToast(`Cobertura seleccionada: ${label}`);
  });

  fetch("/api/v1/branding/logos/")
    .then((response) => (response.ok ? response.json() : Promise.reject(new Error("catalog unavailable"))))
    .then((payload) => {
      document.querySelectorAll("[data-logo-count]").forEach((element) => {
        element.textContent = payload.count;
      });
    })
    .catch(() => {
      // La Home también funciona como prototipo estático cuando no está levantado Django.
    });
})();
