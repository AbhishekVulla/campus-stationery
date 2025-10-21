# mylibrary.py
# pricing logic for "Campus Stationery: any 3 for $5"
# This file only holds the data and the calculator so app.py can stay focused on UI.

# Catalog: a tiny set of items with codes, names, and unit prices
products = {
    "PEN01": {"name": "Gel Pen",      "price": 2.10},
    "HIL01": {"name": "Highlighter",  "price": 2.00},
    "NBK01": {"name": "A5 Notebook",  "price": 2.40},
    "STK01": {"name": "Sticky Notes", "price": 1.60},
    "ERS01": {"name": "Eraser",       "price": 0.90},
}

# bundle rule
bundle = {"size": 3, "bundle_price": 5.00}

# student discount after bundles (cap at $2)
student_rate = 0.10
student_cap = 2.00

# GST toggled in the UI. It is the last step in the math.
gst_rate = 0.09   # 9%

# make a flat list of single units so bundling is easy
def _expand_units(cart):
    '''
    make a flat list of single units so bundling is easy

    Example: {'PEN01': 2, 'NBK01': 1}  becomes [('PEN01', 2.10, 'Gel Pen'), ('PEN01', 2.10, 'Gel Pen'), ('NBK01', 2.40, 'A5 Notebook')]
    '''
    units = []
    for code, qty in cart.items():
        price = products[code]["price"]
        name = products[code]["name"]
        units.extend([(code, price, name)] * int(qty))
    return units

# main calculator function
def compute(cart, *, student=False, gst_on=False):
    """
    do all price math:
      1) build lines
      2) bundle any 3 (take high price first)
      3) student discount (cap at $2)
      4) GST if on
    """
    # Step 1: lines per item code before any discount
    lines = []
    pre_subtotal = 0.0
    cleaned_cart = {}
    total_units = 0

    for code, qty in cart.items():
        q = int(qty)
        if q == 0:
            continue
        unit = products[code]["price"]
        line_total = round(unit * q, 2)
        pre_subtotal += line_total
        cleaned_cart[code] = q
        total_units += q
        lines.append(
            {
                "code": code,
                "name": products[code]["name"],
                "qty": q,
                "unit_price": unit,
                "line_subtotal": line_total,
            }
        )

    # Step 2: sort units from high to low so savings are maximized
    units = sorted(_expand_units(cleaned_cart), key=lambda t: t[1], reverse=True)

    i = 0
    after_bundles = 0.0
    bundles_applied = 0
    bundle_savings = 0.0
    bundle_groups = []              # store item names so ui can show groups
    bundled_count = {c: 0 for c in cleaned_cart.keys()}

    while i < len(units):
        group = units[i : i + bundle["size"]]
        if len(group) == bundle["size"]:
            group_sum = sum(x[1] for x in group)
            charge = min(group_sum, bundle["bundle_price"])
            # count as bundle only if it actually saves money
            if group_sum > bundle["bundle_price"]:
                bundles_applied += 1
                bundle_savings += group_sum - bundle["bundle_price"]
                bundle_groups.append([x[2] for x in group]) # store item names
                for x in group:
                    bundled_count[x[0]] = bundled_count.get(x[0], 0) + 1
            after_bundles += charge
            i += bundle["size"]
        else:
            # leftover < bundle size: pay normal unit prices
            after_bundles += sum(x[1] for x in group)
            i += len(group)

    after_bundles = round(after_bundles, 2)
    bundle_savings = round(bundle_savings, 2)

    # Step 3: student discount on the amount after bundles (cap $2)
    stud_disc = 0.0
    if student:
        stud_disc = min(round(student_rate * after_bundles, 2), student_cap)

    # Step 4: GST on the net amount (after student discount) if toggled
    taxable = after_bundles - stud_disc
    gst_amt = round(gst_rate * taxable, 2) if gst_on else 0.0
    grand = round(taxable + gst_amt, 2)

    return {
        "item_lines": lines,
        "pre_subtotal": round(pre_subtotal, 2),
        "bundles": {
            "bundle_size": bundle["size"],
            "bundle_price": bundle["bundle_price"],
            "applied": bundles_applied,
            "savings": bundle_savings,
            "groups": bundle_groups,
            "bundled_units": bundled_count,
        },
        "after_bundles_subtotal": after_bundles,
        "student": {
            "rate": student_rate,
            "cap": student_cap,
            "discount": round(stud_disc, 2),
        },
        "gst": {
            "rate": gst_rate if gst_on else 0.0,
            "amount": gst_amt,
        },
        "grand_total": grand,
        "total_units": total_units,
    }
