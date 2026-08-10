(() => {
  const familyMeta = {
    "html-svg": { label: "HTML/SVG", description: "Piezas digitales y sociales", icon: "◈" },
    document: { label: "Documento", description: "Archivos listos para impresión o descarga", icon: "▤" },
    "email-html": { label: "Email HTML", description: "Contenido compatible con clientes de correo", icon: "✉" },
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
    name.textContent = template.key;
    const dimensions = document.createElement("span");
    dimensions.textContent = `${dimensionLabel(template.dimensions)} · v${template.version}`;
    info.append(name, dimensions);
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
    title.textContent = materialType.name;
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
  ])
    .then(([typePayload, templatePayload]) => {
      const materialTypes = itemsFrom(typePayload).filter((item) => item.active);
      const templates = itemsFrom(templatePayload).filter((item) => item.active);
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
