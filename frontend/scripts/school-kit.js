(() => {
  const state = { type: null, options: null, bundles: [], currentId: null };
  const $ = (id) => document.getElementById(id);
  const json = async (response) => {
    const body = await response.json();
    if (!response.ok) throw body;
    return body;
  };
  const notice = (message, type = "success") => {
    $("notice").textContent = message;
    $("notice").className = `notice notice--${type}`;
  };

  const selectedValues = (selector) => [...document.querySelectorAll(`${selector} input:checked`)].map((input) => input.value);

  const renderProducts = () => {
    const target = $("products");
    target.innerHTML = "";
    (state.type?.available_products || []).forEach((product) => {
      const label = document.createElement("label");
      label.className = "check-item";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = product.product_slug;
      input.dataset.product = product.product_slug;
      const text = document.createElement("span");
      text.textContent = product.needs_confirmation
        ? `${product.canonical_name} · color por confirmar`
        : product.canonical_name;
      label.append(input, text);
      target.appendChild(label);
    });
  };

  const renderLogos = () => {
    const target = $("additional-logos");
    target.innerHTML = "";
    const logos = [...(state.options?.logos || []).filter((logo) => logo.scope !== "regional"), ...(state.options?.uploaded_logos || [])];
    logos.forEach((logo) => {
      const label = document.createElement("label");
      label.className = "check-item";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = logo.name;
      input.dataset.logo = logo.name;
      const text = document.createElement("span");
      text.textContent = logo.brand || logo.name;
      label.append(input, text);
      target.appendChild(label);
    });
    if (!logos.length) target.innerHTML = '<span class="muted">No hay logos secundarios disponibles.</span>';
  };

  const renderDeliverables = () => {
    $("deliverables").innerHTML = (state.type?.default_deliverables || []).map((item) => `<li><strong>${item.label}</strong><span>${item.template_key}</span></li>`).join("");
  };

  const loadOptions = async () => {
    const country = encodeURIComponent($("country").value || "MX");
    const [types, options] = await Promise.all([
      fetch(`/api/v1/material-types/?country=${country}`).then(json),
      fetch(`/api/v1/briefs/options/?country=${country}`).then(json),
    ]);
    state.type = (Array.isArray(types) ? types : types.results).find((item) => item.slug === "school-kit");
    state.options = options;
    const logoSelect = $("brand_logo_key");
    logoSelect.innerHTML = '<option value="">Selecciona el logo IH</option>';
    (options.logos || []).filter((logo) => logo.scope === "regional").forEach((logo) => {
      const option = document.createElement("option");
      option.value = logo.name;
      option.textContent = logo.brand || logo.name;
      logoSelect.appendChild(option);
    });
    renderProducts();
    renderLogos();
    renderDeliverables();
  };

  const formData = () => ({
    material_type: state.type.id,
    name: $("name").value.trim(),
    country: $("country").value,
    product_slugs: selectedValues("#products"),
    brief_context: {
      brand_logo_key: $("brand_logo_key").value,
      additional_logo_keys: selectedValues("#additional-logos"),
      headline: $("headline").value.trim(),
      body: $("body").value.trim(),
      cta: $("cta").value.trim(),
      audience: $("audience").value.trim(),
      objective: $("objective").value.trim(),
      eyebrow: $("eyebrow_text").value.trim(),
      channel: $("channel").value.trim(),
    },
  });

  const saveBundle = async () => {
    const data = formData();
    if (!data.product_slugs.length) throw { detail: "Selecciona al menos un producto." };
    const url = state.currentId ? `/api/v1/material-bundles/${state.currentId}/` : "/api/v1/material-bundles/";
    const response = await window.authenticatedFetch(url, { method: state.currentId ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
    const bundle = await json(response);
    state.currentId = bundle.id;
    await loadBundles();
    return bundle;
  };

  const generateBundle = async () => {
    const bundle = await saveBundle();
    const response = await window.authenticatedFetch(
      `/api/v1/material-bundles/${bundle.id}/generate/`,
      { method: "POST" },
    );
    const generated = await json(response);
    state.currentId = generated.id;
    await loadBundles();
    notice(`Paquete generado: ${generated.items.length} piezas listas para revisión.`);
  };

  const renderBundles = () => {
    const target = $("bundles");
    if (!state.bundles.length) { target.innerHTML = '<p class="muted">Todavía no hay paquetes guardados.</p>'; return; }
    target.innerHTML = "";
    state.bundles.forEach((bundle) => {
      const card = document.createElement("article");
      card.className = "bundle-item";
      const heading = document.createElement("div");
      heading.className = "bundle-heading";
      heading.innerHTML = `<div><strong></strong><span></span></div><button class="button button--quiet" data-edit="${bundle.id}">Editar</button>`;
      heading.querySelector("strong").textContent = bundle.name;
      heading.querySelector("span").textContent = `${bundle.country || "LATAM"} · ${bundle.status}`;
      card.appendChild(heading);
      (bundle.items || []).forEach((item) => {
        const row = document.createElement("div");
        row.className = "piece-row";
        const design = item.design;
        row.innerHTML = `<div><strong></strong><span></span></div>`;
        row.querySelector("strong").textContent = item.deliverable_key;
        const integrationStatus = design?.claude_review?.integration_status;
        row.querySelector("span").textContent = design
          ? `${design.status} · Claude: ${design.claude_review_status || "pending"}${integrationStatus ? ` · Integración: ${integrationStatus}` : ""}`
          : "Sin diseño";
        if (design) {
          const controls = document.createElement("div");
          controls.className = "review-controls";
          controls.innerHTML = `<input placeholder="Nota de revisión de Claude" data-report="${design.id}" /><button class="button button--pass" data-review="pass" data-design="${design.id}">Pass</button><button class="button button--change" data-review="needs_changes" data-design="${design.id}">Needs changes</button>`;
          row.appendChild(controls);
        }
        card.appendChild(row);
      });
      target.appendChild(card);
    });
  };

  const loadBundles = async () => {
    state.bundles = await fetch("/api/v1/material-bundles/").then(json);
    renderBundles();
  };

  const loadBundleIntoForm = (id) => {
    const bundle = state.bundles.find((item) => item.id === id);
    if (!bundle) return;
    state.currentId = bundle.id;
    const context = bundle.brief_context || {};
    $("name").value = bundle.name || "";
    $("country").value = bundle.country || "MX";
    $("brand_logo_key").value = context.brand_logo_key || "";
    ["audience", "objective", "headline", "body", "cta"].forEach((key) => { $(key).value = context[key] || ""; });
    $("eyebrow_text").value = context.eyebrow || "";
    $("channel").value = context.channel || "instagram";
    document.querySelectorAll("#products input").forEach((input) => { input.checked = bundle.product_slugs.includes(input.value); });
    document.querySelectorAll("#additional-logos input").forEach((input) => { input.checked = (context.additional_logo_keys || []).includes(input.value); });
    notice("Paquete cargado para edición.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  $("kit-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("form-status").textContent = "Guardando…";
    try { await saveBundle(); $("form-status").textContent = "Guardado"; notice("Paquete guardado. Todavía puedes editarlo antes de generar."); }
    catch (error) { $("form-status").textContent = "Revisa los campos"; notice(error.detail || "No pudimos guardar el paquete.", "error"); }
  });
  $("generate").addEventListener("click", async () => {
    $("form-status").textContent = "Generando…";
    try { await generateBundle(); $("form-status").textContent = "Generado"; }
    catch (error) { $("form-status").textContent = "No generado"; notice(error.detail || "No pudimos generar las piezas.", "error"); }
  });
  $("country").addEventListener("change", () => loadOptions().catch(() => notice("No pudimos cargar las opciones.", "error")));
  $("refresh").addEventListener("click", () => loadBundles().catch(() => notice("No pudimos cargar los paquetes.", "error")));
  $("reset").addEventListener("click", () => { state.currentId = null; $("kit-form").reset(); $("country").value = "MX"; loadOptions(); });
  $("bundles").addEventListener("click", async (event) => {
    const edit = event.target.closest("[data-edit]");
    if (edit) { loadBundleIntoForm(edit.dataset.edit); return; }
    const review = event.target.closest("[data-review]");
    if (!review) return;
    const report = document.querySelector(`[data-report="${review.dataset.design}"]`)?.value || "Revisión registrada desde el panel school-kit.";
    try {
      await window.authenticatedFetch(`/api/v1/designs/${review.dataset.design}/claude-review/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision: review.dataset.review, report: { summary: report, source: "claude" } }) }).then(json);
      await loadBundles();
      notice("Revisión de Claude registrada para la pieza.");
    } catch (error) { notice(error.detail || "No pudimos registrar la revisión.", "error"); }
  });

  (async () => {
    try {
      const countries = await fetch("/api/v1/briefs/options/").then(json);
      $("country").innerHTML = countries.countries.map((item) => `<option value="${item.code}">${item.label}</option>`).join("");
      $("country").value = "MX";
      await loadOptions();
      await loadBundles();
    } catch (error) { notice(error.detail || "No pudimos cargar el módulo school-kit.", "error"); }
  })();
})();
