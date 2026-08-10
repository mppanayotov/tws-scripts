def vwce_position(positions: list[tuple[str, object, float, float]], con_id: int) -> float:
    return sum(position for _account, contract, position, _cost in positions if getattr(contract, "conId", None) == con_id)
