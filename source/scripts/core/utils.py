def clamp(value, minimum=0, maximum=100):
    """Keep numeric values constrained to an inclusive range."""
    return max(minimum, min(maximum, value))