from django.db import migrations


VENUE_KIT_PRODUCTS = [
    "general-english",
    "cambridge-exam-preparation",
    "university-programmes",
    "business-english",
    "ielts-preparation",
    "spanish-courses",
]

MEXICO_SOURCE = "https://ihmexico.mx/escuelas-de-ingles-en-mexico/"
COLOMBIA_SOURCE = "https://ihcolombia.com/sedes/"
PERU_SOURCE = "https://ihlima.com/sedes/"
CHILE_SOURCE = "https://ihsantiago.cl/sedes/"


BRANCHES = (
    # Mexico: official JSON-LD entries from the English-school directory.
    ("mx-condesa", "International House México – Condesa", "Ciudad de México", "MX", MEXICO_SOURCE, "Alfonso Reyes 224, Hipódromo Condesa", "06100", "CDMX", "+52 55 5211 6500", None),
    ("mx-satelite", "International House México – Satélite", "Ciudad Satélite, Naucalpan", "MX", MEXICO_SOURCE, "Circuito Médicos 47", "53100", "Estado de México", "+52 5370 3227", "ielts.satelite@ihmexico.com"),
    ("mx-aguascalientes", "International House Aguascalientes", "Aguascalientes", "MX", MEXICO_SOURCE, "Avenida Adolfo López Mateos Ote. 1001", "20250", "Aguascalientes", "+52 449 996 2425, +52 449 996 2426", "aguascalientes@ihmexico.com"),
    ("mx-cancun", "International House Cancún", "Cancún", "MX", MEXICO_SOURCE, "Calle Robalo 50 – 1", "77500", "Quintana Roo", "+52 9983647322", "empresascun@ihmexico.com"),
    ("mx-cuernavaca", "International House Cuernavaca", "Colonia Lomás del Mirador, Cuernavaca", "MX", MEXICO_SOURCE, "Calle Guillermina 50", "62350", "Morelos", "+52 7771352499", "cuernavaca@ihmexico.com"),
    ("mx-guadalajara", "International House Guadalajara", "Col. Providencia, Guadalajara", "MX", MEXICO_SOURCE, "Av. Pablo Neruda 2886 int 201", "44639", "Jalisco", "+52 3337437722", "guadalajara@ihmexico.com"),
    ("mx-puebla", "International House Puebla", "Plaza Inn, Puebla", "MX", MEXICO_SOURCE, "Circuito Juan Pablo II # 2716, locales 18, 19 y 20. Col. Benito Juárez", "72400", "Puebla", "+52 222279 6817", "tania.hernandez@ihmexico.com"),
    ("mx-queretaro", "International House Querétaro", "Col. San Ángel, Querétaro", "MX", MEXICO_SOURCE, "Edificio Tec 100 – Nippo Av. Tecnológico # 100, segundo piso, despachos 201-214", "76030", "Querétaro", "+52 4772656375", "ielts.queretaro@ihmexico.com"),
    ("mx-toluca", "International House Toluca", "Zinacantepec", "MX", MEXICO_SOURCE, "Av. Adolfo López Mateos 206, planta alta, Col. Las Culturas", "51355", "Estado de México", "+52 7229147719", "rogelio.garcia@ihmexico.com"),
    ("mx-veracruz", "International House Veracruz", "Boca del Río", "MX", MEXICO_SOURCE, "Calle Sierra 1639 Altos, Fracc. Costa de Oro", "94299", "Veracruz", "+52 2292139100", "ieltsveracruz@ihmexico.com"),
    ("mx-playa-del-carmen", "International House Playa del Carmen", "Playa del Carmen", "MX", MEXICO_SOURCE, "Calle Catorce Norte 171, entre Av. 5 y 10", "77710", "Quintana Roo", "+52 9848033388", "soporte.cancun@ihmexico.com"),
    ("mx-monterrey", "International House Monterrey (Representación)", "San Pedro Garza García", "MX", MEXICO_SOURCE, "Avenida Lázaro Cárdenas No. 2470, oficina 8, Colonia Villas de San Agustín", "66266", "Nuevo León", "+52 8134400461", "gilberto.zapata@ihmexico.com"),
    ("mx-oaxaca", "International House Oaxaca", "Oaxaca de Juárez", "MX", MEXICO_SOURCE, "C. de Mariano Abasolo 217, Ruta Independencia, Centro", "68000", "Oaxaca", "+52 9512051561", "oaxaca@ihmexico.com"),
    ("mx-torreon", "International House Torreón", "Torreón", "MX", MEXICO_SOURCE, "Blvd. Independencia 2600 local 14, Col. Estrella", "27010", "Coahuila", "+52 8711938427", "andrea.galindo@ihtravel.mx"),
    ("mx-chihuahua", "International House Chihuahua Examination Centre", "Chihuahua", "MX", MEXICO_SOURCE, "Colegio ESPABI Fuente Trevi 7201, Las Fuentes", "31207", "Chihuahua", "+52 6143423023", "ielts.chihuahua@ihmexico.com"),
    ("mx-culiacan", "International House Culiacán Examination Centre", "Culiacán", "MX", MEXICO_SOURCE, "Teresa Villegas #1231, Col. Gabriel Leyva", "80030", "Sinaloa", "+52 6672759343", "sinaloa@ihmexico.com"),
    ("mx-hermosillo", "International House Hermosillo Examination Centre", "Hermosillo", "MX", MEXICO_SOURCE, "Garmendia 56, entre Veracruz y Tamaulipas, Col. San Benito", "83190", "Sonora", "+52 6623117230", "ramon.aguilar@Ihmexico.com"),
    ("mx-leon", "International House León Examination Centre", "León", "MX", MEXICO_SOURCE, "Blvd. Juan Alonso de Torres # 2302-B, Colonia Lomas de Campestre", "31750", "Guanajuato", "+52 4791475097", "ielts.leon@ihmexico.com"),
    ("mx-merida", "International House Mérida Examination Centre", "Mérida", "MX", MEXICO_SOURCE, "Calle 37 #272 x 28 y 30, Colonia Jardines de Pensiones", "97100", "Yucatán", "+52 9881884283", "empresascun@ihmexico.com"),
    ("mx-morelia", "International House Morelia Examination Centre", "Morelia", "MX", MEXICO_SOURCE, "Fuentes de Morelia 803, Fracc. Loma de la Floresta", "58085", "Michoacán", "+52 4432377777", "morelia@ihmexico.com"),
    ("mx-tampico", "International House Tampico Examination Centre", "Cd. Madero", "MX", MEXICO_SOURCE, "Raúl Castillo 118, Colonia Delfino Reséndiz", "89556", "Tamaulipas", "+52 8331608339", "soporte.ielts@ihmexico.com"),
    ("mx-tepic", "International House Tepic Examination Centre", "Tepic", "MX", MEXICO_SOURCE, "Av. Estadios 35, Centro INNE", "63000", "Nayarit", "+52 3111707000", "nayarit@ihmexico.com"),
    ("mx-tijuana", "International House Tijuana Examination Centre", "Zona Urbana Río Tijuana", "MX", MEXICO_SOURCE, "Condominio Paseo 1, 5to piso, oficina 506. Paseo de los Héroes", "22010", "Baja California Norte", "+52 6633243990", "administracionbc@lec.mx, aaron.alcala@ihmexico.com"),
    ("mx-villahermosa", "International House Villahermosa Examination Centre", "Villahermosa", "MX", MEXICO_SOURCE, "Calle Vía 3, entre Av. Vía 2 y Vía Espuela, Plaza Campestre - Local 27, Tabasco 2000", "86035", "Tabasco", "+52 9936327747", "alpha.ponce@ihmexico.com"),
    # Colombia: the official page states seven locations.
    ("co-bogota-carrera-18a", "IH Bogotá - Carrera 18 A", "Bogotá", "CO", COLOMBIA_SOURCE, "Carrera 18 A No. 137–80, piso 2", "110121", "Bogotá D.C.", "+57 310 2147254 / +57 320 8381995", "tea@ihbogota.com"),
    ("co-bogota-santa-barbara", "IH Bogotá - Santa Bárbara", "Bogotá", "CO", COLOMBIA_SOURCE, "Calle 113 #11 A–44, barrio Santa Bárbara", "", "Bogotá D.C.", "+57 310 2147254 / +57 320 8381995", "tea@ihbogota.com"),
    ("co-cali-ciudad-jardin", "IH Cali - Ciudad Jardín", "Cali", "CO", COLOMBIA_SOURCE, "Calle 14 #100–94, barrio Ciudad Jardín", "", "Valle del Cauca", "+57 310 2147254 / +57 320 8381995", "teacali@ihbogota.com"),
    ("co-cali-valle", "IH Cali - Valle del Cauca", "Cali", "CO", COLOMBIA_SOURCE, "Carrera 27 Oeste #4-04, Miraflores", "", "Valle del Cauca", "+57 310 2147254 / +57 320 8381995", "teacali@ihbogota.com"),
    ("co-neiva", "IH Neiva - Huila", "Neiva", "CO", COLOMBIA_SOURCE, "Calle 14 #5–108", "", "Huila", "+57 310 2147254 / +57 320 8381995", "tea@ihbogota.com"),
    ("co-medellin-torre-oviedo", "IH Medellín - Torre Oviedo", "Medellín", "CO", COLOMBIA_SOURCE, "Carrera 43A N° 8 Sur–15, Edificio Torre Oviedo, El Poblado, oficina 510", "", "Antioquia", "+57 321 7554712 / +57 320 8381995", "tea@ihbogota.com / ihmedellin.com"),
    ("co-barranquilla", "IH Barranquilla", "Barranquilla", "CO", COLOMBIA_SOURCE, "Cra. 54 ## 68-189, Norte Centro Histórico", "", "Atlántico", "+57 310 2147254 / +57 320 8381995", "tea@ihbogota.com / teabarranquilla@ihbogota.com"),
    # Peru: Miraflores and Arequipa are on the locations page; San Borja is in the official footer.
    ("pe-miraflores", "IH Lima - Miraflores CD", "Miraflores, Lima", "PE", PERU_SOURCE, "Avenida José Pardo 601, oficina 1302 y 1303", "", "Lima", "+51 1 6803001 / +51 938 743 786", "info@ihlima.com"),
    ("pe-san-borja", "IH Lima - San Borja", "San Borja, Lima", "PE", PERU_SOURCE, "Avenida San Luis 2020, oficina 101", "", "Lima", "+51 1 6803001", "info@ihlima.com"),
    ("pe-arequipa", "IH Lima - Arequipa", "Yanahuara, Arequipa", "PE", PERU_SOURCE, "Calle Cesar Vallejo 102, Yanahuara", "04001", "Arequipa", "+51 924 426 932", "info@ihlima.com"),
    # Chile: current official page exposes Santiago/IELTS Chile.
    ("cl-santiago", "IELTS Chile - Santiago", "Providencia, Santiago", "CL", CHILE_SOURCE, "Miguel Claro 67", "", "Santiago", "+56 9 9205 5055 / +56 9 8805 8143", "info@chileielts.cl / certificaciones@chileielts.cl"),
)


