def calculate_score(base: int, multiplier: int, premium: bool) -> int:
    score = base * multiplier
    if premium:
        score += 25
    if score > 100:
        return 100
    if score < 0:
        return 0
    return score