(() => {
  const familyMeta = {
    presentation: { label: "Presentaciones (PPTX)", description: "Archivos editables para presentar ideas y propuestas", icon: "▶" },
    "html-svg": { label: "HTML/SVG", description: "Piezas digitales y sociales", icon: "◈" },
    document: { label: "Documento", description: "Archivos listos para impresión o descarga", icon: "▤" },
    "email-html": { label: "Email HTML", description: "Contenido compatible con clientes de correo", icon: "✉" },
  };
  const templateMeta = {
    "square-v1": {
      name: "Publicación cuadrada",
      description: "Formato cuadrado 1080×1080, ideal para feed de Instagram y Facebook.",
    },
    "story-v1": {
      name: "Historia",
      description: "Formato vertical largo 1080×1920, para historias de Instagram y Facebook.",
    },
    "portrait-v1": {
      name: "Publicación vertical",
      description: "Formato vertical 1080×1350, ideal para feed y anuncios.",
    },
    "brochure-a4-v1": {
      name: "Brochure de una página",
      description: "Documento A4 listo para compartir o imprimir en PDF.",
    },
    "presentation-16x9-v1": {
      name: "Presentación panorámica",
      description: "Diapositiva editable 16:9 en PowerPoint con identidad IH.",
    },
    "letter-a4-v1": {
      name: "Carta formal con membrete",
      description: "Carta A4 institucional con remitente, destinatario, cuerpo y firma.",
    },
    "announcement-a4-v1": {
      name: "Anuncio escolar",
      description: "Anuncio A4 para fechas, avisos y comunicación con la comunidad escolar.",
    },
    "flyer-a4-v1": {
      name: "Flyer informativo",
      description: "Flyer A4 con título, información principal, acción y contacto.",
    },
  };
  const materialTypeNames = {
    "social-post": "Publicación para redes sociales",
  };
  const groups = document.querySelector("#template-groups");
  const notice = document.querySelector("#templates-notice");
  const dialog = document.querySelector("#quick-design-dialog");
  const quickState = { user: null, template: null, options: null };

  const itemsFrom = (payload) => Array.isArray(payload) ? payload : (payload.results || []);
  const json = async (response) => {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "La solicitud no pudo completarse.");
    return payload;
  };
  const fillSelect = (select, items, valueKey, labelKey, placeholder) => {
    select.replaceChildren();
    if (placeholder) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = placeholder;
      select.appendChild(option);
    }
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item[valueKey];
      option.textContent = item[labelKey];
      select.appendChild(option);
    });
  };
  const renderLiveContent = () => {
    const fields = document.querySelector("#quick-content-fields");
    const headline = fields.querySelector('[name="headline"]')?.value
      || fields.querySelector("input, textarea")?.value
      || "Tu título aparecerá aquí";
    const body = fields.querySelector('[name="body"]')?.value
      || "Completa los campos para revisar la jerarquía del contenido.";
    document.querySelector("#quick-preview-headline").textContent = headline;
    document.querySelector("#quick-preview-body").textContent = body;
  };
  const populateQuickOptions = (options, { keepCountries = false } = {}) => {
    quickState.options = options;
    const country = document.querySelector("#quick-country");
    if (!keepCountries) {
      fillSelect(country, options.countries, "code", "label", "Selecciona un país");
    }
    fillSelect(
      document.querySelector("#quick-product"),
      options.products,
      "product_slug",
      "canonical_name",
      "Selecciona un producto",
    );
    const principal = options.logos.filter((logo) => logo.scope === "regional");
    fillSelect(
      document.querySelector("#quick-logo"),
      principal,
      "name",
      "brand",
      "Selecciona el logo IH",
    );
    const additional = [
      ...options.logos.filter((logo) => logo.scope !== "regional"),
      ...(options.uploaded_logos || []),
    ];
    fillSelect(
      document.querySelector("#quick-additional-logos"),
      additional,
      "name",
      "brand",
      "",
    );
  };
  const loadQuickOptions = (country = "") => fetch(
    `/api/v1/briefs/options/?country=${encodeURIComponent(country)}`,
  ).then(json).then((options) => populateQuickOptions(options, { keepCountries: Boolean(country) }));
  const openQuickEditor = (template) => {
    if (template.key === "school-kit-v1") {
      window.location.href = "school-kit.html";
      return;
    }
    quickState.template = template;
    const friendly = templateMeta[template.key] || { name: "Usar plantilla" };
    document.querySelector("#quick-design-title").textContent = friendly.name;
    document.querySelector("#quick-design-status").textContent = "";
    document.querySelector("#quick-rendered-preview").hidden = true;
    document.querySelector("#quick-download").hidden = true;
    const fields = document.querySelector("#quick-content-fields");
    fields.replaceChildren();
    template.required_fields.forEach((field, index) => {
      const label = document.createElement("label");
      label.textContent = template.field_labels?.[field] || field;
      const input = field === "body" || field === "content"
        ? document.createElement("textarea")
        : document.createElement("input");
      input.name = field;
      input.required = true;
      input.autocomplete = "off";
      input.addEventListener("input", renderLiveContent);
      label.appendChild(input);
      fields.appendChild(label);
      if (index === 0) window.setTimeout(() => input.focus(), 0);
    });
    renderLiveContent();
    dialog.showModal();
    loadQuickOptions().then(() => {
      document.querySelector("#quick-country").value = "MX";
      return loadQuickOptions("MX");
    }).catch((error) => {
      document.querySelector("#quick-design-status").textContent = error.message;
    });
  };
  const dimensionLabel = (dimensions) => {
    if (Array.isArray(dimensions)) return `${dimensions[0]} × ${dimensions[1]} px`;
    if (dimensions.page_size) {
      return `${dimensions.page_size} · ${dimensions.width_mm} × ${dimensions.height_mm} mm`;
    }
    return Object.entries(dimensions).map(([name, value]) => (
      `${name}: ${Array.isArray(value) ? `${value[0]} × ${value[1]} px` : value}`
    )).join(" · ");
  };

  const templateRow = (template) => {
    const row = document.createElement("div");
    row.className = "template-row";
    const info = document.createElement("div");
    const name = document.createElement("strong");
    const friendly = templateMeta[template.key] || {
      name: "Plantilla disponible",
      description: "Formato listo para personalizar con contenido autorizado.",
    };
    name.textContent = friendly.name;
    const description = document.createElement("p");
    description.className = "template-row__description";
    description.textContent = friendly.description;
    const dimensions = document.createElement("span");
    dimensions.textContent = `${dimensionLabel(template.dimensions)} · v${template.version}`;
    dimensions.textContent += ` · ${template.key}`;
    info.append(name, description, dimensions);
    const outputs = document.createElement("div");
    outputs.className = "template-row__outputs";
    outputs.textContent = template.output_formats.join(" / ");
    row.append(info, outputs);
    if (quickState.user?.can_create_briefs) {
      const actions = document.createElement("div");
      actions.className = "template-row__actions";
      const useButton = document.createElement("button");
      useButton.className = "template-use-button";
      useButton.type = "button";
      useButton.textContent = "Usar esta plantilla";
      useButton.addEventListener("click", () => openQuickEditor(template));
      actions.appendChild(useButton);
      row.appendChild(actions);
    }
    return row;
  };

  const materialCard = (materialType, templates) => {
    const card = document.createElement("article");
    card.className = "material-card";
    const top = document.createElement("div");
    top.className = "material-card__top";
    const title = document.createElement("h3");
    title.textContent = materialTypeNames[materialType.slug] || materialType.name;
    const channel = document.createElement("span");
    channel.className = "material-card__channel";
    channel.textContent = materialType.channel;
    top.append(title, channel);
    const formats = document.createElement("p");
    formats.className = "material-card__formats";
    formats.textContent = materialType.supported_formats.length
      ? `Formatos: ${materialType.supported_formats.join(", ")}`
      : "Formatos definidos por template";
    const list = document.createElement("div");
    list.className = "template-list";
    if (templates.length) list.append(...templates.map(templateRow));
    else {
      const empty = document.createElement("p");
      empty.className = "template-empty";
      empty.textContent = "No hay templates activos para este tipo de material.";
      list.appendChild(empty);
    }
    card.append(top, formats, list);
    return card;
  };

  const familySection = (family, materialTypes, templates) => {
    const meta = familyMeta[family] || { label: family, description: "Familia de render", icon: "◇" };
    const section = document.createElement("section");
    section.className = "template-family";
    const header = document.createElement("div");
    header.className = "template-family__header";
    const icon = document.createElement("span");
    icon.className = "template-family__icon";
    icon.textContent = meta.icon;
    const copy = document.createElement("div");
    const heading = document.createElement("h2");
    heading.textContent = meta.label;
    const description = document.createElement("p");
    description.textContent = meta.description;
    copy.append(heading, description);
    header.append(icon, copy);
    const grid = document.createElement("div");
    grid.className = "material-grid";
    grid.append(...materialTypes.map((materialType) => materialCard(
      materialType,
      templates.filter((template) => template.material_type === materialType.id && template.active),
    )));
    section.append(header, grid);
    return section;
  };

  document.querySelector("#menu-toggle")?.addEventListener("click", () => {
    document.querySelector("#sidebar")?.classList.toggle("sidebar--open");
  });
  document.querySelector("#quick-design-close")?.addEventListener("click", () => dialog.close());
  document.querySelector("#quick-country")?.addEventListener("change", (event) => {
    loadQuickOptions(event.target.value).catch((error) => {
      document.querySelector("#quick-design-status").textContent = error.message;
    });
  });
  document.querySelector("#quick-design-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const status = document.querySelector("#quick-design-status");
    const fields = Object.fromEntries(
      [...document.querySelectorAll("#quick-content-fields input, #quick-content-fields textarea")]
        .map((input) => [input.name, input.value]),
    );
    const additionalLogoKeys = [...document.querySelector("#quick-additional-logos").selectedOptions]
      .map((option) => option.value);
    const payload = {
      template_key: quickState.template.key,
      country: document.querySelector("#quick-country").value,
      product_slug: document.querySelector("#quick-product").value,
      brand_logo_key: document.querySelector("#quick-logo").value,
      additional_logo_keys: additionalLogoKeys,
      ...fields,
    };
    status.textContent = "Guardando diseño…";
    fetch("/api/v1/materials/quick-design/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(json).then((result) => {
      status.replaceChildren("Diseño guardado. ");
      const link = document.createElement("a");
      link.href = "review.html";
      link.textContent = "Ver en revisiones";
      status.appendChild(link);
      const frame = document.querySelector("#quick-rendered-preview");
      const download = document.querySelector("#quick-download");
      if (result.preview.html) {
        frame.srcdoc = result.preview.html;
        frame.hidden = false;
      } else {
        download.href = result.preview.pdf_url || result.preview.pptx_url;
        download.textContent = result.preview.pdf_url ? "Abrir PDF" : "Descargar PowerPoint";
        download.hidden = false;
      }
    }).catch((error) => {
      status.textContent = error.message;
    });
  });

  Promise.all([
    fetch("/api/v1/material-types/").then((response) => {
      if (!response.ok) throw new Error("material types unavailable");
      return response.json();
    }),
    fetch("/api/v1/material-templates/").then((response) => {
      if (!response.ok) throw new Error("templates unavailable");
      return response.json();
    }),
    fetch("/api/v1/me/")
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null),
  ])
    .then(([typePayload, templatePayload, user]) => {
      quickState.user = user;
      let materialTypes = itemsFrom(typePayload).filter((item) => item.active);
      let templates = itemsFrom(templatePayload).filter((item) => item.active);
      const canSeeSocial = Boolean(user?.is_admin || user?.roles?.includes("marketing"));
      if (!canSeeSocial) {
        const socialType = materialTypes.find((item) => item.slug === "social-post");
        const generalId = "general-formats";
        const generalTemplates = socialType ? templates
          .filter((template) => (
            template.material_type === socialType.id
            && ["square-v1", "portrait-v1"].includes(template.key)
          ))
          .map((template) => ({ ...template, material_type: generalId })) : [];
        materialTypes = materialTypes.filter((item) => item.slug !== "social-post");
        templates = templates.filter((template) => template.material_type !== socialType?.id);
        if (generalTemplates.length) {
          materialTypes.push({
            id: generalId,
            slug: "general-formats",
            name: "Formatos generales — cuadrado y vertical",
            renderer_family: "html-svg",
            channel: "general",
            supported_formats: ["square", "portrait"],
            active: true,
          });
          templates.push(...generalTemplates);
        }
      }
      const families = [...new Set(materialTypes.map((item) => item.renderer_family))];
      groups.append(...families.map((family) => familySection(
        family,
        materialTypes.filter((item) => item.renderer_family === family),
        templates,
      )));
      document.querySelector("#template-total").textContent = `${templates.length} templates activos`;
      notice.hidden = true;
    })
    .catch(() => {
      notice.textContent = "No pudimos cargar las plantillas. Intenta de nuevo más tarde.";
      document.querySelector("#template-total").textContent = "No disponible";
    });
})();
