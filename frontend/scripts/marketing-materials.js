(() => {
  const state = { assets: [], brand: "", country: "", category: "" };
  const brandNames = { ih: "International House", ielts: "IELTS" };
  const countryNames = { MX: "México", CO: "Colombia", PE: "Perú", CL: "Chile", global: "Global" };
  const categoryNames = {
    foto_perfil: "Fotos de perfil",
    background_computadora: "Fondos para computadora",
    background_celular: "Fondos para celular",
    zoom_background: "Fondos de Zoom",
    firma_electronica: "Firmas electrónicas",
    banner_linkedin: "Banners de LinkedIn",
    template_ppt: "Templates de PowerPoint",
  };
  const imageExtensions = new Set(["png", "jpg", "jpeg", "webp"]);
  const groups = document.querySelector("#marketing-groups");
  const notice = document.querySelector("#marketing-notice");
  const extension = (asset) => String(asset.file || "").split(".").pop().toLowerCase();
  const assetCard = (asset) => {
    const card = document.createElement("article");
    card.className = "marketing-card";
    const preview = document.createElement("div");
    preview.className = "marketing-card__preview";
    if (imageExtensions.has(extension(asset))) {
      const image = document.createElement("img");
      image.src = asset.file_url;
      image.alt = asset.label;
      image.loading = "lazy";
      preview.appendChild(image);
    } else {
      const fileType = document.createElement("span");
      fileType.textContent = extension(asset).toUpperCase();
      preview.appendChild(fileType);
    }
    const body = document.createElement("div");
    body.className = "marketing-card__body";
    const title = document.createElement("h4");
    title.textContent = asset.label;
    const download = document.createElement("a");
    download.href = asset.file_url;
    download.textContent = "Descargar ↓";
    download.target = "_blank";
    download.rel = "noopener";
    body.append(title, download);
    card.append(preview, body);
    return card;
  };
  const render = () => {
    const visible = state.assets.filter((asset) => (
      (!state.brand || asset.brand === state.brand)
      && (!state.country || (asset.country || "global") === state.country)
      && (!state.category || asset.category === state.category)
    ));
    groups.replaceChildren();
    ["ih", "ielts"].forEach((brand) => {
      const brandAssets = visible.filter((asset) => asset.brand === brand);
      if (!brandAssets.length) return;
      const section = document.createElement("section");
      section.className = "marketing-brand";
      const heading = document.createElement("h2");
      heading.textContent = brandNames[brand];
      section.appendChild(heading);
      const countries = [...new Set(brandAssets.map((asset) => asset.country || "global"))].sort();
      countries.forEach((country) => {
        const countrySection = document.createElement("section");
        countrySection.className = "marketing-country";
        const countryHeading = document.createElement("h3");
        countryHeading.textContent = countryNames[country] || country;
        countrySection.appendChild(countryHeading);
        Object.keys(categoryNames).forEach((category) => {
          const assets = brandAssets.filter((asset) => (
            (asset.country || "global") === country && asset.category === category
          ));
          if (!assets.length) return;
          const categorySection = document.createElement("section");
          categorySection.className = "marketing-category";
          const categoryHeading = document.createElement("h4");
          categoryHeading.textContent = categoryNames[category];
          const grid = document.createElement("div");
          grid.className = "marketing-grid";
          grid.append(...assets.map(assetCard));
          categorySection.append(categoryHeading, grid);
          countrySection.appendChild(categorySection);
        });
        section.appendChild(countrySection);
      });
      groups.appendChild(section);
    });
    document.querySelector("#visible-assets").textContent = visible.length;
    notice.hidden = visible.length > 0;
    if (!visible.length) notice.textContent = "No hay materiales que coincidan con estos filtros.";
  };
  const fillFilters = () => {
    const countries = [...new Set(state.assets.map((asset) => asset.country || "global"))].sort();
    const categories = [...new Set(state.assets.map((asset) => asset.category))].sort();
    const countrySelect = document.querySelector("#asset-country");
    countries.forEach((country) => {
      const option = document.createElement("option");
      option.value = country;
      option.textContent = countryNames[country] || country;
      countrySelect.appendChild(option);
    });
    const categorySelect = document.querySelector("#asset-category");
    categories.forEach((category) => {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = categoryNames[category] || category;
      categorySelect.appendChild(option);
    });
  };
  ["brand", "country", "category"].forEach((field) => {
    document.querySelector(`#asset-${field}`).addEventListener("change", (event) => {
      state[field] = event.target.value;
      render();
    });
  });
  document.querySelector("#clear-assets").addEventListener("click", () => {
    state.brand = "";
    state.country = "";
    state.category = "";
    ["brand", "country", "category"].forEach((field) => {
      document.querySelector(`#asset-${field}`).value = "";
    });
    render();
  });
  document.querySelector("#menu-toggle")?.addEventListener("click", () => {
    document.querySelector("#sidebar")?.classList.toggle("sidebar--open");
  });
  fetch("/api/v1/marketing-assets/")
    .then((response) => {
      if (!response.ok) throw new Error("assets unavailable");
      return response.json();
    })
    .then((payload) => {
      state.assets = Array.isArray(payload) ? payload : payload.results || [];
      document.querySelector("#asset-total").textContent = `${state.assets.length} archivos activos`;
      fillFilters();
      render();
    })
    .catch(() => {
      notice.textContent = "No pudimos cargar los materiales. Intenta de nuevo más tarde.";
      document.querySelector("#asset-total").textContent = "No disponible";
    });
})();
