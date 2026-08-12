(() => {
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
  const json = async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(body.detail || "La solicitud no pudo completarse."), { status: response.status });
    return body;
  };
  const request = (url, options = {}) => window.authenticatedFetch(url, options).then(json);
  const notice = (message, type = "error") => {
    $("review-notice").textContent = message;
    $("review-notice").className = `notice notice--${type}`;
  };
  const commentMarkup = (comment) => `<article class="review-comment"><strong>${escapeHtml(comment.author_email)}</strong><p>${escapeHtml(comment.comment)}</p><time>${new Date(comment.created_at).toLocaleString("es-MX")}</time></article>`;
  const formatLabels = { square: "Cuadrado", story: "Historia", portrait: "Vertical" };
  const statusLabels = { in_review: "En revisión", self_review: "Revisión automática", test_ready: "Listo para prueba", revision_requested: "Cambios solicitados" };
  const reviewLabels = { pending: "Pendiente", pass: "Correcto", needs_changes: "Requiere cambios" };
  const canvasFor = (version) => version?.validation_summary?.checks?.find((check) => check.name === "safe_area")?.canvas;
  const validationSummary = (version) => {
    const checks = version?.validation_summary?.checks || [];
    const needsChanges = checks.filter((check) => check.status !== "passed" && check.status !== "pass").length;
    if (!checks.length) return "Sin validación persistida.";
    return needsChanges ? `${needsChanges} verificación(es) requieren atención.` : `${checks.length} verificaciones correctas.`;
  };
  const versionDetailsMarkup = (version) => {
    const canvas = canvasFor(version);
    return `<div class="review-version-meta"><span>Template: ${escapeHtml(version?.template_key || "—")}</span><span>Dimensiones: ${canvas ? `${canvas.width} × ${canvas.height}px` : "No disponibles"}</span><span>Revisión: ${escapeHtml(reviewLabels[version?.claude_review_status] || version?.claude_review_status || "—")}</span></div><div class="review-version-summary"><strong>Validación</strong><span>${escapeHtml(validationSummary(version))}</span></div>`;
  };
  const previewMarkup = (version) => {
    const svg = version?.render_data?.svg;
    if (version?.render_data?.pdf_path) return '<p class="review-empty">Documento PDF listo para descargar.</p>';
    if (version?.render_data?.pptx_path) return '<p class="review-empty">Presentación PPTX lista para descargar.</p>';
    if (!svg) return '<p class="review-empty">La versión todavía no tiene una vista previa persistida.</p>';
    return `<img src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}" alt="Vista previa del diseño" />`;
  };
  const exportUrl = (designId, version, output) => `/api/v1/designs/${designId}/versions/${version.number}/export/?output=${output}`;
  const versionActionsMarkup = (designId, version) => {
    const actions = [];
    if (version?.render_data?.svg) {
      actions.push(`<a class="button button--secondary" href="${exportUrl(designId, version, "svg")}" download>Descargar SVG</a>`);
      actions.push(`<button class="button button--secondary" type="button" data-download-png="${designId}" data-version-number="${version.number}">Descargar PNG</button>`);
    }
    if (version?.render_data?.html) actions.push(`<a class="button button--secondary" href="${exportUrl(designId, version, "html")}" download>Descargar HTML</a>`);
    if (version?.render_data?.pdf_path) actions.push(`<a class="button button--secondary" href="${exportUrl(designId, version, "pdf")}" download>Descargar PDF</a>`);
    if (version?.render_data?.pptx_path) actions.push(`<a class="button button--secondary" href="${exportUrl(designId, version, "pptx")}" download>Descargar PPTX</a>`);
    return actions.length ? actions.join("") : '<span class="muted">Sin archivos descargables.</span>';
  };
  const versionHistoryMarkup = (design) => `<section class="version-history" aria-label="Historial de versiones"><h3>Historial de versiones</h3><div class="version-history__list">${design.versions.map((version, index) => `<button class="version-history__item${index === 0 ? " is-active" : ""}" type="button" data-select-version="${design.id}" data-version-id="${version.id}" data-version-number="${version.number}"><strong>Versión ${version.number}</strong><span>${escapeHtml(version.claude_review_status)}</span><time>${new Date(version.created_at).toLocaleString("es-MX")}</time></button>`).join("")}</div></section>`;
  const cardMarkup = (design, comments, testMode) => {
    const version = design.versions[0];
    const actions = testMode
      ? '<p class="test-mode-note">Durante las primeras 50 pruebas el flujo termina en revisión, sin aprobación formal.</p>'
      : `<div class="review-actions"><button class="button button--primary" data-decision="approve" data-design="${design.id}">Aprobar</button><button class="button button--secondary" data-decision="reject" data-design="${design.id}">Rechazar</button></div>`;
    return `<article class="card review-card" data-review-card="${design.id}"><div><div class="review-preview">${previewMarkup(version)}</div><div class="review-version-actions">${versionActionsMarkup(design.id, version)}</div>${versionHistoryMarkup(design)}</div><div><p class="eyebrow">${escapeHtml(statusLabels[design.status] || design.status)}</p><h2>${escapeHtml(design.brief_title)}</h2><div class="review-meta"><span>${escapeHtml(design.brief_country || "Sin país")}</span><span>${escapeHtml(design.brief_product_slug || "Sin producto")}</span><span>${escapeHtml(formatLabels[design.brief_format] || design.brief_format || "Sin formato")}</span><span data-current-version>Versión ${version?.number || "—"}</span></div><div data-version-details>${versionDetailsMarkup(version)}</div><div class="review-thread">${comments.length ? comments.map(commentMarkup).join("") : '<p class="muted">Todavía no hay comentarios.</p>'}</div><form class="review-form" data-comment-form="${design.id}"><textarea name="comment" required placeholder="Escribe retroalimentación clara y accionable"></textarea><input type="hidden" name="version_id" value="${version?.id || ""}" /><input type="hidden" name="version_number" value="${version?.number || ""}" /><button class="button button--secondary" type="submit">Agregar comentario</button></form>${actions}</div></article>`;
  };

  const state = { testMode: true, designs: new Map(), entries: [] };
  const filterElements = ["review-search", "review-status-filter", "review-country-filter", "review-product-filter", "review-format-filter", "review-automatic-filter"];
  const setFilterOptions = (id, values, labels = {}) => {
    const select = $(id);
    const current = select.value;
    select.querySelectorAll("option:not(:first-child)").forEach((option) => option.remove());
    [...new Set(values.filter(Boolean))].sort().forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labels[value] || value;
      select.appendChild(option);
    });
    select.value = current;
  };
  const populateFilters = (designs) => {
    setFilterOptions("review-status-filter", designs.map((design) => design.status), statusLabels);
    setFilterOptions("review-country-filter", designs.map((design) => design.brief_country));
    setFilterOptions("review-product-filter", designs.map((design) => design.brief_product_slug));
    setFilterOptions("review-format-filter", designs.map((design) => design.brief_format), formatLabels);
    setFilterOptions("review-automatic-filter", designs.map((design) => design.versions[0]?.claude_review_status), reviewLabels);
  };
  const renderEntries = () => {
    const search = $("review-search").value.trim().toLocaleLowerCase("es");
    const matches = state.entries.filter(({ design }) => {
      const latest = design.versions[0];
      return (!search || design.brief_title.toLocaleLowerCase("es").includes(search))
        && (!$("review-status-filter").value || design.status === $("review-status-filter").value)
        && (!$("review-country-filter").value || design.brief_country === $("review-country-filter").value)
        && (!$("review-product-filter").value || design.brief_product_slug === $("review-product-filter").value)
        && (!$("review-format-filter").value || design.brief_format === $("review-format-filter").value)
        && (!$("review-automatic-filter").value || latest?.claude_review_status === $("review-automatic-filter").value);
    });
    $("review-result-count").textContent = `${matches.length} de ${state.entries.length} diseños`;
    $("review-list").innerHTML = matches.length
      ? matches.map(({ design, comments }) => cardMarkup(design, comments, state.testMode)).join("")
      : '<article class="card review-empty"><h2>Sin coincidencias.</h2><p>Prueba con otros filtros o limpia la búsqueda.</p></article>';
  };
  const load = () => request("/api/v1/me/").then((user) => {
    if (!user.can_review) {
      $("review-access-denied").hidden = false;
      $("review-list").innerHTML = "";
      throw Object.assign(new Error("Necesitas capacidad de revisión para consultar esta página."), { handled: true });
    }
    $("review-access-denied").hidden = true;
    $("review-loading").hidden = false;
    $("reviewer-label").textContent = user.email || "Reviewer";
    state.testMode = user.design_test_mode;
    return request("/api/v1/designs/");
  }).then((payload) => {
    const reviewStatuses = ["in_review", "self_review", "test_ready", "revision_requested"];
    const designs = (payload.results || payload).filter((design) => reviewStatuses.includes(design.status));
    if (!designs.length) {
      $("review-list").innerHTML = '<article class="card review-empty"><h2>No hay diseños pendientes.</h2><p>Cuando una pieza entre a revisión aparecerá aquí.</p></article>';
      $("review-loading").hidden = true;
      return null;
    }
    state.designs = new Map(designs.map((design) => [String(design.id), design]));
    return Promise.all(designs.map((design) => request(`/api/v1/designs/${design.id}/comments/`).then((comments) => ({ design, comments })))).then((entries) => {
      state.entries = entries;
      populateFilters(designs);
      $("review-filters").hidden = false;
      $("review-loading").hidden = true;
      renderEntries();
    });
  }).catch((error) => { $("review-loading").hidden = true; if (!error.handled) notice(error.message); });

  $("review-list").addEventListener("submit", (event) => {
    const form = event.target.closest("[data-comment-form]");
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    request(`/api/v1/designs/${form.dataset.commentForm}/comments/`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comment: data.get("comment"), version: Number(data.get("version_id")) || null }),
    }).then(() => { notice("Comentario guardado.", "success"); return load(); }).catch((error) => notice(error.message));
  });
  $("review-list").addEventListener("click", (event) => {
    const versionButton = event.target.closest("[data-select-version]");
    if (versionButton) {
      const design = state.designs.get(versionButton.dataset.selectVersion);
      const version = design?.versions.find((item) => String(item.id) === versionButton.dataset.versionId);
      const card = versionButton.closest("[data-review-card]");
      if (!version || !card) return;
      card.querySelector(".review-preview").innerHTML = previewMarkup(version);
      card.querySelector(".review-version-actions").innerHTML = versionActionsMarkup(design.id, version);
      card.querySelector("[data-current-version]").textContent = `Versión ${version.number}`;
      card.querySelector("[data-version-details]").innerHTML = versionDetailsMarkup(version);
      card.querySelector('[name="version_id"]').value = version.id;
      card.querySelector('[name="version_number"]').value = version.number;
      card.querySelectorAll("[data-select-version]").forEach((item) => item.classList.toggle("is-active", item === versionButton));
      return;
    }
    const pngButton = event.target.closest("[data-download-png]");
    if (pngButton) {
      const designId = pngButton.dataset.downloadPng;
      const versionNumber = pngButton.dataset.versionNumber;
      window.authenticatedFetch(exportUrl(designId, { number: versionNumber }, "svg"))
        .then(async (response) => {
          if (!response.ok) throw new Error("No pudimos preparar el PNG.");
          return response.blob();
        })
        .then((svgBlob) => new Promise((resolve, reject) => {
          const image = new Image();
          const source = URL.createObjectURL(svgBlob);
          image.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = image.naturalWidth;
            canvas.height = image.naturalHeight;
            canvas.getContext("2d").drawImage(image, 0, 0);
            URL.revokeObjectURL(source);
            canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("No pudimos preparar el PNG.")), "image/png");
          };
          image.onerror = () => { URL.revokeObjectURL(source); reject(new Error("No pudimos leer el SVG.")); };
          image.src = source;
        }))
        .then((blob) => {
          const link = document.createElement("a");
          link.href = URL.createObjectURL(blob);
          link.download = `design-${designId}-version-${versionNumber}.png`;
          link.click();
          URL.revokeObjectURL(link.href);
          notice("PNG preparado para descargar.", "success");
        })
        .catch((error) => notice(error.message));
      return;
    }
    const button = event.target.closest("[data-decision]");
    if (!button) return;
    const form = button.closest("[data-review-card]").querySelector("[data-comment-form]");
    const data = new FormData(form);
    request(`/api/v1/designs/${button.dataset.design}/review/`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: button.dataset.decision, version: Number(data.get("version_number")), comment: data.get("comment") }),
    }).then(() => { notice("Decisión guardada.", "success"); return load(); }).catch((error) => notice(error.message));
  });
  filterElements.forEach((id) => $(id).addEventListener(id === "review-search" ? "input" : "change", renderEntries));
  $("review-clear-filters").addEventListener("click", () => {
    filterElements.forEach((id) => { $(id).value = ""; });
    renderEntries();
    $("review-search").focus();
  });
  load();
})();
