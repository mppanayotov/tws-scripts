from vwce_buy.ibkr_client import OrderState

def test_order_state_never_claims_filled_without_an_explicit_ibkr_filled_status():
    pending = OrderState(1, "Submitted", filled=0, remaining=1)
    confirmed = OrderState(1, "Filled", filled=1, remaining=0)
    assert pending.status != "Filled" and confirmed.status == "Filled"
