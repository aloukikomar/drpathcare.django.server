from decimal import Decimal
from django.core.exceptions import ValidationError
from django.apps import apps

Coupon = apps.get_model("bookings", "Coupon")
LabTest = apps.get_model("lab", "LabTest")
Profile = apps.get_model("lab", "Profile")
Package = apps.get_model("lab", "Package")


def get_booking_calculations(client_data, items, coupon_id=None):
    """
    Validates pricing and recalculates all totals from authoritative DB values.

    Args:
        client_data (dict): Payload from frontend containing totals and discounts:
            {
              "base_total": "150.00",
              "offer_total": "100.00",
              "final_amount": "90.00",
              "discount_amount": "60.00",
              "coupon_discount": "10.00",
              "admin_discount": "5.00",
              ...
            }
        items (list): Booking item payload from frontend, each with:
            {
              "product_type": "lab_test" | "lab_profile" | "lab_package",
              "product_id": 1,
              "base_price": "150.00",
              "offer_price": "100.00",
              ...
            }
        coupon_id (uuid): ID of the applied coupon if any.

    Returns:
        (bool, dict | str): 
            (True, result_dict) if valid,
            (False, error_message) if invalid
    """

    # ✅ Step 1: Calculate actual totals from DB
    base_total = Decimal("0.00")
    offer_total = Decimal("0.00")
    item_results = []

    for item in items:
        product_type = item.get("product_type")
        product_id = item.get("product_id")

        # Pull actual product prices from DB
        if product_type == "lab_test":
            product = LabTest.objects.filter(id=product_id).first()
        elif product_type == "lab_profile":
            product = Profile.objects.filter(id=product_id).first()
        elif product_type == "lab_package":
            product = Package.objects.filter(id=product_id).first()
        else:
            return False, f"Invalid product type: {product_type}"

        if not product:
            return False, f"Product {product_type} with ID {product_id} not found"

        db_base_price = Decimal(product.price or 0)
        db_offer_price = Decimal(getattr(product, "offer_price", None) or db_base_price)

        base_total += db_base_price
        offer_total += db_offer_price

        item_results.append({
            "product_type": product_type,
            "product_id": product_id,
            "base_price": db_base_price,
            "offer_price": db_offer_price,
            "patient": item.get("patient")
        })

    # ✅ Step 2: Apply coupon (if valid)
    coupon_discount = Decimal("0.00")
    if coupon_id:
        coupon = Coupon.objects.filter(id=coupon_id).first()
        if not coupon:
            return False, "Coupon not found."
        if not coupon.is_valid_now():
            return False, "Coupon is expired or inactive."

        if coupon.discount_type == "percent":
            coupon_discount = base_total * (coupon.discount_value / Decimal("100"))
            if coupon.max_discount_amount:
                coupon_discount = min(coupon_discount, coupon.max_discount_amount)
        else:
            coupon_discount = coupon.discount_value

    # ✅ Step 3: Admin discount
    admin_discount = Decimal(str(client_data.get("admin_discount") or 0))

    # ✅ Step 4: Final total calculations
    print(base_total , offer_total , coupon_discount , admin_discount)
    total_discount = (base_total - offer_total) + coupon_discount + admin_discount
    final_amount = base_total - total_discount
    if final_amount < 0:
        final_amount = Decimal("0.00")

    # ✅ Step 5: Compare with client data (within small tolerance)
    def close_enough(server_val, client_val, tolerance=Decimal("1.00")):
        return abs(server_val - client_val) <= tolerance

    posted_base = Decimal(str(client_data.get("base_total") or "0"))
    posted_offer = Decimal(str(client_data.get("offer_total") or "0"))
    posted_final = Decimal(str(client_data.get("final_amount") or "0"))

    if not close_enough(base_total, posted_base):
        return False, f"Base total mismatch: server {base_total}, client {posted_base}"

    if not close_enough(offer_total, posted_offer):
        return False, f"Offer total mismatch: server {offer_total}, client {posted_offer}"

    if not close_enough(final_amount, posted_final):
        return False, f"Final amount mismatch: server {final_amount}, client {posted_final}"

    # ✅ Step 6: Return validated calculation summary
    return True, {
        "base_total": base_total,
        "offer_total": offer_total,
        "coupon_discount": coupon_discount,
        "admin_discount": admin_discount,
        "total_discount": total_discount,
        "final_amount": final_amount,
        "items": item_results
    }
