(() => {
  const ROLES = ["platform_admin", "marketing", "designer", "reviewer", "viewer"];
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
  const cookie = (name) => document.cookie.split("; ").find((item) => item.startsWith(`${name}=`))?.split("=")[1] || "";
  const json = async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const fieldError = Object.values(body).flat()[0];
      throw new Error(body.detail || fieldError || "La solicitud no pudo completarse.");
    }
    return body;
  };
  const request = (url, options = {}) => {
    const headers = new Headers(options.headers || {});
    if (options.method && options.method !== "GET") headers.set("X-CSRFToken", decodeURIComponent(cookie("csrftoken")));
    return fetch(url, { ...options, headers }).then(json);
  };
  const notice = (message, type = "error") => {
    $("admin-notice").textContent = message;
    $("admin-notice").className = `notice notice--${type}`;
  };
  const renderRows = (selector, rows, empty, columns, render) => {
    $(selector).innerHTML = rows.length ? rows.map(render).join("") : `<tr><td colspan="${columns}">${empty}</td></tr>`;
  };
  const items = (payload) => payload.results || payload;
  const csv = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);

  const roleControls = (user) => {
    const options = ROLES.map((role) => `<option value="${role}">${role}</option>`).join("");
    return `<div class="row-actions"><select data-role-user="${user.id}">${options}</select><button class="button button--small" data-role-action="add" data-user="${user.id}">Agregar</button><button class="button button--small" data-role-action="remove" data-user="${user.id}">Quitar</button><button class="button button--small" data-user-active="${user.id}" data-active="${!user.is_active}">${user.is_active ? "Desactivar" : "Reactivar"}</button></div>`;
  };
  const renderUsers = (payload) => {
    const users = items(payload);
    renderRows("user-table", users, "No hay usuarios corporativos.", 5, (user) => {
      const roles = user.roles.length ? user.roles.map((role) => `<span class="role-badge">${escapeHtml(role)}</span>`).join(" ") : "—";
      return `<tr><td>${escapeHtml(user.username)}</td><td>${escapeHtml(user.email)}</td><td>${roles}</td><td class="${user.is_active ? "status" : "status status--inactive"}">${user.is_active ? "Activo" : "Inactivo"}</td><td>${roleControls(user)}</td></tr>`;
    });
    $("password-user").innerHTML = users.map((user) => `<option value="${user.id}">${escapeHtml(user.username)} · ${escapeHtml(user.email)}</option>`).join("");
  };
  const renderMaterialTypes = (payload) => {
    const materialTypes = items(payload);
    renderRows("material-type-table", materialTypes, "No hay tipos de material.", 4, (type) => `<tr><td>${escapeHtml(type.slug)}</td><td>${escapeHtml(type.name)}</td><td>${escapeHtml(type.renderer_family)}</td><td class="status">${type.active ? "Sí" : "No"}</td></tr>`);
    $("template-material-type").innerHTML = materialTypes.map((type) => `<option value="${type.id}">${escapeHtml(type.slug)}</option>`).join("");
  };
  const renderMaterialTemplates = (payload, materialTypes) => {
    const typeNames = Object.fromEntries(items(materialTypes).map((type) => [type.id, type.slug]));
    renderRows("material-template-table", items(payload), "No hay templates.", 4, (template) => `<tr><td>${escapeHtml(template.key)}</td><td>${escapeHtml(typeNames[template.material_type] || template.material_type)}</td><td>${escapeHtml(template.output_formats.join(", "))}</td><td class="status">${template.active ? "Sí" : "No"}</td></tr>`);
  };

  const load = () => request("/api/v1/me/").then((user) => {
    if (!user.is_admin) {
      $("access-denied").hidden = false;
      $("admin-content").hidden = true;
      return null;
    }
    return Promise.all([
      request("/api/v1/briefs/"), request("/api/v1/uploaded-logos/"),
      request("/api/v1/artwork-references/knowledge/?limit=1"), request("/api/v1/security/users/"),
      request("/api/v1/material-types/"), request("/api/v1/material-templates/"),
    ]);
  }).then((payloads) => {
    if (!payloads) return;
    const [briefs, logos, references, users, materialTypes, materialTemplates] = payloads;
    $("access-denied").hidden = true;
    $("admin-content").hidden = false;
    const briefItems = items(briefs);
    const logoItems = items(logos);
    $("stat-briefs").textContent = briefs.count ?? briefItems.length;
    $("stat-logos").textContent = logos.count ?? logoItems.length;
    $("stat-references").textContent = references.summary?.total_assets ?? "—";
    $("stat-ready").textContent = briefItems.filter((brief) => ["test_ready", "completed"].includes(brief.status)).length;
    renderRows("brief-table", briefItems.slice(0, 20), "Todavía no hay briefs.", 4, (brief) => `<tr><td>${escapeHtml(brief.title)}</td><td>${escapeHtml(brief.product_slug || "—")}</td><td class="status">${escapeHtml(brief.status)}</td><td>${brief.test_number || "—"}</td></tr>`);
    renderRows("logo-table", logoItems.slice(0, 20), "Todavía no hay logos aportados.", 3, (logo) => `<tr><td>${escapeHtml(logo.name)}</td><td>${escapeHtml(logo.country || "—")}</td><td class="status">${escapeHtml(logo.status)}</td></tr>`);
    renderUsers(users);
    renderMaterialTypes(materialTypes);
    renderMaterialTemplates(materialTemplates, materialTypes);
  }).catch((error) => notice(error.message));

  $("user-table").addEventListener("click", (event) => {
    const roleButton = event.target.closest("[data-role-action]");
    const activeButton = event.target.closest("[data-user-active]");
    if (!roleButton && !activeButton) return;
    let operation;
    if (roleButton) {
      const userId = roleButton.dataset.user;
      const role = document.querySelector(`[data-role-user="${userId}"]`).value;
      operation = request(`/api/v1/security/users/${userId}/roles/`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role, action: roleButton.dataset.roleAction }),
      });
    } else {
      operation = request(`/api/v1/security/users/${activeButton.dataset.userActive}/`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: activeButton.dataset.active === "true" }),
      });
    }
    operation.then(() => { notice("Usuario actualizado.", "success"); return load(); }).catch((error) => notice(error.message));
  });

  $("user-create-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    request("/api/v1/security/users/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: form.get("username"),
        email: form.get("email"),
        password: form.get("password"),
        roles: form.getAll("roles"),
      }),
    }).then(() => {
      event.currentTarget.reset();
      notice("Usuario creado.", "success");
      return load();
    }).catch((error) => notice(error.message));
  });

  $("password-reset-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    request(`/api/v1/security/users/${form.get("user_id")}/password/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: form.get("password") }),
    }).then(() => {
      event.currentTarget.reset();
      notice("Contraseña actualizada.", "success");
      return load();
    }).catch((error) => notice(error.message));
  });

  $("material-type-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    request("/api/v1/material-types/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      slug: form.get("slug"), name: form.get("name"), renderer_family: form.get("renderer_family"), channel: form.get("channel"), schema_version: "1.0.0", supported_formats: csv(form.get("supported_formats")), priority_product_slugs: [], product_scope: "all_catalog", active: form.has("active"),
    }) }).then(() => { event.currentTarget.reset(); notice("Tipo de material creado.", "success"); return load(); }).catch((error) => notice(error.message));
  });

  $("material-template-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    let dimensions;
    try { dimensions = JSON.parse(form.get("dimensions")); } catch { notice("Dimensiones debe ser JSON válido."); return; }
    request("/api/v1/material-templates/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
      material_type: Number(form.get("material_type")), key: form.get("key"), version: form.get("version"), dimensions, output_formats: csv(form.get("output_formats")), required_fields: csv(form.get("required_fields")), constraints: {}, active: form.has("active"),
    }) }).then(() => { event.currentTarget.reset(); notice("Template creado.", "success"); return load(); }).catch((error) => notice(error.message));
  });

  $("refresh").addEventListener("click", load);
  load();
})();
