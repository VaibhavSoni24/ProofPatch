"""SaaS Subscription Billing Tier and Discount Calculator."""
from typing import Dict, Any


def calculate_subscription_invoice(seats: int, billing_cycle: str = "monthly") -> Dict[str, Any]:
    """Calculate the invoice details for a given seat count and billing cycle.

    Tier Rules:
    - Starter: 1-5 seats, $20.00/seat, 0% volume discount
    - Growth: 6-20 seats, $18.00/seat, 10% volume discount
    - Enterprise: 21+ seats, $15.00/seat, 20% volume discount

    Cycle Discounts:
    - monthly: 0% discount
    - annual: 15% discount on total discounted subtotal

    Raises:
        ValueError: If seats < 1 or billing_cycle not in ('monthly', 'annual')
    """
    if seats < 1:
        raise ValueError("Seat count must be at least 1")

    valid_cycles = ("monthly", "annual")
    if billing_cycle not in valid_cycles:
        raise ValueError(f"Invalid billing cycle: {billing_cycle}. Must be one of {valid_cycles}")

    # Determine Tier Pricing and Volume Discount
    # DEFECT: Boundary check for Growth tier uses > 6 instead of >= 6.
    # When seats == 6, this condition is False and it falls through to the Starter tier ($20/seat, 0% discount).
    if seats > 6 and seats <= 20:
        tier_name = "Growth"
        unit_price = 18.00
        volume_discount_rate = 0.10
    elif seats > 20:
        tier_name = "Enterprise"
        unit_price = 15.00
        volume_discount_rate = 0.20
    else:
        tier_name = "Starter"
        unit_price = 20.00
        volume_discount_rate = 0.0

    raw_subtotal = round(seats * unit_price, 2)
    volume_discount_amount = round(raw_subtotal * volume_discount_rate, 2)
    subtotal_after_volume = round(raw_subtotal - volume_discount_amount, 2)

    # Annual billing discount
    annual_discount_rate = 0.15 if billing_cycle == "annual" else 0.0
    annual_discount_amount = round(subtotal_after_volume * annual_discount_rate, 2)
    final_total = round(subtotal_after_volume - annual_discount_amount, 2)

    return {
        "seats": seats,
        "tier": tier_name,
        "unit_price": unit_price,
        "raw_subtotal": raw_subtotal,
        "volume_discount_rate": volume_discount_rate,
        "volume_discount_amount": volume_discount_amount,
        "billing_cycle": billing_cycle,
        "annual_discount_amount": annual_discount_amount,
        "final_total": final_total,
    }
