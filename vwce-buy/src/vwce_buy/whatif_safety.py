def require_whatif_postconditions(active_buy: bool, position_before: float, position_after: float) -> None:
    if active_buy: raise RuntimeError("CRITICAL SAFETY FAILURE: PAPER WhatIf unexpectedly created a working order.")
    if position_before != position_after: raise RuntimeError("CRITICAL SAFETY FAILURE: VWCE position changed during WhatIf test.")
