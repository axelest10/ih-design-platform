/* Generado automáticamente por brand/scripts/generate_tokens.py.
No editar a mano — editar los YAML fuente en brand/tokens/ y brand/product-colors/. */

export const ihBrandTokens = {
  "colors": {
    "knowledge": "#3B44B5",
    "technology": "#923472",
    "youth": "#B7DB6E",
    "joy": "#F4CF80",
    "light": "#F4AB63",
    "salmon": "#F06C6A",
    "pink": "#E070A2",
    "green": "#28AE62",
    "ielts_red": "#E31736",
    "neutral_white": "#FFFFFF",
    "neutral_black": "#000000",
    "neutral_dark_navy": "#1A2566",
    "neutral_gray_100": "#F5F5F5",
    "neutral_gray_300": "#D0D0D0",
    "neutral_surface_1": "#F8F8F8",
    "neutral_surface_2": "#FAFAFA",
    "neutral_surface_tint_blue": "#F0F4FF"
  },
  "productColors": {
    "ingles_general": {
      "display_name": "Inglés General",
      "commercial_alias": "Hello!",
      "alias_note": "Decisión actualizada por el cliente (Axel Estrada, 2026-08-09): \"Hello!\", el nombre comercial de cara al público de IH para el pilar \"Inglés General\", sigue usando el color institucional Youth Green (#B7DB6E) en materiales institucionales de IH. La decisión del 2026-08-05 se revierte únicamente para el sub-brand independiente \"Hello Live English\", que tiene dominio, producto y Brandfolder propios y cuya identidad visual separada fue adoptada formalmente. Ver `brand/product-colors/sub-brand-identities.yaml`; esa identidad no reemplaza la paleta institucional documentada en este pilar.\n",
      "primary_hex": "#B7DB6E",
      "primary_token": "youth",
      "secondary_hex": "#28AE62",
      "secondary_token": "green",
      "background_hex": "#F0FAF0",
      "cta": {
        "background_hex": "#28AE62",
        "text_hex": "#FFFFFF"
      },
      "sensation": "Fresca, accesible, dinámica",
      "justification": "Verde joven transmite accesibilidad y oportunidad de crecimiento."
    },
    "cambridge": {
      "display_name": "Cambridge",
      "primary_hex": "#923472",
      "primary_token": "technology",
      "secondary_hex": "#3B44B5",
      "secondary_token": "knowledge",
      "background_hex": "#F5EBF2",
      "cta": {
        "background_hex": "#923472",
        "text_hex": "#FFFFFF"
      },
      "sensation": "Académico, serio, distinguido",
      "justification": "El magenta denota prestigio y certificación de alto nivel."
    },
    "university_programmes": {
      "display_name": "University Programmes",
      "commercial_alias": "UP",
      "alias_note": "Confirmado por el cliente (Axel Estrada, 2026-08-05): \"UP\" (de `Color por producto.pdf`) es el nombre corto/comercial de este mismo pilar \"University Programmes\", mismo color institucional (Knowledge Blue #3B44B5).\n",
      "primary_hex": "#3B44B5",
      "primary_token": "knowledge",
      "secondary_hex": "#F4CF80",
      "secondary_token": "joy",
      "background_hex": "#EEF0FF",
      "cta": {
        "background_hex": "#3B44B5",
        "text_hex": "#FFFFFF"
      },
      "sensation": "Confianza, global, aspiracional",
      "justification": "Azul IH principal. Transmite credibilidad y apertura internacional."
    },
    "empresas": {
      "display_name": "Inglés para Empresas",
      "primary_hex": "#28AE62",
      "primary_token": "green",
      "secondary_hex": "#B7DB6E",
      "secondary_token": "youth",
      "background_hex": "#EBF7F0",
      "cta": {
        "background_hex": "#28AE62",
        "text_hex": "#FFFFFF",
        "note": "El documento fuente tiene una errata de tipeo ('#2BAE62'); se normaliza al token oficial green (#28AE62)."
      },
      "sensation": "Profesional, crecimiento, resultados",
      "justification": "Verde asocia crecimiento empresarial y resultados medibles."
    },
    "ielts": {
      "display_name": "IELTS",
      "primary_hex": "#E31736",
      "primary_token": "ielts_red",
      "primary_token_source": "extended_colors",
      "secondary_hex": "#E070A2",
      "secondary_token": "pink",
      "background_hex": "#FFF0F0",
      "cta": {
        "background_hex": "#E31736",
        "text_hex": "#FFFFFF"
      },
      "sensation": "Urgente, enfocado, competitivo",
      "justification": "Rojo IELTS oficial. Comunica urgencia y alto rendimiento."
    },
    "spanish_courses": {
      "display_name": "Spanish Courses",
      "primary_hex": "#F4AB63",
      "primary_token": "light",
      "secondary_hex": "#923472",
      "secondary_token": "technology",
      "background_hex": "#FFF8F0",
      "cta": {
        "background_hex": "#923472",
        "text_hex": "#FFFFFF"
      },
      "sensation": "Cálido, cultural, auténtico",
      "justification": "Ámbar evoca México, calidez cultural y experiencia auténtica."
    }
  },
  "typography": {
    "version": "1.0.0",
    "status": "approved_with_open_questions",
    "typefaces": {
      "heading": {
        "name": "Aptos",
        "role": "headings",
        "source": "International House Brand Guidelines (1).pdf — 'Golden rule: Always use Aptos as the primary typeface.'",
        "weights_documented": [
          "Regular",
          "Semibold",
          "Bold"
        ],
        "fallback_stack": "Aptos, Arial, sans-serif",
        "fallback_source": "IH_Mexico_Sistema_Diseno_Web.docx / IH_Sistema_Colores_v2.docx — variable CSS --font-heading",
        "license_status": "RESTRICTED_STANDARD_LICENSE",
        "license_note": "Investigado el 2026-08-05: Microsoft publica una descarga oficial de Aptos (microsoft.com/en-us/download/details.aspx?id=106087), pero la licencia estándar que acompaña esa descarga permite usar la fuente para crear/mostrar/imprimir contenido, mas NO autoriza la redistribución de los archivos .ttf dentro de un repositorio de código o dependencia interna reutilizable — Microsoft ofrece licenciamiento aparte para redistribución de software/hardware o instalación en servidores. Por eso los .ttf de Aptos NO se incluyen en brand/assets/fonts/aptos/. Si IH México ya cuenta con un acuerdo empresarial con Microsoft que cubra la redistribución, debe confirmarse explícitamente antes de cambiar este estado. Ver brand/assets/fonts/README.md.\n"
      },
      "body": {
        "name": "Open Sans",
        "role": "body",
        "source": "International House Brand Guidelines (1).pdf — 'Golden rule: Always use Open Sans as a secondary typeface.'",
        "weights_documented": [
          "Light",
          "Regular",
          "Semibold",
          "Bold"
        ],
        "fallback_stack": "'Open Sans', sans-serif",
        "license_status": "OFL",
        "license_note": "SIL Open Font License 1.1 — incluida en brand/assets/fonts/open-sans/OFL.txt. Uso y redistribución libres bajo los términos de la licencia."
      }
    },
    "sub_brand_typefaces": {
      "hello_live_english": {
        "name": "Poppins",
        "role": "Logotipo y títulos en Bold; textos de soporte en Regular",
        "source": "Brandfolder-Hello Live English.pdf — página 'Tipografía'",
        "weights_documented": [
          "Bold",
          "Regular"
        ],
        "fallback_stack": "Poppins, Arial, sans-serif",
        "license_status": "OFL",
        "license_note": "SIL Open Font License 1.1 — incluida en brand/assets/fonts/poppins/OFL.txt, copyright \"The Poppins Project Authors\". Aplica solo al sub-brand Hello Live English y su variante Live English Kids; no reemplaza Aptos/Open Sans en materiales institucionales de IH.\n"
      }
    },
    "leading": {
      "heading": {
        "ratio": 1.1,
        "percent": "110%"
      },
      "subheading": {
        "ratio": 1.2,
        "percent": "120%"
      },
      "body": {
        "ratio": 1.4,
        "percent": "140%"
      }
    },
    "tracking": {
      "heading": {
        "figma_percent": "-2%",
        "adobe_pt": -20
      },
      "subheading": {
        "figma_percent": "-1%",
        "adobe_pt": -10
      },
      "body": {
        "figma_percent": "0%",
        "adobe_pt": 0
      }
    },
    "weight_rules": [
      "Para títulos y encabezados usar el peso semibold de Aptos (no bold por defecto) para llamar la atención sin sensación de pesadez.",
      "Para cuerpo de texto usar Open Sans Light o Regular.",
      "Para enfatizar una palabra/frase dentro de un párrafo, subir un solo nivel de peso (p. ej. de Regular a Semibold, saltando 'medium').",
      "Usar como máximo 3 tamaños de fuente por pieza de comunicación."
    ],
    "type_scale": {
      "status": "mx_extension",
      "styles": {
        "h1_display": {
          "typeface": "heading",
          "weight": "Bold",
          "size_px": 56,
          "line_height_px": 64,
          "letter_spacing": "-1%",
          "usage": "Títulos hero principales. Solo uno por página.",
          "mobile_max_px": 32
        },
        "h2_section": {
          "typeface": "heading",
          "weight": "Semibold",
          "size_px": 40,
          "line_height_px": 48,
          "usage": "Títulos de sección principales.",
          "mobile_max_px": 24
        },
        "h3_subsection": {
          "typeface": "heading",
          "weight": "Semibold",
          "size_px": 28,
          "line_height_px": 36,
          "usage": "Subtítulos de bloque y títulos grandes de card."
        },
        "h4_card_title": {
          "typeface": "heading",
          "weight": "Semibold",
          "size_px": 22,
          "line_height_px": 28,
          "usage": "Títulos dentro de cards y modales."
        },
        "body_large": {
          "typeface": "body",
          "weight": "Regular",
          "size_px": 18,
          "line_height_px": 28,
          "usage": "Párrafos principales debajo del hero."
        },
        "body_base": {
          "typeface": "body",
          "weight": "Regular",
          "size_px": 16,
          "line_height_px": 24,
          "usage": "Texto de cuerpo estándar."
        },
        "body_small": {
          "typeface": "body",
          "weight": "Regular",
          "size_px": 14,
          "line_height_px": 20,
          "usage": "Texto secundario, labels, notas al pie."
        },
        "caption": {
          "typeface": "body",
          "weight": "Regular",
          "size_px": 12,
          "line_height_px": 18,
          "usage": "Captions, metadatos, textos legales."
        },
        "cta_button": {
          "typeface": "heading",
          "weight": "Semibold",
          "size_px": 16,
          "usage": "Botones. Mayúsculas opcional."
        },
        "badge_tag": {
          "typeface": "body",
          "weight": "Bold",
          "size_px": 12,
          "letter_spacing": "1%",
          "usage": "Tags de categoría, badges, pills."
        }
      }
    },
    "incorrect_use": [
      "No mezclar alineaciones de texto en párrafos cercanos.",
      "No distorsionar las tipografías en texto de cuerpo.",
      "No mezclar tipografías distintas dentro del mismo bloque de texto.",
      "No justificar el texto."
    ]
  },
  "spacing": {
    "version": "1.0.0",
    "status": "mx_extension",
    "base_unit_px": 8,
    "scale": {
      "xs": 8,
      "sm": 16,
      "md": 24,
      "lg": 32,
      "xl": 48,
      "2xl": 64,
      "3xl": 80,
      "4xl": 120
    },
    "grid": {
      "desktop": {
        "columns": 12,
        "gutter_px": 72,
        "margin_px": 80,
        "breakpoint_px": 1440
      },
      "tablet": {
        "columns": 8,
        "gutter_px": 24,
        "margin_px": 40,
        "breakpoint_px": 768
      },
      "mobile": {
        "columns": 4,
        "gutter_px": 16,
        "margin_px": 20,
        "breakpoint_px": 375
      },
      "auto_layout_rule": "Hug en ambas dimensiones para componentes. Fill para contenedores de sección."
    },
    "responsive_breakpoints": {
      "desktop_min_px": 1200,
      "tablet_range_px": [
        768,
        1199
      ],
      "mobile_max_px": 767
    },
    "rules": [
      "Nunca ocultar CTAs en mobile — son el elemento más importante.",
      "Las imágenes hero en mobile deben ser verticales o cuadradas, no el mismo recorte que desktop.",
      "Los formularios en mobile deben ocupar el 100% del ancho, sin columnas internas.",
      "Todos los botones CTA en mobile deben tener mínimo 44px de altura (touch target estándar)."
    ]
  },
  "radius": {
    "button_px": 8,
    "card_px": 12,
    "input_px": 8,
    "pill_px": 100
  },
  "shadows": {
    "level_1": "0 2px 8px rgba(0,0,0,0.08)",
    "level_2": "0 8px 24px rgba(0,0,0,0.12)",
    "level_3": "0 16px 48px rgba(0,0,0,0.16)",
    "card": "0 8px 24px rgba(0,0,0,0.10)"
  },
  "motion": {
    "version": "0.1.0-draft",
    "status": "NOT_OFFICIAL_PENDING_BRAND_APPROVAL",
    "durations_ms": {
      "fast": 120,
      "base": 200,
      "slow": 320
    },
    "easing": {
      "standard": "cubic-bezier(0.4, 0, 0.2, 1)",
      "entrance": "cubic-bezier(0, 0, 0.2, 1)",
      "exit": "cubic-bezier(0.4, 0, 1, 1)"
    },
    "note": "No usar estos valores como si fueran reglas de marca en materiales de cliente/institucionales hasta que el equipo de marketing/diseño de IH México los apruebe explícitamente.\n"
  },
  "rainbow": {
    "status": "approved",
    "rule": "Inicia siempre en salmon, termina siempre en joy (yellow). No reordenar, no gradientes, no rotar ni mezclar variantes distintas en la misma pieza.",
    "colors_hex": [
      "#F06C6A",
      "#3B44B5",
      "#28AE62",
      "#923472",
      "#B7DB6E",
      "#F4AB63",
      "#F4CF80",
      "#E070A2"
    ],
    "note": "El orden visual exacto de las franjas dentro de cada variante gráfica (Line, Rhythm, Flat Wavy Up/Down, Double Line) está definido por los archivos SVG oficiales en brand/assets/rainbows/ — no se debe regenerar ni reordenar el rainbow manualmente.\n",
    "rejected_variant": {
      "source": "IH_Mexico_Sistema_Diseno_Web.docx, Tabla 9",
      "reason": "Sustituía Light Orange (#F4AB63) por un color 'Teal' #407B98 inexistente en la paleta oficial del manual global. Rechazada por el cliente el 2026-08-05."
    }
  }
};

export default ihBrandTokens;