def seed_venue_kit(apps, schema_editor):
    material_type_model = apps.get_model("materials", "MaterialType")
    branch_model = apps.get_model("catalog", "Branch")
    material_type_model.objects.update_or_create(
        slug="venue-kit",
        defaults={
            "name": "Paquetería de marketing para sedes",
            "renderer_family": "html-svg",
            "channel": "local-venue",
            "schema_version": "1.0.0",
            "supported_formats": ["square", "story", "portrait", "a4", "16:9"],
            "priority_product_slugs": VENUE_KIT_PRODUCTS,
            "product_scope": "all_catalog",
            "active": True,
        },
    )
    for code, name, city, country, source_url, address, postal, region, phone, email in BRANCHES:
        needs_confirmation = ["hours", "map_url", "cta", "approved_local_assets"]
        if not email:
            needs_confirmation.append("email")
        branch_model.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "country": country,
                "city": city,
                "source_url": source_url,
                "official_contact_data": {
                    "location": {
                        "address": address,
                        "postal_code": postal,
                        "region": region,
                    },
                    "contact": {"phone": phone, "email": email},
                    "source_status": "confirmed",
                    "needs_confirmation": needs_confirmation,
                },
                "is_active": True,
            },
        )


def remove_venue_kit(apps, schema_editor):
    apps.get_model("materials", "MaterialType").objects.filter(slug="venue-kit").delete()
    apps.get_model("catalog", "Branch").objects.filter(
        code__in=[branch[0] for branch in BRANCHES]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_branch_provenance"),
        ("materials", "0010_alter_marketingasset_file"),
    ]

    operations = [migrations.RunPython(seed_venue_kit, remove_venue_kit)]
