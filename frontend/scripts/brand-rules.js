(() => {
  const allowedDocuments = new Set([
    "logo-rules.md",
    "color-rules.md",
    "typography-rules.md",
    "imagery-rules.md",
    "layout-rules.md",
    "accessibility-rules.md",
    "do-and-dont.md",
  ]);
  const content = document.querySelector("#rules-content");
  const status = document.querySelector("#rules-status");

  const activateButton = (filename) => {
    document.querySelectorAll("[data-document]").forEach((button) => {
      button.classList.toggle("rules-menu__item--active", button.dataset.document === filename);
    });
  };

  const renderDocument = (filename) => {
    if (!allowedDocuments.has(filename)) return;
    activateButton(filename);
    status.hidden = false;
    status.textContent = "Cargando reglas…";
    content.hidden = true;
    fetch(`/brand/documentation/${encodeURIComponent(filename)}`)
      .then((response) => {
        if (!response.ok) throw new Error("document unavailable");
        return response.text();
      })
      .then((markdown) => {
        if (!window.marked?.parse) throw new Error("markdown renderer unavailable");
        content.innerHTML = window.marked.parse(markdown);
        content.querySelectorAll("a[href]").forEach((link) => {
          if (link.href.startsWith("http")) {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
          }
        });
        status.hidden = true;
        content.hidden = false;
        window.history.replaceState({}, "", `?doc=${encodeURIComponent(filename)}`);
      })
      .catch(() => {
        status.textContent = "No pudimos cargar este documento. Intenta de nuevo más tarde.";
      });
  };

  document.querySelector("#menu-toggle")?.addEventListener("click", () => {
    document.querySelector("#sidebar")?.classList.toggle("sidebar--open");
  });
  document.querySelectorAll("[data-document]").forEach((button) => {
    button.addEventListener("click", () => renderDocument(button.dataset.document));
  });

  const requested = new URLSearchParams(window.location.search).get("doc");
  renderDocument(allowedDocuments.has(requested) ? requested : "logo-rules.md");
})();
