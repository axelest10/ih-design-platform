(() => {
  const renderableFormats = new Set(["png", "svg", "jpg", "jpeg", "webp"]);
  const countryNames = { CL: "Chile", CO: "Colombia", MX: "México", PE: "Perú" };
  const variantNames = {
    black: "Negro",
    classic: "Color",
    "monochrome-blue": "Monocromo azul",
    "monochrome-white": "Blanco",
    white: "Blanco",
  };
  const state = { logos: [], country: "", brand: "", isAdmin: false };
  const grid = document.querySelector("#logo-grid");
  const notice = document.querySelector("#catalog-notice");
  const countryFilter = document.querySelector("#catalog-country");
  const brandFilter = document.querySelector("#catalog-brand");

  const assetUrl = (file) => `/brand/assets/logos/${file.split("/").map(encodeURIComponent).join("/")}`;
  const brandName = (logo) => logo.brand || "International House";

  const previewFor = (logo) => {
    if (renderableFormats.has(String(logo.format).toLowerCase())) return logo;
    return state.logos.find((candidate) => (
      renderableFormats.has(String(candidate.format).toLowerCase())
      && brandName(candidate) === brandName(logo)
      && candidate.variant === logo.variant
    )) || state.logos.find((candidate) => (
      renderableFormats.has(String(candidate.format).toLowerCase())
      && brandName(candidate) === brandName(logo)
    ));
  };

  const tag = (text, neutral = false) => {
    const element = document.createElement("span");
    element.className = `logo-card__tag${neutral ? " logo-card__tag--neutral" : ""}`;
    element.textContent = text;
    return element;
  };

  const logoCard = (logo) => {
    const card = document.createElement("article");
    card.className = "logo-card";
    const media = document.createElement("div");
    media.className = `logo-card__media${String(logo.variant).includes("white") ? " logo-card__media--dark" : ""}`;
    const preview = previewFor(logo);
    if (preview) {
      const image = document.createElement("img");
      image.src = assetUrl(preview.file);
      image.alt = `Logo ${brandName(logo)}, variante ${variantNames[logo.variant] || logo.variant}`;
      image.loading = "lazy";
      image.addEventListener("error", () => {
        image.remove();
        const fallback = document.createElement("span");
        fallback.className = "logo-card__fallback";
        fallback.textContent = "Vista previa no disponible";
        media.appendChild(fallback);
      }, { once: true });
      media.appendChild(image);
    }

    const body = document.createElement("div");
    body.className = "logo-card__body";
    const meta = document.createElement("div");
    meta.className = "logo-card__meta";
    meta.append(tag(logo.country ? (countryNames[logo.country] || logo.country) : "Global"));
    meta.append(tag(variantNames[logo.variant] || logo.variant, true));
    const title = document.createElement("h2");
    title.textContent = state.isAdmin ? logo.name : brandName(logo);
    const brand = document.createElement("p");
    brand.textContent = state.isAdmin
      ? brandName(logo)
      : `${variantNames[logo.variant] || logo.variant} · ${logo.country ? (countryNames[logo.country] || logo.country) : "Global"}`;
    const footer = document.createElement("div");
    footer.className = "logo-card__footer";
    const format = document.createElement("span");
    format.textContent = String(logo.format).toUpperCase();
    const link = document.createElement("a");
    link.href = assetUrl(logo.file);
    link.textContent = "Abrir archivo ↗";
    link.target = "_blank";
    link.rel = "noopener";
    footer.append(format, link);
    if (preview && preview !== logo) {
      const note = document.createElement("span");
      note.className = "logo-card__preview-note";
      note.textContent = "Vista web equivalente";
      meta.append(note);
    }
    body.append(meta, title, brand, footer);
    card.append(media, body);
    return card;
  };

  const render = () => {
    const visible = state.logos.filter((logo) => (
      (!state.country || (logo.country || "global") === state.country)
      && (!state.brand || brandName(logo) === state.brand)
    ));
    grid.replaceChildren(...visible.map(logoCard));
    document.querySelector("#visible-count").textContent = visible.length;
    notice.hidden = visible.length > 0;
    if (!visible.length) notice.textContent = "No hay logos que coincidan con estos filtros.";
  };

  const fillFilters = () => {
    const countries = [...new Set(state.logos.map((logo) => logo.country || "global"))].sort();
    const brands = [...new Set(state.logos.map(brandName))].sort((a, b) => a.localeCompare(b, "es"));
    countries.forEach((country) => {
      const option = document.createElement("option");
      option.value = country;
      option.textContent = country === "global" ? "Global / sin país" : (countryNames[country] || country);
      countryFilter.appendChild(option);
    });
    brands.forEach((brand) => {
      const option = document.createElement("option");
      option.value = brand;
      option.textContent = brand;
      brandFilter.appendChild(option);
    });
  };

  document.querySelector("#menu-toggle")?.addEventListener("click", () => {
    document.querySelector("#sidebar")?.classList.toggle("sidebar--open");
  });
  countryFilter.addEventListener("change", () => { state.country = countryFilter.value; render(); });
  brandFilter.addEventListener("change", () => { state.brand = brandFilter.value; render(); });
  document.querySelector("#clear-filters").addEventListener("click", () => {
    countryFilter.value = "";
    brandFilter.value = "";
    state.country = "";
    state.brand = "";
    render();
  });

  Promise.all([
    fetch("/api/v1/branding/logos/").then((response) => {
      if (!response.ok) throw new Error("catalog unavailable");
      return response.json();
    }),
    fetch("/api/v1/me/")
      .then((response) => (response.ok ? response.json() : null))
      .catch(() => null),
  ])
    .then(([payload, user]) => {
      state.logos = payload.logos;
      state.isAdmin = Boolean(user?.is_admin);
      document.querySelector("#catalog-version").textContent = `${payload.count} logos · v${payload.version}`;
      fillFilters();
      render();
    })
    .catch(() => {
      notice.textContent = "No pudimos cargar el catálogo. Intenta de nuevo más tarde.";
      document.querySelector("#visible-count").textContent = "—";
      document.querySelector("#catalog-version").textContent = "No disponible";
    });
})();
