# Buggy Python Service — SaaS Billing Tier Engine

This bundled example service simulates a production billing service used by ProofPatch to demonstrate an autonomous, verifiable bug-fix lifecycle completely offline without external AI API credits.

## Problem Description
Issue **#104**: `[BUG] 6-seat Growth tier boundary calculates at Starter tier rate ($120.00 instead of $97.20)`

### Expected Tier Rules
- **Starter Tier** (1–5 seats): $20/seat, 0% volume discount.
- **Growth Tier** (6–20 seats): $18/seat, 10% volume discount.
- **Enterprise Tier** (21+ seats): $15/seat, 20% volume discount.
- **Billing Cycles**:
  - `monthly`: standard price.
  - `annual`: additional 15% savings discount applied to discounted subtotal.

### Root Cause
In `src/billing.py`, line 34:
```python
# DEFECT: Boundary check excludes exactly 6 seats from Growth tier
if seats > 6 and seats <= 20:
```
Because of `seats > 6`, a customer ordering 6 seats fails the condition and falls back to Starter Tier ($20/seat with 0% discount = $120.00) instead of the documented Growth Tier ($18 * 6 - 10% = $97.20).

### Correction (Minimal Patch)
```diff
--- a/src/billing.py
+++ b/src/billing.py
@@ -34,3 +34,3 @@
-    if seats > 6 and seats <= 20:
+    if seats >= 6 and seats <= 20:
```

## Running Tests
```bash
pytest tests -v
```
- **Before Patch**: 1 test fails (`test_growth_tier_boundary_six_seats`). Exit code: `1`.
- **After Patch**: All tests pass. Exit code: `0`.
