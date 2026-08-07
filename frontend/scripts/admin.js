(() => {
  const $ = (id) => document.getElementById(id);
  const json = (response) => response.ok ? response.json() : Promise.reject(new Error("No autorizado"));
  const notice = (message) => { $("admin-notice").textContent = message; $("admin-notice").className = "notice notice--error"; };
  const renderRows = (selector, rows, empty, render) => { const target = $(selector); target.innerHTML = rows.length ? rows.map(render).join("") : `<tr><td colspan="4">${empty}</td></tr>`; };
  const load = () => Promise.all([fetch("/api/v1/me/").then(json), fetch("/api/v1/briefs/").then(json), fetch("/api/v1/uploaded-logos/").then(json), fetch("/api/v1/artwork-references/knowledge/?limit=1").then(json)]).then(([user, briefs, logos, references]) => {
    if (!user.is_admin) { $("access-denied").hidden = false; return; }
    $("admin-content").hidden = false;
    const briefItems = briefs.results || briefs;
    const logoItems = logos.results || logos;
    $("stat-briefs").textContent = briefs.count ?? briefItems.length;
    $("stat-logos").textContent = logos.count ?? logoItems.length;
    $("stat-references").textContent = references.summary?.total_assets ?? "—";
    $("stat-ready").textContent = briefItems.filter((brief) => ["test_ready", "completed"].includes(brief.status)).length;
    renderRows("brief-table", briefItems.slice(0, 20), "Todavía no hay briefs.", (brief) => `<tr><td>${brief.title}</td><td>${brief.product_slug || "—"}</td><td class="status">${brief.status}</td><td>${brief.test_number || "—"}</td></tr>`);
    renderRows("logo-table", logoItems.slice(0, 20), "Todavía no hay logos aportados.", (logo) => `<tr><td>${logo.name}</td><td>${logo.country || "—"}</td><td class="status">${logo.status}</td></tr>`);
  }).catch(() => notice("No se pudo cargar el panel. Comprueba la sesión corporativa."));
  $("refresh").addEventListener("click", load);
  load();
})();
