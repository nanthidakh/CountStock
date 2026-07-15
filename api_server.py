# pip install flask pyodbc
from flask import Flask, jsonify, request
import pyodbc

app = Flask(__name__)
# แก้ไข Connection String ของคุณให้ถูกต้อง
CONN_STR = "DRIVER={SQL Server};SERVER=DBSQL;DATABASE=HWKING_BW;UID=sa;PWD=Hwkingp@ssw0rd;Timeout=10"

@app.route('/get_products', methods=['GET'])
def get_products():
    count_month = request.args.get('month', '08/2026')
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        query = """SELECT b.BARCODE, a.code, a.NAME, f.SNAME, ? as count_month, c.LNAME 
                   FROM CSPRODUCT a 
                   LEFT JOIN csbarcode b ON a.code=b.PRODUCTCODE
                   LEFT JOIN CSPDPRICE d ON b.PRODUCTCODE=d.PRODUCTCODE AND d.UNITID=b.UNITID AND d.TAXTYPE=1 AND d.CURRENCY=1
                   LEFT JOIN CSUNIT c ON a.STOCKUNIT=c.ID
                   LEFT JOIN CSDIM5 f ON a.DIM5=f.ID
                   WHERE d.UNITPRICE1 IS NOT NULL AND a.SYSDOCFLAG=0 AND a.USEFLAG=0"""
        cursor.execute(query, (count_month,))
        rows = [list(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/export_data', methods=['POST'])
def export_data():
    try:
        data = request.json
        table = data['table']
        rows = data['data']
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        for r in rows:
            cursor.execute(f"INSERT INTO {table} (location, staff_name, product_code, barcode, qty, scan_date) VALUES (?,?,?,?,?,?)",
                           (r['location'], r['staff'], r['p_code'], r['barcode'], r['qty'], r['date']))
        conn.commit()
        conn.close()
        return "OK", 200
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)