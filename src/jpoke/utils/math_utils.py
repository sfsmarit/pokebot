from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_DOWN


def round_half_up(v: float) -> int:
    """四捨五入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_UP))


def round_half_down(v: float) -> int:
    """五捨五超入"""
    return int(Decimal(str(v)).quantize(Decimal('0'), rounding=ROUND_HALF_DOWN))


def frac(v: float) -> float:
    """小数部分"""
    return v - int(v)
