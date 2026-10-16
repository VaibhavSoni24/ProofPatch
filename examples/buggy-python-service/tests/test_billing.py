import sys
from pathlib import Path
import pytest

# Ensure src is importable
service_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(service_root))

from src.billing import calculate_subscription_invoice


def test_starter_tier_single_seat():
    """1 seat should use Starter tier ($20/seat, 0% discount)."""
    invoice = calculate_subscription_invoice(seats=1, billing_cycle="monthly")
    assert invoice["tier"] == "Starter"
    assert invoice["unit_price"] == 20.00
    assert invoice["raw_subtotal"] == 20.00
    assert invoice["volume_discount_amount"] == 0.00
    assert invoice["final_total"] == 20.00


def test_starter_tier_five_seats():
    """5 seats should still be Starter tier ($20/seat, 0% discount)."""
    invoice = calculate_subscription_invoice(seats=5, billing_cycle="monthly")
    assert invoice["tier"] == "Starter"
    assert invoice["unit_price"] == 20.00
    assert invoice["raw_subtotal"] == 100.00
    assert invoice["volume_discount_amount"] == 0.00
    assert invoice["final_total"] == 100.00


def test_growth_tier_boundary_six_seats():
    """ISSUE #104: 6 seats must enter Growth tier ($18/seat, 10% volume discount).

    Expected:
      6 seats * $18.00 = $108.00 subtotal
      10% discount = $10.80
      Final total = $97.20

    Buggy behavior:
      Evaluates seats > 6 -> False, falls back to Starter tier ($20/seat, total $120.00).
    """
    invoice = calculate_subscription_invoice(seats=6, billing_cycle="monthly")
    assert invoice["tier"] == "Growth", (
        f"Expected Growth tier for 6 seats, but got {invoice['tier']}"
    )
    assert invoice["unit_price"] == 18.00, (
        f"Expected unit price $18.00, got ${invoice['unit_price']:.2f}"
    )
    assert invoice["raw_subtotal"] == 108.00
    assert invoice["volume_discount_amount"] == 10.80
    assert invoice["final_total"] == 97.20, (
        f"Expected final total $97.20 for 6 seats, got ${invoice['final_total']:.2f}"
    )


def test_growth_tier_ten_seats():
    """10 seats is safely within Growth tier."""
    invoice = calculate_subscription_invoice(seats=10, billing_cycle="monthly")
    assert invoice["tier"] == "Growth"
    assert invoice["unit_price"] == 18.00
    assert invoice["raw_subtotal"] == 180.00
    assert invoice["volume_discount_amount"] == 18.00
    assert invoice["final_total"] == 162.00


def test_enterprise_tier_twenty_five_seats():
    """25 seats should enter Enterprise tier ($15/seat, 20% discount)."""
    invoice = calculate_subscription_invoice(seats=25, billing_cycle="monthly")
    assert invoice["tier"] == "Enterprise"
    assert invoice["unit_price"] == 15.00
    assert invoice["raw_subtotal"] == 375.00
    assert invoice["volume_discount_amount"] == 75.00
    assert invoice["final_total"] == 300.00


def test_annual_discount_applied():
    """Annual billing cycle should apply an additional 15% discount."""
    # 10 seats: $162.00 after volume discount * 0.85 = $137.70
    invoice = calculate_subscription_invoice(seats=10, billing_cycle="annual")
    assert invoice["billing_cycle"] == "annual"
    assert invoice["annual_discount_amount"] == 24.30
    assert invoice["final_total"] == 137.70


def test_invalid_arguments_raise_error():
    """Invalid seat count or billing cycle must raise ValueError."""
    with pytest.raises(ValueError):
        calculate_subscription_invoice(seats=0)

    with pytest.raises(ValueError):
        calculate_subscription_invoice(seats=5, billing_cycle="quarterly")
