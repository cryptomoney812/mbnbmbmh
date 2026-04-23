"""
sources.py — конфигурация источников и категорий
"""

# ─── Категории ────────────────────────────────────────────────────────────────
CATEGORIES = {
    "🏠 Недвижимость":    "real_estate",
    "🚗 Авто":            "cars",
    "📱 Электроника":     "electronics",
    "👗 Одежда и мода":   "fashion",
    "💼 Бизнес/Услуги":   "business",
    "🛋 Мебель/Дом":      "furniture",
    "💎 Ювелирка":        "jewelry",
    "🌾 Продукты/Опт":    "wholesale",
    "🔧 Оборудование":    "equipment",
    "🐾 Животные":        "animals",
}

# ─── Страны по регионам ───────────────────────────────────────────────────────
COUNTRIES = {
    "🇷🇺 СНГ": [
        ("Россия", "ru"), ("Украина", "ua"), ("Казахстан", "kz"),
        ("Беларусь", "by"), ("Узбекистан", "uz"), ("Азербайджан", "az"),
        ("Грузия", "ge"), ("Армения", "am"), ("Кыргызстан", "kg"),
        ("Таджикистан", "tj"), ("Молдова", "md"),
    ],
    "🌍 Ближний Восток": [
        ("ОАЭ", "ae"), ("Саудовская Аравия", "sa"), ("Турция", "tr"),
        ("Египет", "eg"), ("Иордания", "jo"), ("Кувейт", "kw"),
        ("Катар", "qa"), ("Бахрейн", "bh"), ("Оман", "om"),
        ("Ирак", "iq"), ("Ливан", "lb"), ("Израиль", "il"),
    ],
    "🌍 Африка": [
        ("Нигерия", "ng"), ("Гана", "gh"), ("Кения", "ke"),
        ("Танзания", "tz"), ("Уганда", "ug"), ("Алжир", "dz"),
        ("Марокко", "ma"), ("Тунис", "tn"), ("ЮАР", "za"),
        ("Эфиопия", "et"), ("Камерун", "cm"), ("Сенегал", "sn"),
    ],
    "🌏 Азия": [
        ("Индия", "in"), ("Пакистан", "pk"), ("Бангладеш", "bd"),
        ("Индонезия", "id"), ("Малайзия", "my"), ("Филиппины", "ph"),
        ("Таиланд", "th"), ("Вьетнам", "vn"), ("Китай", "cn"),
        ("Япония", "jp"), ("Южная Корея", "kr"), ("Сингапур", "sg"),
    ],
    "🌎 Латинская Америка": [
        ("Бразилия", "br"), ("Мексика", "mx"), ("Аргентина", "ar"),
        ("Колумбия", "co"), ("Чили", "cl"), ("Перу", "pe"),
        ("Венесуэла", "ve"), ("Эквадор", "ec"), ("Боливия", "bo"),
    ],
    "🌍 Европа": [
        ("Германия", "de"), ("Франция", "fr"), ("Испания", "es"),
        ("Италия", "it"), ("Польша", "pl"), ("Румыния", "ro"),
        ("Нидерланды", "nl"), ("Бельгия", "be"), ("Португалия", "pt"),
        ("Чехия", "cz"), ("Венгрия", "hu"), ("Греция", "gr"),
    ],
    "🌎 Северная Америка": [
        ("США", "us"), ("Канада", "ca"), ("Мексика", "mx"),
    ],
}

