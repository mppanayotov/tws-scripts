from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from vwce_buy.market_status import historical_medians


def test_historical_medians_completed_dates_and_invalid_bars():
    first = date(2026, 8, 1)
    bars = [
        SimpleNamespace(
            date=(first + timedelta(days=index)).strftime("%Y%m%d"),
            open=str(index + 1),
            high=str(index + 3),
            low=str(index + 1),
            close=str(index + 2),
        )
        for index in range(1, 32)
    ]
    bars.reverse()
    bars.insert(
        0, SimpleNamespace(date="20260902", open="invalid", high=0, low=0, close=0)
    )
    result = historical_medians(bars, completed_through=date(2026, 9, 1))
    assert result.count == 30
    assert (result.first_date, result.last_date) == (date(2026, 8, 3), date(2026, 9, 1))
    assert result.median_open == Decimal("17.5")
    assert result.median_close == Decimal("18.5")
    assert result.median_typical == Decimal("18.5")

    with pytest.raises(ValueError, match="duplicate"):
        historical_medians([*bars, bars[-1]], completed_through=date(2026, 9, 1))
    with pytest.raises(ValueError, match="inconsistent"):
        historical_medians(
            [
                *bars[:-1],
                SimpleNamespace(date="20260802", open=10, high=9, low=8, close=10),
            ],
            completed_through=date(2026, 9, 1),
        )
    with pytest.raises(ValueError, match="invalid OHLC"):
        historical_medians(
            [
                *bars[:-1],
                SimpleNamespace(date="20260802", open="NaN", high=9, low=8, close=9),
            ],
            completed_through=date(2026, 9, 1),
        )
    with pytest.raises(ValueError, match="need 30"):
        historical_medians(bars[:29], completed_through=date(2026, 9, 1))
