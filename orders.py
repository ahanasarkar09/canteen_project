import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

try:
    from .database import (
        get_available_menu, 
        place_order, 
        request_recharge, 
        get_student_orders, 
        get_student_by_id
    )
except ImportError:
    from database import (
        get_available_menu, 
        place_order, 
        request_recharge, 
        get_student_orders, 
        get_student_by_id
    )

def total_bill(order_items):
    for item in order_items:
        item["Total"] = item["price"] * item["quantity"]
    return sum(item["Total"] for item in order_items)

def main():
    student = st.session_state.get("student")

    if student is None:
        st.warning("Please log in before placing an order.")
        if st.button("Go to Login"):
            st.session_state["page"] = "login"
            st.rerun()
        return

    # Sync latest balance from database
    updated_stu = get_student_by_id(student.student_id)
    if updated_stu:
        student.balance = updated_stu[4]

    st.title(f"Welcome, {student.name}!")
    st.info(f"Class: **{student.student_class}** | Digital Token Balance: **₹{student.balance:.2f}**")


    page = st.segmented_control(
    "Navigate",
    options=["Today's Menu", "Request Cash Recharge", "Your orders and status"],
    default="Today's Menu",
    key="student_page",
    label_visibility="collapsed"
    )

    #PAGE 1: Place Order
    if page=="Today's Menu":
        st.subheader("Today's Menu")
        menu = get_available_menu()
        if not menu:
            st.warning("No menu items available at the moment.")
        else:
            with st.form("order_form"):
                selected_items = []
                for item in menu:
                    item_id, item_name, item_price = item[0], item[1], item[2]
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{item_name}**")
                    with col2:
                        st.write(f"₹{item_price:.2f}")
                    with col3:
                        quantity = st.number_input(
                            f"Qty", min_value=0, step=1, key=f"qty_{item_id}", label_visibility="collapsed"
                        )

                    if quantity > 0:
                        selected_items.append({
                            "item_id": item_id,
                            "item_name": item_name,
                            "price": item_price,
                            "quantity": quantity,
                        })

                submitted = st.form_submit_button("Place Order")

            if submitted:
                if not selected_items:
                    st.warning("Please select at least one item.")
                else:
                    bill = total_bill(selected_items)
                    if student.balance < bill:
                        st.error(f"Insufficient token balance! Order total: ₹{bill:.2f}, Balance: ₹{student.balance:.2f}")
                    else:
                        success = place_order(student.student_id, [i['price'] for i in selected_items], [i['quantity'] for i in selected_items])
                        print(success)
                        if success:
                            st.success(f"Order placed successfully!")
                            st.rerun()
                        else:
                            st.error("Error placing order")

    # PAGE 2: Cash Recharge Request
    elif page=="Request Cash Recharge":
        st.subheader("Request Cash Recharge")
        st.write("Deposit cash with the canteen staff, then submit a recharge request here to credit your account.")
        with st.form("recharge_form"):
            amount = st.number_input("Enter Amount Deposited (₹)", min_value=10, step=10)
            req_submitted = st.form_submit_button("Submit Request")

        if req_submitted:
            request_recharge(student.student_id, amount)
            st.success(f"Recharge request for ₹{amount} submitted! Please pay cash to canteen staff for approval.")

    # PAGE 3: Track Orders
    elif page=="Your orders and status":
        st.subheader("Your Orders & Status")
        
        # Automatically refresh this page every 5000 milliseconds (5 seconds)
        #st_autorefresh(interval=2500, limit=None, key="order_status_refresh")
        
        orders = get_student_orders(student.student_id)
        if orders:
            df = pd.DataFrame(orders, columns=["Order ID", "Price (₹)", "Quantity", "Status", "Placed At"])
            st.dataframe(df, use_container_width=True)
            st.caption("🔄 Status updates automatically in real-time.")
        else:
            st.info("No orders found.")
