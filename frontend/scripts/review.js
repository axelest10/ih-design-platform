(() => {
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
  const cookie = (name) => document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1] || "";
  const json = async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(body.detail || "La solicitud no pudo completarse."), { status: response.status });
    return body;
  };
  const request = (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (options.method && options.method !== "GET") headers.set("X-CSRFToken", decodeURIComponent(cookie("csrftoken")));
    return fetch(url, { ...options, headers }).then(json);
  };
  const notice = (message, type = "error") => {
    $("review-notice").textContent = message;
    $("review-notice").className = `notice notice--${type}`;
  };
  const commentMarkup = (comment) => `<article class="review-comment"><strong>${escapeHtml(comment.author_email)}</strong><p>${escapeHtml(comment.comment)}</p><time>${new Date(comment.created_at).toLocaleString("es-MX")}</time></article>`;
  const previewMarkup = (version) => {
    const svg = version?.render_data?.svg;
    if (!svg) return '<p class="review-empty">La versión todavía no tiene un SVG persistido.</p>';
    return `<img src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}" alt="Vista previa del diseño" />`;
  };
  const cardMarkup = (design, comments, testMode) => {
    const version = design.versions[0];
    const actions = testMode
      ? '<p class="test-mode-note">Durante las primeras 50 pruebas el flujo termina en revisión, sin aprobación formal.</p>'
      : `<div class="review-actions"><button class="button button--primary" data-decision="approve" data-design="${design.id}">Aprobar</button><button class="button button--secondary" data-decision="reject" data-design="${design.id}">Rechazar</button></div>`;
    return `<article class="card review-card" data-review-card="${design.id}"><div><div class="review-preview">${previewMarkup(version)}</div></div><div><p class="eyebrow">${escapeHtml(design.status)}</p><h2>${escapeHtml(design.brief_title)}</h2><div class="review-meta"><span>${escapeHtml(design.brief_product_slug || "Sin producto")}</span><span>Versión ${version?.number || "—"}</span></div><div class="review-thread">${comments.length ? comments.map(commentMarkup).join("") : '<p class="muted">Todavía no hay comentarios.</p>'}</div><form class="review-form" data-comment-form="${design.id}"><textarea name="comment" required placeholder="Escribe retroalimentación clara y accionable"></textarea><input type="hidden" name="version" value="${version?.id || ""}" /><button class="button button--secondary" type="submit">Agregar comentario</button></form>${actions}</div></article>`;
  };

  const state = { testMode: true };
  const load = () => request("/api/v1/me/").then((user) => {
    if (!user.can_review) {
      $("review-access-denied").hidden = false;
      $("review-list").innerHTML = "";
      throw Object.assign(new Error("Necesitas capacidad de revisión para consultar esta página."), { handled: true });
    }
    $("review-access-denied").hidden = true;
    $("reviewer-label").textContent = user.email || "Reviewer";
    state.testMode = user.design_test_mode;
    return request("/api/v1/designs/");
  }).then((payload) => {
    const designs = (payload.results || payload).filter((design) => ["in_review", "self_review"].includes(design.status));
    if (!designs.length) {
      $("review-list").innerHTML = '<article class="card review-empty"><h2>No hay diseños pendientes.</h2><p>Cuando una pieza entre a revisión aparecerá aquí.</p></article>';
      return null;
    }
    return Promise.all(designs.map((design) => request(`/api/v1/designs/${design.id}/comments/`).then((comments) => ({ design, comments })))).then((entries) => {
      $("review-list").innerHTML = entries.map(({ design, comments }) => cardMarkup(design, comments, state.testMode)).join("");
    });
  }).catch((error) => { if (!error.handled) notice(error.message); });

  $("review-list").addEventListener("submit", (event) => {
    const form = event.target.closest("[data-comment-form]");
    if (!form) return;
    event.preventDefault();
    const data = new FormData(form);
    request(`/api/v1/designs/${form.dataset.commentForm}/comments/`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comment: data.get("comment"), version: Number(data.get("version")) || null }),
    }).then(() => { notice("Comentario guardado.", "success"); return load(); }).catch((error) => notice(error.message));
  });
  $("review-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-decision]");
    if (!button) return;
    const form = button.closest("[data-review-card]").querySelector("[data-comment-form]");
    const data = new FormData(form);
    request(`/api/v1/designs/${button.dataset.design}/review/`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: button.dataset.decision, version: Number(data.get("version")), comment: data.get("comment") }),
    }).then(() => { notice("Decisión guardada.", "success"); return load(); }).catch((error) => notice(error.message));
  });
  load();
})();
