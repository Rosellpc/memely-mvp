def calculate_calories(weight, activity):

    factor = {"low": 1.2, "medium": 1.5, "high": 1.8}

    calories = weight * 24 * factor[activity]

    return calories
