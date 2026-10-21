"""Deterministic sample menus. No AI, calorie prescription or medical personalization."""

DAYS = ('Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo')
BREAKFASTS = ('Avena con fruta y yogur', 'Tostadas con huevo y tomate', 'Yogur con fruta y semillas')
VEGETARIAN = ('Lentejas con arroz y verduras', 'Garbanzos con quinoa y ensalada', 'Pasta con tofu y verduras')
BALANCED = ('Pollo con arroz y verduras', 'Pescado con papa y ensalada', 'Lentejas con quinoa y verduras')
DINNERS = ('Sopa de verduras con tostadas y queso', 'Tortilla de verduras con pan', 'Ensalada de garbanzos y aguacate')


def build_plan(preference):
    lunches = VEGETARIAN if preference == 'vegetarian' else BALANCED
    return [
        {'day': day, 'meals': [
            {'label': 'Desayuno', 'title': BREAKFASTS[i % len(BREAKFASTS)]},
            {'label': 'Almuerzo', 'title': lunches[i % len(lunches)]},
            {'label': 'Cena', 'title': DINNERS[i % len(DINNERS)]},
        ]}
        for i, day in enumerate(DAYS)
    ]
