def has_active_vwce_buy(orders: list[tuple[int, object, object, object]], con_id: int) -> bool:
    inactive = {"Filled", "Cancelled", "Inactive", "ApiCancelled"}
    return any(getattr(contract, "conId", None) == con_id and getattr(order, "action", "") == "BUY" and getattr(state, "status", "") not in inactive for _id, contract, order, state in orders)
