import mysql.connector
import pandas as pd
from werkzeug.security import generate_password_hash
import streamlit as st


def get_db_connection():
    db_config = st.secrets["mysql"]
    
    return mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        port=int(db_config["port"]),
        ssl_ca="ca.pem",
        ssl_verify_cert=True,
        ssl_verify_identity=True
    )

def init_db():
    mydb = get_db_connection()
    cursor = mydb.cursor()
    
    # Create Student table with token balance
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Student (
            stu_id INT PRIMARY KEY,
            stu_name VARCHAR(100),
            stu_class VARCHAR(50),
            password VARCHAR(255),
            balance DECIMAL(10, 2) DEFAULT 0.00
        )
    """)
    
    # Create Menu table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Menu (
            item_id INT AUTO_INCREMENT PRIMARY KEY,
            item_name VARCHAR(100),
            price DECIMAL(10, 2),
            available INT DEFAULT 1
        )
    """)
    
    # Create Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Orders (
            order_id INT AUTO_INCREMENT PRIMARY KEY,
            item_id INT,
            stu_id INT,
            price DECIMAL(10, 2),
            quantity SMALLINT,
            status VARCHAR(50) DEFAULT 'Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stu_id) REFERENCES Student(stu_id),
            FOREIGN KEY (item_id) REFERENCES Menu(item_id)
        )
    """)

    # Create Recharge Requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RechargeRequests (
            request_id INT AUTO_INCREMENT PRIMARY KEY,
            stu_id INT,
            amount DECIMAL(10, 2),
            status VARCHAR(50) DEFAULT 'Pending',
            requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (stu_id) REFERENCES Student(stu_id)
        )
    """)

    mydb.commit()
    cursor.close()
    mydb.close()

def register_student(student, password):
    mydb = get_db_connection()
    try:
        mycursor = mydb.cursor()
        password_hash = generate_password_hash(password)
        query = "INSERT INTO Student(stu_id, stu_name, stu_class, password, balance) VALUES (%s, %s, %s, %s, 0.00)"
        values = (student.student_id, student.name, student.student_class, password_hash)
        mycursor.execute(query, values)
        mydb.commit()
        mycursor.close()
        return True
    except mysql.connector.Error as exc:
        print(f"Database error: {exc}")
        return False
    finally:
        mydb.close()

def get_student_by_id(student_id):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT stu_id, stu_name, stu_class, password, balance FROM Student WHERE stu_id = %s"
    mycursor.execute(query, (student_id,))
    student = mycursor.fetchone()
    mycursor.close()
    mydb.close()
    return student

def get_menu_items():
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT * FROM Menu"
    mycursor.execute(query)
    column_names = [column[0] for column in mycursor.description]
    menu_items = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    return pd.DataFrame(menu_items, columns=column_names)

def update_menu(edited_menu):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "UPDATE Menu SET price = %s, available = %s WHERE item_id = %s"
    for item in edited_menu.to_dict("records"):
        values = (item["price"], item["available"], item["item_id"])
        mycursor.execute(query, values)
    mydb.commit()
    mycursor.close()
    mydb.close()
    return True

def get_available_menu():
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT * FROM Menu WHERE available = 1"
    mycursor.execute(query)
    menu_items = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    return menu_items

# --- Token & Order Handling Functions ---

def place_order(stu_id, price, quantity):
    total_amount = sum([i*j for i,j in zip(price,quantity)])
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    
    # Check balance
    mycursor.execute("SELECT balance FROM Student WHERE stu_id = %s", (stu_id,))
    res = mycursor.fetchone()
    if not res or res[0] < total_amount:
        mycursor.close()
        mydb.close()
        return False, "Insufficient token balance."

    # Deduct balance and insert order
    new_balance = res[0] - total_amount
    mycursor.execute("UPDATE Student SET balance = %s WHERE stu_id = %s", (new_balance, stu_id))
    for i,j in zip(price,quantity):
        mycursor.execute("INSERT INTO Orders (stu_id, price, quantity, status) VALUES (%s, %s, %s, 'Placed')", (stu_id, i, j))
    
    mydb.commit()
    mycursor.close()
    mydb.close()
    return True

def request_recharge(stu_id, amount):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "INSERT INTO RechargeRequests (stu_id, amount, status) VALUES (%s, %s, 'Pending')"
    mycursor.execute(query, (stu_id, amount))
    mydb.commit()
    mycursor.close()
    mydb.close()

def get_student_orders(stu_id):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT order_id, price, quantity, status, created_at FROM Orders WHERE stu_id = %s ORDER BY created_at DESC"
    mycursor.execute(query, (stu_id,))
    orders = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    return orders

def get_all_orders():
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT o.order_id, o.stu_id, s.stu_name, o.price, o.quantity, o.status, o.created_at FROM Orders o JOIN Student s ON o.stu_id = s.stu_id ORDER BY o.created_at DESC"
    mycursor.execute(query)
    orders = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    return orders

def update_order_status(order_id, status):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "UPDATE Orders SET status = %s WHERE order_id = %s"
    mycursor.execute(query, (status, order_id))
    mydb.commit()
    mycursor.close()
    mydb.close()

def get_pending_recharges():
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "SELECT r.request_id, r.stu_id, s.stu_name, r.amount FROM RechargeRequests r JOIN Student s ON r.stu_id = s.stu_id WHERE r.status = 'Pending'"
    mycursor.execute(query)
    recharges = mycursor.fetchall()
    mycursor.close()
    mydb.close()
    return recharges

def approve_recharge(request_id):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    
    mycursor.execute("SELECT stu_id, amount FROM RechargeRequests WHERE request_id = %s", (request_id,))
    req = mycursor.fetchone()
    if req:
        stu_id, amount = req
        mycursor.execute("UPDATE Student SET balance = balance + %s WHERE stu_id = %s", (amount, stu_id))
        mycursor.execute("UPDATE RechargeRequests SET status = 'Approved' WHERE request_id = %s", (request_id,))
        mydb.commit()
    
    mycursor.close()
    mydb.close()

def add_menu_item(item_name, price, available):
    mydb = get_db_connection()
    mycursor = mydb.cursor()
    query = "INSERT INTO Menu (item_name, price, available) VALUES (%s, %s, %s)"
    mycursor.execute(query, (item_name, price, available))
    mydb.commit()
    mycursor.close()
    mydb.close()
    return True