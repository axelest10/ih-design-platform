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
  };
  const materialTypeNames = {
    "social-post": "Publicación para redes sociales",
  };
  const groups = document.querySelector("#template-groups");
  const notice = document.querySelector("#templates-notice");

  const itemsFrom = (payload) => Array.isArray(payload) ? payload : (payload.results || []);
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
