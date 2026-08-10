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

  const setText = (selector, value) => {
    document.querySelectorAll(selector).forEach((element) => {
      element.textContent = value;
    });
  };

  const workflowState = (workflow) => {
    if (!workflow.briefs) return { active: 0, label: "Crear brief", href: "panel.html" };
    if (!workflow.designs) return { active: 1, label: "Generar preview", href: "panel.html" };
    if (workflow.pending_review || !workflow.approved) {
      return { active: 2, label: "Revisión pendiente", href: "review.html" };
    }
    return { active: 3, label: "Piezas disponibles", href: "review.html" };
  };

  const renderWorkflow = (workflow) => {
    const state = workflowState(workflow);
    const steps = document.querySelectorAll("[data-workflow-step]");
    steps.forEach((step, index) => {
      step.classList.toggle("review-step--done", index < state.active);
      step.classList.toggle("review-step--active", index === state.active);
      step.querySelector(":scope > span").textContent = index < state.active ? "✓" : index + 1;
    });
    setText("[data-workflow-status]", state.label);
    const link = document.querySelector("[data-workflow-link]");
    if (link) link.href = state.href;
    const reviewBadge = document.querySelector("[data-review-count]");
    if (reviewBadge) {
      reviewBadge.textContent = workflow.pending_review;
      reviewBadge.hidden = workflow.pending_review === 0;
    }
  };

  const resetSummary = () => {
    setText("[data-logo-count]", "—");
    setText("[data-material-type-count]", "—");
    setText("[data-country-count]", "—");
    setText("[data-catalog-status]", "—");
    setText("[data-catalog-footer]", "No disponible");
    setText("[data-workflow-status]", "No disponible");
  };

  menuToggle?.addEventListener("click", () => {
    sidebar?.classList.toggle("sidebar--open");
  });

  document.querySelectorAll("[data-toast]").forEach((element) => {
    element.addEventListener("click", () => showToast(element.dataset.toast));
  });

  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => sidebar?.classList.remove("sidebar--open"));
  });

  document.querySelector("#country-filter")?.addEventListener("change", (event) => {
    const label = event.target.options[event.target.selectedIndex].text;
    showToast(`Cobertura seleccionada: ${label}`);
  });

  fetch("/api/v1/stats/summary/")
    .then((response) => {
      if (!response.ok) throw new Error("summary unavailable");
      return response.json();
    })
    .then((summary) => {
      setText("[data-logo-count]", summary.logos.approved);
      setText("[data-material-type-count]", summary.material_types.active);
      setText("[data-country-count]", summary.countries.count);
      const catalogStatus = summary.catalog.status === "partial" ? "En actualización" : "Activo";
      setText("[data-catalog-status]", catalogStatus);
      setText("[data-catalog-footer]", `${catalogStatus} · v${summary.catalog.version}`);
      renderWorkflow(summary.workflow);
    })
    .catch(resetSummary);
})();
