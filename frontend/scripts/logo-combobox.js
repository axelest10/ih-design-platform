(() => {
  const normalize = (value) => String(value || "").trim().toLocaleLowerCase("es");

  const uniqueLogos = (logos) => {
    const byName = new Map();
    logos.forEach((logo) => {
      if (logo?.name && !byName.has(logo.name)) byName.set(logo.name, logo);
    });
    return [...byName.values()];
  };

  const create = ({
    host,
    selectionElement = null,
    placeholder = "Buscar por marca o variante",
    emptyMessage = "No hay logos adicionales disponibles.",
  }) => {
    const root = typeof host === "string" ? document.querySelector(host) : host;
    const nativeSelect = typeof selectionElement === "string"
      ? document.querySelector(selectionElement)
      : selectionElement;
    if (!root) return null;

    let logos = [];
    let activeIndex = -1;
    const selected = new Set();

    root.replaceChildren();
    root.classList.add("logo-combobox");

    const chips = document.createElement("div");
    chips.className = "logo-combobox__chips";
    chips.setAttribute("aria-label", "Logos seleccionados");

    const control = document.createElement("div");
    control.className = "logo-combobox__control";
    const search = document.createElement("input");
    const listId = `${root.id || "logo"}-suggestions`;
    search.type = "search";
    search.className = "logo-combobox__search";
    search.placeholder = placeholder;
    search.autocomplete = "off";
    search.setAttribute("role", "combobox");
    search.setAttribute("aria-label", "Buscar logos adicionales");
    search.setAttribute("aria-autocomplete", "list");
    search.setAttribute("aria-controls", listId);
    search.setAttribute("aria-expanded", "false");

    const list = document.createElement("div");
    list.id = listId;
    list.className = "logo-combobox__list";
    list.setAttribute("role", "listbox");
    list.hidden = true;

    const status = document.createElement("span");
    status.className = "logo-combobox__status";
    status.setAttribute("aria-live", "polite");

    const hiddenInputs = document.createElement("div");
    hiddenInputs.className = "logo-combobox__selection-inputs";
    hiddenInputs.hidden = true;

    control.append(search, list);
    root.append(chips, control, status, hiddenInputs);

    const availableMatches = () => {
      const query = normalize(search.value);
      return logos.filter((logo) => {
        if (selected.has(logo.name)) return false;
        if (!query) return true;
        return normalize(logo.brand).includes(query) || normalize(logo.name).includes(query);
      });
    };

    const syncSelectionElement = () => {
      if (nativeSelect) {
        [...nativeSelect.options].forEach((option) => {
          option.selected = selected.has(option.value);
        });
        return;
      }
      hiddenInputs.replaceChildren();
      selected.forEach((name) => {
        const input = document.createElement("input");
        input.type = "checkbox";
        input.value = name;
        input.checked = true;
        input.defaultChecked = true;
        hiddenInputs.appendChild(input);
      });
    };

    const renderChips = () => {
      chips.replaceChildren();
      selected.forEach((name) => {
        const logo = logos.find((item) => item.name === name);
        if (!logo) return;
        const chip = document.createElement("span");
        chip.className = "logo-combobox__chip";
        const text = document.createElement("span");
        text.textContent = logo.brand || logo.name;
        const variant = document.createElement("small");
        variant.textContent = logo.name;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "logo-combobox__remove";
        remove.textContent = "×";
        remove.setAttribute("aria-label", `Quitar ${logo.brand || logo.name}: ${logo.name}`);
        remove.addEventListener("click", () => {
          selected.delete(name);
          syncSelectionElement();
          renderChips();
          renderSuggestions(true);
          search.focus();
        });
        chip.append(text, variant, remove);
        chips.appendChild(chip);
      });
    };

    const selectLogo = (logo) => {
      selected.add(logo.name);
      search.value = "";
      activeIndex = -1;
      syncSelectionElement();
      renderChips();
      renderSuggestions(true);
      search.focus();
    };

    const renderSuggestions = (open = false) => {
      const matches = availableMatches();
      list.replaceChildren();
      activeIndex = Math.min(activeIndex, matches.length - 1);
      matches.forEach((logo, index) => {
        const option = document.createElement("button");
        option.type = "button";
        option.className = "logo-combobox__option";
        option.setAttribute("role", "option");
        option.setAttribute("aria-selected", "false");
        if (index === activeIndex) option.classList.add("logo-combobox__option--active");
        const brand = document.createElement("strong");
        brand.textContent = logo.brand || logo.name;
        const name = document.createElement("small");
        name.textContent = logo.name;
        option.append(brand, name);
        option.addEventListener("mousedown", (event) => event.preventDefault());
        option.addEventListener("click", () => selectLogo(logo));
        list.appendChild(option);
      });
      const shouldOpen = open && logos.length > 0;
      list.hidden = !shouldOpen;
      search.setAttribute("aria-expanded", String(shouldOpen));
      status.textContent = matches.length
        ? `${matches.length} opciones disponibles.`
        : (logos.length ? "No hay coincidencias." : emptyMessage);
    };

    const moveActive = (offset) => {
      const matches = availableMatches();
      if (!matches.length) return;
      activeIndex = activeIndex === -1
        ? (offset > 0 ? 0 : matches.length - 1)
        : (activeIndex + offset + matches.length) % matches.length;
      renderSuggestions(true);
      list.children[activeIndex]?.scrollIntoView({ block: "nearest" });
    };

    search.addEventListener("focus", () => renderSuggestions(true));
    search.addEventListener("input", () => {
      activeIndex = -1;
      renderSuggestions(true);
    });
    search.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        moveActive(event.key === "ArrowDown" ? 1 : -1);
      } else if (event.key === "Enter") {
        const matches = availableMatches();
        if (!matches.length) return;
        event.preventDefault();
        selectLogo(matches[activeIndex >= 0 ? activeIndex : 0]);
      } else if (event.key === "Escape") {
        list.hidden = true;
        search.setAttribute("aria-expanded", "false");
      }
    });
    document.addEventListener("click", (event) => {
      if (!root.contains(event.target)) {
        list.hidden = true;
        search.setAttribute("aria-expanded", "false");
      }
    });

    const setSelected = (names = []) => {
      const availableNames = new Set(logos.map((logo) => logo.name));
      selected.clear();
      names.forEach((name) => {
        if (availableNames.has(name)) selected.add(name);
      });
      syncSelectionElement();
      renderChips();
      renderSuggestions(false);
    };

    const setOptions = (nextLogos = []) => {
      const previousSelection = nativeSelect
        ? [...nativeSelect.selectedOptions].map((option) => option.value)
        : [...selected];
      logos = uniqueLogos(nextLogos);
      if (nativeSelect) {
        nativeSelect.replaceChildren();
        logos.forEach((logo) => {
          const option = document.createElement("option");
          option.value = logo.name;
          option.textContent = `${logo.brand || logo.name} — ${logo.name}`;
          nativeSelect.appendChild(option);
        });
      }
      search.disabled = logos.length === 0;
      setSelected(previousSelection);
    };

    renderSuggestions(false);
    return { setOptions, setSelected, getSelected: () => [...selected] };
  };

  window.IHLogoCombobox = { create };
})();
