# ไฟล์: database.py
import sqlite3
import os
import requests
import shutil
from kivy.app import App
from kivy.utils import platform
from datetime import datetime

DB_NAME = "inventory.db"
CUR_DIR = os.path.dirname(__file__) if '__file__' in locals() else os.getcwd()

def get_db_path():
    if platform == 'android':
        # 1. ดึง Path ของโฟลเดอร์ที่แอปเขียนไฟล์ได้ใน Android
        user_data_dir = App.get_running_app().user_data_dir
        dest_path = os.path.join(user_data_dir, DB_NAME)
        
        # 2. ถ้ายังไม่มีไฟล์ในเครื่อง ให้คัดลอกจาก APK มาวาง
        if not os.path.exists(dest_path):
            source_path = os.path.join(CUR_DIR, DB_NAME)
            if os.path.exists(source_path):
                shutil.copyfile(source_path, dest_path)
            else:
                # กรณีหาไฟล์ใน APK ไม่เจอ (เพื่อความปลอดภัย)
                print(f"Error: Not found source DB at {source_path}")
        
        return dest_path
    else:
        # บน PC ให้ใช้ Path เดิม
        return os.path.join(CUR_DIR, DB_NAME)

def get_connection():
    conn = sqlite3.connect(get_db_path(), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_connection() 
    cursor = conn.cursor()
    
    # 1. ตารางเก็บค่า Configuration
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS db_config (
            branch_name TEXT, 
            iis_server_ip TEXT, 
            db_server_ip TEXT, 
            db_name TEXT, 
            db_user TEXT, 
            db_password TEXT, 
            count_month TEXT
        )
    """)
    
    # 2. ตารางเก็บข้อมูลสินค้าหลัก
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS main_products (
            barcode TEXT PRIMARY KEY, product_code TEXT, product_name TEXT, 
            Dept TEXT, CountMonth TEXT, unit TEXT
        )
    """)
    
    # 3. ตารางเก็บผลการสแกน
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Countstock_scan_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT, staff_name TEXT, product_code TEXT, 
            barcode TEXT, qty INTEGER DEFAULT 1, 
            scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
            scan_date TEXT, export_date TEXT, is_exported INTEGER DEFAULT 0
        )
    """)
    
    # Commit ครั้งเดียวตอนท้าย
    conn.commit()
    # ปิดครั้งเดียวตอนท้าย
    conn.close()
    print("✓ เริ่มต้นระบบฐานข้อมูล SQLite เรียบร้อยแล้ว")

def save_config(branch, ip, db, user, pwd, count_month, iis_ip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM db_config")
    cursor.execute("""
        INSERT INTO db_config (branch_name, iis_server_ip, db_server_ip, db_name, db_user, db_password, count_month)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (branch, iis_ip, ip, db, user, pwd, count_month))
    conn.commit()
    conn.close()

def get_config():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT branch_name, db_server_ip, db_name, db_user, db_password, count_month, iis_server_ip FROM db_config LIMIT 1")
    config = cursor.fetchone()
    conn.close()
    return config

def query_product(barcode):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT product_code, product_name, unit FROM main_products WHERE barcode = ?", (barcode,))
    product = cursor.fetchone()
    conn.close()
    return product
def query_product_by_code(product_code):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT product_code,
               product_name,
               unit
        FROM main_products
        WHERE TRIM(product_code)=?
    """, (product_code,))

    row = cursor.fetchone()

    conn.close()

    return row

def get_existing_scan(location, barcode):
    
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               qty
        FROM Countstock_scan_data
        WHERE location=?
        AND barcode=?
    """, (location, barcode))

    row = cursor.fetchone()

    conn.close()

    return row


def update_scan_qty(scan_id, qty):
    
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Countstock_scan_data
        SET qty=?,
            scan_date=?
        WHERE id=?
    """,
    (
        qty,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        scan_id
    ))

    conn.commit()

    conn.close()
    
def save_edit_qty(location, barcode, qty):
    
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE Countstock_scan_data
        SET qty=?,
            scan_date=?
        WHERE location=?
        AND barcode=?
    """,
    (
        qty,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        location,
        barcode
    ))

    conn.commit()

    conn.close()    
    
def get_export_rows():
    
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            location,
            staff_name,
            product_code,
            barcode,
            qty,
            scan_date
        FROM Countstock_scan_data
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows

def clear_scan_table():
    
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("DELETE FROM Countstock_scan_data")

    conn.commit()

    conn.close()  
def insert_scan_result_to_db(location, staff, product_code, barcode, qty):
    """บันทึกข้อมูลการนับสต็อกใหม่ลงตาราง Countstock_scan_data"""
    conn = get_connection()
    cursor = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    query = """
        INSERT INTO Countstock_scan_data (location, staff_name, product_code, barcode, qty, scan_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    cursor.execute(query, (location, staff, product_code, barcode, qty, current_date))
    conn.commit()
    conn.close()

def get_recent_scans_from_table(limit=5):
    """ดึงรายการประวัติที่พนักงานเพิ่งสแกนล่าสุดมาโชว์บนหน้าจอ"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT s.barcode, p.product_name, s.qty, s.scan_date, s.location
        FROM Countstock_scan_data s
        LEFT JOIN main_products p ON s.product_code = p.product_code
        ORDER BY s.id DESC LIMIT ?
    """
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def import_products_from_mssql():
    """ฟังก์ชันหลักสำหรับกดปุ่มนำเข้าข้อมูล (ปรับปรุงรองรับข้อมูลจำนวนมาก)"""
    try:
        config = get_config()
        if not config:
            return "❌ กรุณาตั้งค่า Config ก่อน"
        
        branch, db_server_ip, db_name, user, pwd, count_month, iis_ip = config
        
        payload = {
            "db_server_ip": db_server_ip,
            "db_name": db_name,
            "month": count_month or '08/2026'
        }
        
        api_url = f"http://{iis_ip}/API_HWK_CountStock_Data/get_products.ashx"
        
        # ปรับ timeout เป็น 300 วินาที เพื่อรอข้อมูลก้อนใหญ่
        response = requests.post(api_url, json=payload, timeout=300)
        
        if response.status_code != 200:
            return f"❌ API Error: {response.status_code} - {response.text}"
        
        data = response.json()
        
        if not data:
            return 0
        
        total_items = len(data)
        
        # 3. บันทึกลง SQLite ด้วยการแบ่ง Batch
        lite_conn = get_connection()
        cursor = lite_conn.cursor()
        
        try:
            cursor.execute("DELETE FROM main_products")
            
            # แบ่งบันทึกทีละ 5,000 รายการ เพื่อไม่ให้กิน Memory และไม่ให้ UI ค้างนาน
            batch_size = 5000
            for i in range(0, total_items, batch_size):
                batch = data[i : i + batch_size]
                cursor.executemany("""
                    INSERT INTO main_products (barcode, product_code, product_name, Dept, CountMonth, unit)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
                # Commit เป็นระยะๆ ป้องกัน Transaction Log เต็ม
                lite_conn.commit()
                
            return total_items 
            
        except Exception as e:
            lite_conn.rollback()
            raise e
        finally:
            lite_conn.close()
        
    except requests.exceptions.Timeout:
        return "❌ Error: การเชื่อมต่อหมดเวลา (Timeout) โปรดตรวจสอบความเร็วเน็ต"
    except Exception as e:
        return f"❌ Error: {str(e)}"