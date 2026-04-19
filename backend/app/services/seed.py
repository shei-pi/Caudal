from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.categorization_rule import CategorizationRule

EXPENSE_CATEGORIES = [
    {"name": "Supermercados", "color": "#10B981", "icon": "shopping-cart", "rules": [
        "CARREFOUR", "DIA ", "COTO ", "JUMBO", "WALMART", "LA ANONIMA", "DISCO",
        "CHANGOMAS", "VEA ", "VITAL", "MAKRO", "COSTCO",
    ]},
    {"name": "Almacén y verdulería", "color": "#34D399", "icon": "leaf", "rules": []},
    {"name": "Restaurantes y cafés", "color": "#F59E0B", "icon": "utensils", "rules": [
        "MCDONALDS", "BURGER KING", "KFC ", "SUBWAY", "MOSTAZA",
        "STARBUCKS", "CAFE ", "RESTAURANT", "PIZZERIA", "SUSHI",
    ]},
    {"name": "Delivery", "color": "#EF4444", "icon": "truck", "rules": [
        "PEDIDOSYA", "RAPPI", "UBER EATS", "GLOVO",
    ]},
    {"name": "Transporte", "color": "#3B82F6", "icon": "bus", "rules": [
        "SUBE", "UBER ", "CABIFY", "REMIS", "PEAJE", "AUTOPISTA",
    ]},
    {"name": "Combustible", "color": "#6366F1", "icon": "gas-pump", "rules": [
        "YPF", "SHELL", "AXION", "PUMA ", "OIL ", "NAFTA",
    ]},
    {"name": "Salud", "color": "#EC4899", "icon": "heart", "rules": [
        "FARMACIA", "FARMACITY", "OSDE", "SWISS MEDICAL", "GALENO",
        "MEDICUS", "CONSULTA", "CLINICA", "HOSPITAL", "DOCTOR",
    ]},
    {"name": "Educación", "color": "#8B5CF6", "icon": "book", "rules": [
        "COLEGIO", "UNIVERSIDAD", "UDEMY", "COURSERA", "PLATZI",
        "LIBRERIA", "BIBLIOTECA",
    ]},
    {"name": "Entretenimiento", "color": "#06B6D4", "icon": "film", "rules": [
        "NETFLIX", "SPOTIFY", "DISNEY", "HBO ", "AMAZON PRIME",
        "CINE ", "TEATRO", "STEAM ", "PLAYSTATION",
    ]},
    {"name": "Ropa e indumentaria", "color": "#F97316", "icon": "shirt", "rules": [
        "ZARA", "H&M", "ADIDAS", "NIKE ", "FALABELLA", "RIPLEY",
        "INDUMENTARIA", "ROPA ",
    ]},
    {"name": "Electrónica y tecnología", "color": "#64748B", "icon": "laptop", "rules": [
        "GARBARINO", "FRAVEGA", "MUSIMUNDO", "APPLE", "SAMSUNG",
        "MERCADOLIBRE", "TIENDA NUBE",
    ]},
    {"name": "Servicios del hogar", "color": "#A78BFA", "icon": "home", "rules": [
        "EDENOR", "EDESUR", "EDELAP", "METROGAS", "AYSA", "AGUAS ",
        "LUZ ", "GAS ", "AGUA ",
    ]},
    {"name": "Telecomunicaciones", "color": "#60A5FA", "icon": "phone", "rules": [
        "MOVISTAR", "CLARO ", "PERSONAL", "TELECENTRO", "FIBERTEL",
        "CABLEVISION", "DIRECTV", "TELECOM",
    ]},
    {"name": "Alquiler e hipoteca", "color": "#D97706", "icon": "building", "rules": [
        "ALQUILER", "HIPOTECA", "EXPENSAS",
    ]},
    {"name": "Seguros", "color": "#9CA3AF", "icon": "shield", "rules": [
        "SEGURO", "ZURICH", "MAPFRE", "LA CAJA", "SANCOR SEG", "REDES CRUCIALES",
    ]},
    {"name": "Impuestos y tasas", "color": "#6B7280", "icon": "receipt", "rules": [
        "ARBA", "AGIP", "ABL ", "AFIP", "RENTAS", "IMPUESTO",
    ]},
    {"name": "Comisiones bancarias", "color": "#374151", "icon": "bank", "rules": [
        "COMISION", "MANTENIMIENTO", "CARGO ", "DEBITO AUTOMATICO",
    ]},
    {"name": "Retiros y efectivo", "color": "#1F2937", "icon": "cash", "rules": [
        "EXTRACCION", "CAJERO", "ATM ", "RETIRO ",
    ]},
    {"name": "Transferencias enviadas", "color": "#4B5563", "icon": "arrow-right", "rules": [
        "TRANSFERENCIA EMITIDA", "DEBIN ENVIADO",
    ]},
    {"name": "Otros gastos", "color": "#9CA3AF", "icon": "dots", "rules": []},
]

INCOME_CATEGORIES = [
    {"name": "Sueldo y haberes", "color": "#10B981", "icon": "briefcase", "rules": [
        "SUELDO", "HABERES", "REMUNERACION",
    ]},
    {"name": "Honorarios y freelance", "color": "#34D399", "icon": "code", "rules": [
        "HONORARIOS", "FREELANCE",
    ]},
    {"name": "Alquileres cobrados", "color": "#6EE7B7", "icon": "key", "rules": [
        "ALQUILER COBRADO",
    ]},
    {"name": "Dividendos", "color": "#A7F3D0", "icon": "chart", "rules": [
        "DIVIDENDO", "RENTA FCI",
    ]},
    {"name": "Transferencias recibidas", "color": "#D1FAE5", "icon": "arrow-left", "rules": [
        "TRANSFERENCIA RECIBIDA", "DEBIN RECIBIDO",
    ]},
    {"name": "Ventas", "color": "#ECFDF5", "icon": "tag", "rules": [
        "MERCADOPAGO", "MERCADO PAGO", "TIENDAMIA",
    ]},
    {"name": "Otros ingresos", "color": "#F0FDF4", "icon": "plus", "rules": []},
]


def seed_categories(db: Session) -> int:
    existing = db.query(Category).filter(Category.is_system == True).count()  # noqa: E712
    if existing > 0:
        return 0

    count = 0
    for cat_data in EXPENSE_CATEGORIES:
        cat = Category(
            name=cat_data["name"],
            color=cat_data["color"],
            icon=cat_data.get("icon"),
            is_income=False,
            is_system=True,
        )
        db.add(cat)
        db.flush()
        for pattern in cat_data.get("rules", []):
            rule = CategorizationRule(
                category_id=cat.id,
                pattern=pattern,
                match_type="contains",
                priority=0,
                is_active=True,
            )
            db.add(rule)
        count += 1

    for cat_data in INCOME_CATEGORIES:
        cat = Category(
            name=cat_data["name"],
            color=cat_data["color"],
            icon=cat_data.get("icon"),
            is_income=True,
            is_system=True,
        )
        db.add(cat)
        db.flush()
        for pattern in cat_data.get("rules", []):
            rule = CategorizationRule(
                category_id=cat.id,
                pattern=pattern,
                match_type="contains",
                priority=0,
                is_active=True,
            )
            db.add(rule)
        count += 1

    db.commit()
    return count
