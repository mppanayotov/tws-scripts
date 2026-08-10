from decimal import Decimal
from ibapi.contract import Contract
from ibapi.order import Order
from .config import DESTINATION
from .contract import ResolvedContract

def build_contract(resolved: ResolvedContract) -> Contract:
    contract = Contract()
    contract.conId, contract.exchange, contract.secType, contract.currency = resolved.con_id, DESTINATION, "STK", "EUR"
    return contract

def build_order(account: str, price: Decimal) -> Order:
    order = Order()
    order.account, order.action, order.orderType = account, "BUY", "LMT"
    order.totalQuantity, order.lmtPrice, order.tif = 1, float(price), "DAY"
    order.outsideRth, order.transmit, order.orderRef = False, True, "VWCE_DCA"
    return order
