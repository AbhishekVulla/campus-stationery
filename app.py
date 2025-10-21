# app.py
# streamlit ui for our campus stationery app

from datetime import datetime
import csv
import io
import streamlit as st

# bring in data and pricing functions from helper module
from mylibrary import (
    products,
    bundle,
    student_cap,
    student_rate,
    gst_rate,
    compute,
)

# pictures for a friendly shelf view (put image files in an "images" folder)
PRODUCT_IMAGES = {
    "PEN01": "images/pen.png",
    "HIL01": "images/highlighter.png",
    "NBK01": "images/notebook.png",
    "STK01": "images/sticky.png",
    "ERS01": "images/eraser.png",
}

# page header
st.set_page_config(page_title="Campus Stationery - any 3 for $5", layout="wide")
st.title("Campus Stationery : Any 3 for $5")
st.caption("CTD 1D Project")

# sidebar toggles
with st.sidebar:
    st.header("Options")
    # we keep toggle values in session_state using the widget keys
    st.checkbox("Student 10% (cap $2)", key="student", value=st.session_state.get("student", False))
    st.checkbox("GST", key="gst_on", value=st.session_state.get("gst_on", False))
    st.write(f"Bundle rule: any {bundle['size']} for ${bundle['bundle_price']:.2f}")
    st.write(f"Student discount: {int(student_rate*100)}% up to ${student_cap:.2f}")
    st.write(f"GST rate: {int(gst_rate*100)}%")

# shelf pictures
with st.expander("See what's on the shelf (pictures)", expanded=False):
    cols = st.columns(5)
    for col, code in zip(cols, products.keys()):
        with col:
            img_path = PRODUCT_IMAGES.get(code)
            if img_path:
                # Stretch image to the container width (Streamlit's newer argument)
                st.image(img_path, width="stretch")
            # Escape the dollar sign so markdown shows it literally
            st.markdown(f"**{products[code]['name']}**  \n\\${products[code]['price']:.2f}")

# quantities
st.subheader("Add items")

# one number box per item code
qty = {}
cols = st.columns(2)
for i, (code, meta) in enumerate(products.items()):
    with cols[i % 2]:
        qty[code] = st.number_input(
            f"{meta['name']} (${meta['price']:.2f})",  # we use f string to make it more user friendly, and use .2f to format it to look neat
            min_value=0,
            max_value=50,
            step=1,
            key=code,
            help="Enter quantity (0-50).",
        )

# run the calculator using the helper module
result = compute(
    qty,
    student=st.session_state.get("student", False),
    gst_on=st.session_state.get("gst_on", False),
)

# for very large carts we show a hint so the demo stays manageable
if result["total_units"] > 30:
    st.warning("Heads up: large cart detected. Consider splitting into multiple receipts to avoid mistakes.")

# choose how to sort the receipt table
sort_choice = st.selectbox(
    "Sort items by",
    ["Spend (desc)", "Quantity (desc)", "Name (A->Z)"],
    index=0,
)

# build rows for the receipt table (simple dicts)
rows = [
    {
        "Item": line["name"],
        "Qty": line["qty"],
        "Unit": f"${line['unit_price']:.2f}",
        "Line": f"${line['line_subtotal']:.2f}",
        "Bundled": result["bundles"]["bundled_units"].get(line["code"], 0),
    }
    for line in result["item_lines"]
]

# apply sorting chosen above
if rows:
    if sort_choice == "Spend (desc)":
        rows.sort(key=lambda r: float(r["Line"].replace("$", "")), reverse=True)
    elif sort_choice == "Quantity (desc)":
        rows.sort(key=lambda r: r["Qty"], reverse=True)
    else:
        rows.sort(key=lambda r: r["Item"])

# small helper for natural text like “1 point” vs “2 points”
def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")

# receipt
st.subheader("Receipt")

if not rows:
    # friendly greeter when cart is empty so a new user knows what to try first
    st.info("Hi! Add any 3 items for $5.  \n\nTip: notebooks are the best deal.")
else:
    st.table(rows)

# show the breakdown of amounts
st.markdown(f"**Pre-subtotal:** ${result['pre_subtotal']:.2f}")
st.markdown(f"**Bundles applied:** {result['bundles']['applied']} : savings ${result['bundles']['savings']:.2f}")
st.markdown(f"**After bundles:** ${result['after_bundles_subtotal']:.2f}")

if st.session_state.get("student", False):
    st.markdown(
        f"**Student discount** ({int(student_rate*100)}% up to ${student_cap:.2f}): -${result['student']['discount']:.2f}"
    )
    # cap message when it hits max
    if result["student"]["discount"] == student_cap:
        st.caption("Cap hit: max $2 reached.")

if st.session_state.get("gst_on", False):
    st.markdown(f"**GST** ({int(gst_rate*100)}%): ${result['gst']['amount']:.2f}")

# show the final amount and how much money the user saved in total
saved_bundle = result["bundles"]["savings"]
saved_student = result["student"]["discount"] if st.session_state.get("student", False) else 0.0
saved_total = saved_bundle + saved_student
st.success(
    f"Grand Total: \\${result['grand_total']:.2f}  \n\n"
    f"You saved \\${saved_total:.2f} today (Bundles \\${saved_bundle:.2f} + Student \\${saved_student:.2f})."
)

# Edge-case prompt: if 2 mod 3 units, nudge to add 1 more for bundle
if result["total_units"] % bundle["size"] == 2 and result["total_units"] > 0:
    st.info("Add 1 more to get the $5 bundle.")

# show bundle groups e.g. "Notebook + Highlighter + Sticky"
bundle_groups = result["bundles"]["groups"]
if result["bundles"]["applied"] > 0 and bundle_groups:
    grouped = "; ".join([" + ".join(g) for g in bundle_groups])
    st.caption(f"Bundle groups: {grouped}")

# simple rewards: 1 point per $5 after bundles
points = int(result["after_bundles_subtotal"] // 5)
st.caption("Rewards: " + plural(points, "point") + " earned this purchase.")

# CSV download 
if rows:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["Item", "Qty", "Unit", "Line", "Bundled"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    today = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="Download receipt (CSV)",
        data=buf.getvalue(),
        file_name=f"receipt_{today}.csv",
        mime="text/csv",
    )

# reset button
def _reset_cart():
    # set all quantities back to 0
    for code in products.keys():
        st.session_state[code] = 0

st.button("Reset cart", on_click=_reset_cart)