# ─── Источники по странам ─────────────────────────────────────────────────────
SOURCES = {
    # СНГ
    "ru": [
        {"name": "Avito",    "url": "https://www.avito.ru/rossiya/{cat}?q={query}",          "type": "avito"},
        {"name": "Юла",      "url": "https://youla.ru/search?q={query}",                      "type": "generic"},
        {"name": "OLX.ru",   "url": "https://www.olx.ru/list/q-{query}/",                     "type": "olx"},
    ],
    "ua": [
        {"name": "OLX.ua",   "url": "https://www.olx.ua/uk/list/q-{query}/",                  "type": "olx"},
    ],
    "kz": [
        {"name": "OLX.kz",   "url": "https://www.olx.kz/list/q-{query}/",                     "type": "olx"},
        {"name": "Krisha.kz","url": "https://krisha.kz/search/?q={query}",                     "type": "generic"},
    ],
    "uz": [
        {"name": "OLX.uz",   "url": "https://www.olx.uz/list/q-{query}/",                     "type": "olx"},
    ],
    # Ближний Восток
    "ae": [
        {"name": "Dubizzle",  "url": "https://dubai.dubizzle.com/search/?q={query}",           "type": "dubizzle"},
        {"name": "OpenSooq",  "url": "https://ae.opensooq.com/en/search?q={query}",            "type": "opensooq"},
    ],
    "sa": [
        {"name": "OpenSooq",  "url": "https://sa.opensooq.com/en/search?q={query}",            "type": "opensooq"},
        {"name": "Haraj",     "url": "https://haraj.com.sa/search/{query}",                    "type": "generic"},
    ],
    "tr": [
        {"name": "Sahibinden","url": "https://www.sahibinden.com/arama?query={query}",         "type": "generic"},
        {"name": "Letgo.tr",  "url": "https://tr.letgo.com/search?q={query}",                  "type": "generic"},
    ],
    "eg": [
        {"name": "OLX.eg",    "url": "https://www.olx.com.eg/en/list/q-{query}/",             "type": "olx"},
        {"name": "OpenSooq",  "url": "https://eg.opensooq.com/en/search?q={query}",            "type": "opensooq"},
    ],
    # Африка
    "ng": [
        {"name": "Jiji.ng",   "url": "https://jiji.ng/search?query={query}",                   "type": "jiji"},
        {"name": "OLX.ng",    "url": "https://www.olx.com.ng/en/list/q-{query}/",             "type": "olx"},
    ],
    "gh": [
        {"name": "Jiji.gh",   "url": "https://jiji.com.gh/search?query={query}",               "type": "jiji"},
    ],
    "ke": [
        {"name": "Jiji.ke",   "url": "https://jiji.co.ke/search?query={query}",                "type": "jiji"},
        {"name": "PigiaMe",   "url": "https://www.pigiame.co.ke/search?q={query}",             "type": "generic"},
    ],
    "tz": [
        {"name": "Jiji.tz",   "url": "https://jiji.co.tz/search?query={query}",                "type": "jiji"},
    ],
    "dz": [
        {"name": "Ouedkniss", "url": "https://www.ouedkniss.com/search?q={query}",             "type": "generic"},
    ],
    "ma": [
        {"name": "Avito.ma",  "url": "https://www.avito.ma/fr/maroc/{query}",                  "type": "generic"},
    ],
    # Азия
    "in": [
        {"name": "OLX.in",    "url": "https://www.olx.in/items/q-{query}",                     "type": "olx"},
        {"name": "Quikr",     "url": "https://www.quikr.com/search/{query}",                   "type": "generic"},
    ],
    "pk": [
        {"name": "OLX.pk",    "url": "https://www.olx.com.pk/items/q-{query}",                 "type": "olx"},
    ],
    "id": [
        {"name": "OLX.id",    "url": "https://www.olx.co.id/items/q-{query}",                  "type": "olx"},
    ],
    "ph": [
        {"name": "OLX.ph",    "url": "https://www.olx.ph/items/q-{query}",                     "type": "olx"},
    ],
    # Латинская Америка
    "br": [
        {"name": "OLX.br",    "url": "https://www.olx.com.br/brasil?q={query}",                "type": "olx"},
        {"name": "MercadoLibre","url": "https://listado.mercadolibre.com.br/{query}",           "type": "mercadolibre"},
    ],
    "mx": [
        {"name": "MercadoLibre","url": "https://listado.mercadolibre.com.mx/{query}",          "type": "mercadolibre"},
        {"name": "OLX.mx",    "url": "https://www.olx.com.mx/items/q-{query}",                 "type": "olx"},
    ],
    "ar": [
        {"name": "MercadoLibre","url": "https://listado.mercadolibre.com.ar/{query}",          "type": "mercadolibre"},
    ],
    "co": [
        {"name": "MercadoLibre","url": "https://listado.mercadolibre.com.co/{query}",          "type": "mercadolibre"},
    ],
    # Европа
    "de": [
        {"name": "eBay Kleinanzeigen","url": "https://www.kleinanzeigen.de/s/{query}/k0",      "type": "generic"},
    ],
    "fr": [
        {"name": "Leboncoin", "url": "https://www.leboncoin.fr/recherche?text={query}",        "type": "generic"},
    ],
    "es": [
        {"name": "Wallapop",  "url": "https://es.wallapop.com/app/search?keywords={query}",    "type": "generic"},
        {"name": "Milanuncios","url": "https://www.milanuncios.com/?q={query}",                "type": "generic"},
    ],
    "pl": [
        {"name": "OLX.pl",    "url": "https://www.olx.pl/oferty/q-{query}/",                   "type": "olx"},
    ],
    "ro": [
        {"name": "OLX.ro",    "url": "https://www.olx.ro/oferte/q-{query}/",                   "type": "olx"},
    ],
    # США/Канада
    "us": [
        {"name": "Craigslist","url": "https://www.craigslist.org/search/sss?query={query}",    "type": "craigslist"},
        {"name": "Facebook MP","url": "https://www.facebook.com/marketplace/search/?query={query}", "type": "generic"},
    ],
    "ca": [
        {"name": "Kijiji",    "url": "https://www.kijiji.ca/b-canada/{query}/k0l0",            "type": "generic"},
    ],
}

# Категории для Avito
AVITO_CATS = {
    "real_estate": "nedvizhimost",
    "cars":        "transport",
    "electronics": "elektronika",
    "fashion":     "odezhda-i-aksessuary",
    "business":    "uslugi",
    "furniture":   "dom-i-sad",
    "wholesale":   "tovary-dlya-biznesa",
    "equipment":   "oborudovanie",
}
