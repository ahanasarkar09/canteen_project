import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

try:
    from database import (
        init_db,
        get_menu_items, 
        update_menu, 
        add_menu_item,
        get_all_orders, 
        update_order_status, 
        get_pending_recharges, 
        approve_recharge
    )
except ImportError:
    from database import (
        init_db,
        get_menu_items, 
        update_menu, 
        add_menu_item,
        get_all_orders, 
        update_order_status, 
        get_pending_recharges, 
        approve_recharge
    )

def admin_main():
    # Initialize tables if not already created
    try:
        init_db()
    except Exception:
        pass

    st.title("Canteen Admin Panel")

    tab1, tab2, tab3 = st.tabs(["Incoming Orders", "Recharge Requests", "Manage Menu"])

    # TAB 1: Process Orders
    with tab1:
        st.subheader("Order Management")
        orders = get_all_orders()
        if orders:
            for order in orders:
                order_id, stu_id, name, amount, quantity, status, created_at = order
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.write(f"**Order #{order_id}** - Student: {name} (ID: {stu_id})")
                    st.write(f"Total: ₹{amount:.2f} | Placed at: {created_at}")
                with col2:
                    st.write(f"Status: **{status}**")
                with col3:
                    new_status = st.selectbox(
                        "Update Status",
                        ["Placed", "Preparing", "Ready", "Collected"],
                        index=["Placed", "Preparing", "Ready", "Collected"].index(status),
                        key=f"status_{order_id}"
                    )
                    if new_status != status:
                        update_order_status(order_id, new_status)
                        st.success(f"Order #{order_id} updated to {new_status}")
                        st.rerun()
                st.divider()
        else:
            st.info("No incoming orders.")

    # TAB 2: Approve Cash Recharges
    with tab2:
        st.subheader("Pending Cash Recharges")
        recharges = get_pending_recharges()
        st_autorefresh(interval=2500, limit=None, key="order_status_refresh")
        if recharges:
            for req in recharges:
                req_id, stu_id, name, amount = req
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Request #{req_id}**: {name} (ID: {stu_id}) deposited **₹{amount:.2f}**")
                with col2:
                    if st.button("Approve Cash", key=f"app_{req_id}"):
                        approve_recharge(req_id)
                        st.success(f"Approved ₹{amount:.2f} for Student {name}")
                        st.rerun()
        else:
            st.info("No pending recharge requests.")

    # TAB 3: Manage Menu & Add New Items
    with tab3:
        st.subheader("Add New Menu Item")
        with st.form("add_item_form"):
            new_name = st.text_input("Item Name")
            new_price = st.number_input("Price (₹)", min_value=0.0, step=1.0)
            new_available = st.checkbox("Available Immediately", value=True)
            submit_item = st.form_submit_button("Add Item")

        if submit_item:
            if not new_name.strip():
                st.error("Please enter a valid item name.")
            else:
                add_menu_item(new_name, new_price, 1 if new_available else 0)
                st.success(f"Successfully added '{new_name}' to the menu!")
                st.rerun()

        st.divider()
        st.subheader("Edit Existing Menu & Availability")
        menu_items = get_menu_items()
        edited_menu = st.data_editor(
            menu_items,
            use_container_width=True,
            disabled=["item_id", "item_name"],
            column_config={
                "price": st.column_config.NumberColumn("Price (₹)", min_value=0, step=1),
                "available": st.column_config.CheckboxColumn("Available")
            },
            hide_index=True
        )
        if st.button("Save Menu Changes"):
            update_menu(edited_menu)
            st.success("Menu updated successfully!")

if __name__ == "__main__":
    admin_main()