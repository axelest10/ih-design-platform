(() => {
  const state = { options: null, user: null };
  const $ = (id) => document.getElementById(id);
  const notice = (message, type = "success") => {
    const element = $("notice");
    element.textContent = message;
    element.className = `notice notice--${type}`;
  };
  const json = async (response) => {
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw Object.assign(new Error(body.detail || "La solicitud no pudo completarse."), body, {
        status: response.status,
      });
    }
    return body;
  };
  const isAuthError = (error) => error?.status === 401 || error?.status === 403;
  const setBriefFormDisabled = (disabled) => {
    $("brief-form").querySelectorAll("input, select, textarea, button").forEach((control) => {
      control.disabled = disabled;
    });
  };
  const showUnauthenticatedState = () => {
    state.user = null;
    $("user-label").textContent = "No has iniciado sesión";
    $("role-label").textContent = "Acceso restringido";
    setBriefFormDisabled(true);
    notice("Inicia sesión con tu correo corporativo para crear briefs.", "error");
    const loginLink = document.createElement("a");
    loginLink.href = "login.html";
    loginLink.textContent = "Iniciar sesión";
    $("notice").append(" ", loginLink);
  };
  const handleOptionsError = (error) => {
    if (isAuthError(error)) {
      showUnauthenticatedState();
      return;
    }
    notice("No pudimos cargar las opciones del brief. Verifica que la API esté disponible.", "error");
  };

  const fillSelect = (select, items, valueKey, labelKey, placeholder) => {
    select.innerHTML = `<option value="">${placeholder}</option>`;
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item[valueKey];
      option.textContent = item[labelKey];
      select.appendChild(option);
    });
  };

  const renderProductPreview = () => {
    const product = state.options?.products.find((item) => item.product_slug === $("product_slug").value);
    const preview = $("product-preview");
    if (!product || !product.authorized_color?.primary_hex) {
      preview.className = "product-preview product-preview--empty";
      preview.textContent = "Selecciona un producto para ver su color.";
      return;
    }
    const productClass = product.product_slug.replace(/[^a-z0-9-]/g, "");
    preview.className = `product-preview product-preview--${productClass}`;
    preview.innerHTML = `<strong>${product.canonical_name}</strong><span>${product.authorized_color.primary_hex} · color autorizado</span>`;
  };

  const loadOptions = () => fetch(`/api/v1/briefs/options/?country=${encodeURIComponent($("country").value)}`).then(json).then((options) => {
    state.options = options;
    const localLogos = options.logos.filter((logo) => logo.scope === "regional");
    fillSelect($("brand_logo_key"), localLogos, "name", "brand", "Selecciona el logo IH de la sede");
    fillSelect($("product_slug"), options.products, "product_slug", "canonical_name", "Selecciona un producto");
    const logoContainer = $("additional-logos");
    logoContainer.innerHTML = "";
    [...options.logos.filter((logo) => logo.scope !== "regional"), ...(options.uploaded_logos || [])].forEach((logo) => {
      const label = document.createElement("label");
      label.className = "checkbox-item";
      label.innerHTML = `<input type="checkbox" value="${logo.name}" /> <span>${logo.brand || logo.name}</span>`;
      logoContainer.appendChild(label);
    });
    if (!logoContainer.children.length) logoContainer.innerHTML = "<small>No hay logos adicionales disponibles para esta selección.</small>";
    renderProductPreview();
  }).catch(handleOptionsError);

  const loadInitialOptions = () => fetch("/api/v1/briefs/options/").then(json).then((options) => {
    state.options = options;
    fillSelect($("country"), options.countries, "code", "label", "Selecciona un país");
    $("country").value = "MX";
    return loadOptions();
  }).catch(handleOptionsError);

  const uploadLogo = () => {
    const file = $("logo-file").files[0];
    if (!file) return Promise.resolve(null);
    const body = new FormData();
    body.append("file", file);
    body.append("name", $("logo-name").value || file.name);
    body.append("country", $("country").value);
    body.append("logo_type", $("logo-type").value);
    body.append("usage_notes", $("logo-notes").value);
    return fetch("/api/v1/uploaded-logos/", { method: "POST", body }).then(json);
  };

  const createBrief = async (event) => {
    event.preventDefault();
    $("form-status").textContent = "Guardando…";
    try {
      const uploaded = $("upload-logo-toggle").checked ? await uploadLogo() : null;
      const selectedAdditional = [...document.querySelectorAll("#additional-logos input:checked")].map((input) => input.value);
      if (uploaded) selectedAdditional.push(`uploaded:${uploaded.key}`);
      const data = {
        title: $("requested_message").value.slice(0, 180),
        format: $("format").value,
        country: $("country").value,
        product_slug: $("product_slug").value,
        brand_logo_key: $("brand_logo_key").value,
        additional_logo_keys: selectedAdditional,
        audience: $("audience").value,
        objective: $("objective").value,
        requested_message: $("requested_message").value,
        language: $("language").value,
        channel: $("channel").value,
        visual_reference_urls: $("visual_reference_url").value ? [$("visual_reference_url").value] : [],
        brief_data: {
          audience_need: $("audience_need").value,
          logo_variant: $("logo_variant").value,
          campaign_info: $("campaign_info").value,
          required_information: $("required_information").value,
          cta: $("cta").value,
          cta_destination: $("cta_destination").value,
          tone: $("tone").value,
          visual_elements: $("visual_elements").value,
        },
      };
      const response = await fetch("/api/v1/briefs/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      const brief = await json(response);
      const referenceFile = $("visual_reference_file").files[0];
      if (referenceFile) {
        const referenceBody = new FormData();
        referenceBody.append("brief", brief.id);
        referenceBody.append("file", referenceFile);
        referenceBody.append("caption", "Referencia visual del brief");
        await fetch("/api/v1/brief-reference-uploads/", { method: "POST", body: referenceBody }).then(json);
      }
      $("form-status").textContent = "Brief guardado";
      notice(`Brief guardado correctamente. ID: ${brief.id}`);
    } catch (error) {
      $("form-status").textContent = "Revisa los campos";
      notice(error?.detail || error?.country || "No pudimos guardar el brief.", "error");
    }
  };

  const loadUser = () => fetch("/api/v1/me/").then(json).then((user) => {
    state.user = user;
    setBriefFormDisabled(false);
    $("user-label").textContent = user.email || "Sesión local";
    $("role-label").textContent = user.is_admin ? "Administrador" : (user.roles[0] || "Usuario");
    if (user.is_admin) $("admin-panel").hidden = false;
    return fetch("/api/v1/briefs/").then(json);
  }).then((briefs) => {
    $("brief-count").textContent = briefs.count ?? briefs.length ?? "—";
    return true;
  }).catch((error) => {
    if (isAuthError(error)) {
      showUnauthenticatedState();
    } else {
      $("user-label").textContent = "Perfil no disponible";
      notice("No pudimos verificar tu perfil. Intenta de nuevo cuando la API esté disponible.", "error");
    }
    return false;
  });

  const loadAdminStats = () => fetch("/api/v1/uploaded-logos/").then(json).then((logos) => { $("logo-count").textContent = logos.count ?? logos.length ?? "—"; }).catch(() => {});

  $("country").addEventListener("change", loadOptions);
  $("product_slug").addEventListener("change", renderProductPreview);
  $("upload-logo-toggle").addEventListener("change", (event) => { $("upload-logo-fields").hidden = !event.target.checked; });
  $("brief-form").addEventListener("submit", createBrief);
  $("refresh-admin").addEventListener("click", () => {
    loadUser().then((authenticated) => {
      if (!authenticated) return;
      loadInitialOptions();
      loadAdminStats();
    });
  });
  loadUser().then((authenticated) => {
    if (!authenticated) return;
    loadInitialOptions();
    loadAdminStats();
  });
})();
