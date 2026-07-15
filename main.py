# ไฟล์: main.py
import os
import sys
import sqlite3
import requests  # ใช้แทน pyodbc สำหรับการสื่อสารผ่าน Network
import threading
from kivy.clock import Clock
from datetime import datetime
from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivy.clock import Clock
from kivy.utils import platform

# รองรับระบบเสียงบน Android
if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
else:
    import winsound

Window.keyboard_anim_delay = 0

from database import (
    init_db, save_config, get_config, import_products_from_mssql,
    query_product, insert_scan_result_to_db, get_recent_scans_from_table
)

CUR_DIR = os.path.dirname(__file__) if __file__ in locals() else os.getcwd()

class MainMenuScreen(MDScreen):
    def exit_app(self):
        sys.exit(0)

class ConfigScreen(MDScreen):
    def go_back(self):
        self.manager.current = 'menu_screen'

    def load_current_config(self):
        config = get_config()
        if config:
            self.ids.txt_branch.text = str(config[0]) if config[0] else ""
            self.ids.txt_db_server_ip.text = str(config[1]) if config[1] else ""
            self.ids.txt_db.text = str(config[2]) if config[2] else ""
            self.ids.txt_user.text = str(config[3]) if config[3] else ""
            self.ids.txt_pwd.text = str(config[4]) if config[4] else ""
            self.ids.txt_month.text = str(config[5]) if len(config) > 5 and config[5] else "08/2026"
            self.ids.txt_iis_ip.text = str(config[6]) if config[6] else ""

    def save_data(self):
        branch = self.ids.txt_branch.text.strip()
        ip = self.ids.txt_db_server_ip.text.strip()
        db = self.ids.txt_db.text.strip()
        user = self.ids.txt_user.text.strip()
        pwd = self.ids.txt_pwd.text.strip()
        month = self.ids.txt_month.text.strip()
        iis_ip = self.ids.txt_iis_ip.text.strip()
        if not all([branch, ip, db, user, pwd, month]):
            MDApp.get_running_app().show_alert("⚠️ ข้อมูลไม่ครบ", "กรุณากรอกข้อมูลให้ครบทุกช่อง")
            return

        try:
            save_config(branch, ip, db, user, pwd, month,iis_ip)
            MDApp.get_running_app().show_alert("✓ สำเร็จ", "บันทึกการตั้งค่าเรียบร้อยแล้ว")
            self.go_back()
        except Exception as e:
            MDApp.get_running_app().show_alert("❌ เกิดข้อผิดพลาด", f"{e}")
    def test_all_connections(self):
        iis_ip = self.ids.txt_iis_ip.text.strip()
        db_ip = self.ids.txt_db_server_ip.text.strip()
        db_name = self.ids.txt_db.text.strip()

        # 1. ทดสอบ IIS ก่อน
        try:
            # ส่ง Ping ง่ายๆ ไปที่ไฟล์ที่ไม่มีอยู่จริงหรือไฟล์เช็คสถานะบน IIS
            # หรือแค่เช็คว่า IP นี้เปิด Port 80 อยู่ไหม
            response = requests.get(f"http://{iis_ip}/", timeout=5)
            print("IIS เชื่อมต่อสำเร็จ")
        except Exception as e:
            MDApp.get_running_app().show_alert("❌ IIS ล้มเหลว", f"ไม่สามารถติดต่อ IIS ได้: {e}")
            return

        # 2. ทดสอบ DB ผ่าน IIS (ส่ง JSON ไปถามสถานะ)
        try:
            payload = {
                'action': 'test_connection',
                'db_server_ip': db_ip,
                'db_name': db_name
            }
            response = requests.post(f"http://{iis_ip}/API_HWK_CountStock_Data/Export.ashx", json=payload, timeout=10)
            
            if response.status_code == 200:
                MDApp.get_running_app().show_alert("✅ สำเร็จ", "การเชื่อมต่อ IIS และ Database ปกติดี")
            else:
                MDApp.get_running_app().show_alert("❌ DB ล้มเหลว", "IIS ติดต่อได้ แต่เข้า DB ไม่ได้")
        except Exception as e:
            MDApp.get_running_app().show_alert("❌ Error", f"การเชื่อมต่อผิดพลาด: {e}")


class ImportScreen(MDScreen):
    
    def go_back(self):
        self.manager.current = 'menu_screen'

    def start_import(self):
        # 1. ปิดปุ่ม
        self.ids.btn_import.disabled = True
        
        # 2. เริ่ม Thread
        threading.Thread(target=self.run_import_thread, daemon=True).start()

    def run_import_thread(self):
        # ทำงานหนักที่นี่
        result = import_products_from_mssql()
        
        # ส่งผลลัพธ์กลับไปที่ Main Thread เพื่ออัปเดต UI
        Clock.schedule_once(lambda dt: self.show_import_result(result))

    def show_import_result(self, result):
        # 3. เปิดปุ่มคืน
        self.ids.btn_import.disabled = False
        
        # 4. แสดงผลลัพธ์
        if isinstance(result, int):
            if result > 0:
                MDApp.get_running_app().show_alert("✅ สำเร็จ", f"ซิงค์และแทนที่สินค้าแล้ว {result:,} รายการ")
            else:
                MDApp.get_running_app().show_alert("⚠️ แจ้งเตือน", "ไม่พบข้อมูลสินค้า")
        else:
            MDApp.get_running_app().show_alert("❌ ล้มเหลว", str(result))
   

class StockCountScreen(MDScreen):
    edit_dialog = None
    edit_text_field = None

    def go_back(self):
        self.stop_android_scanner()
        self.manager.current = 'menu_screen'
        
    def focus_barcode(self):
        self.update_recent_list()  
        self.start_android_scanner()

    def start_android_scanner(self):
        """เริ่มเปิดระบบดักจับ Intent บาร์โค้ดของเครื่อง CipherLab"""
        if platform == 'android':
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                IntentFilter = autoclass('android.content.IntentFilter')
                
                # สร้าง BroadcastReceiver ใน Java ผ่าน jnius
                self.receiver = create_android_receiver(self.on_android_barcode_received)
                
                # ลงทะเบียน Event Listener สำหรับรับค่า Intent
                current_activity = PythonActivity.mActivity
                intent_filter = IntentFilter("com.cipherlab.barcode.queue")
                current_activity.registerReceiver(self.receiver, intent_filter)
                print("✓ Android Barcode Receiver Registered")
            except Exception as e:
                print(f"Android Scanner Error: {e}")

    def stop_android_scanner(self):
        """ปิดระบบดักจับเมื่อออกจากหน้าสแกน"""
        if platform == 'android' and hasattr(self, 'receiver'):
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                current_activity = PythonActivity.mActivity
                current_activity.unregisterReceiver(self.receiver)
                del self.receiver
            except Exception as e:
                print(f"Stop Scanner Error: {e}")

    def play_sound(self, success=True):
        """ระบบเล่นเสียงแจ้งเตือน"""
        if platform == 'android':
            try:
                ToneGenerator = autoclass('android.media.ToneGenerator')
                AudioManager = autoclass('android.media.AudioManager')
                # 100 = ความดังสูงสุด
                tone_gen = ToneGenerator(AudioManager.STREAM_MUSIC, 100)
                if success:
                    # เสียงติ๊ดสั้น (ยิงสำเร็จ)
                    tone_gen.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
                else:
                    # เสียงตื๊ดยาวเตือน (ยิงผิดพลาด/ไม่พบสินค้า)
                    tone_gen.startTone(ToneGenerator.TONE_SUP_ERROR, 400)
            except Exception as e:
                print(f"Sound Error: {e}")
        else:
            # เล่นเสียงบี๊บบน Windows สำหรับทดสอบพัฒนา
            if success:
                winsound.Beep(2000, 150)
            else:
                winsound.Beep(600, 400)

    def on_android_barcode_received(self, barcode_str):
        """รับค่าบาร์โค้ดจากหัวอ่าน CipherLab ส่งมาทำงานต่อ"""
        if barcode_str:
            self.process_barcode(barcode_str.strip())

    def on_windows_keyboard_validate(self):
        """รับค่าจากแป้นพิมพ์ (สำหรับเปิดทดสอบบนคอมพิวเตอร์)"""
        barcode_input = self.ids.txt_barcode.text.strip()
        if barcode_input:
            self.process_barcode(barcode_input)
        self.ids.txt_barcode.text = ""
    def on_barcode_scan(self):
        """รองรับการเรียกใช้งานจากไฟล์ main_design.kv เมื่อกด Enter"""
        self.on_windows_keyboard_validate()
    def process_barcode(self, barcode_input):
        """ฟังก์ชันหลักในการตรวจสอบและบันทึกบาร์โค้ด"""
        location = self.ids.txt_location.text.strip()
        staff = self.ids.txt_staff.text.strip()
        
        if not location or not staff:
            self.play_sound(success=False)
            MDApp.get_running_app().show_alert("⚠️ คำเตือน", "กรุณาระบุตำแหน่งและผู้ตรวจนับก่อนทำการสแกน")
            return
            
        product = query_product(barcode_input)
        if not product:
            self.play_sound(success=False) # เสียงยิงผิดพลาด
            MDApp.get_running_app().show_alert("❌ ไม่พบข้อมูลสินค้า", f"ไม่พบบาร์โค้ด [{barcode_input}] ในระบบคลังสินค้า")
            return

        product_code, product_name, unit_name = product
        self.ids.lbl_product_code.text = f"รหัส: {product_code}"
        self.ids.lbl_product_name.text = f"ชื่อสินค้า: {product_name}"
        self.ids.lbl_unit.text = f"หน่วย: {unit_name}"

        try:
            conn = sqlite3.connect('inventory.db') 
            cursor = conn.cursor()
            cursor.execute("SELECT id, qty FROM Countstock_scan_data WHERE location=? AND barcode=?", (location, barcode_input))
            row = cursor.fetchone()
            
            if row:
                scan_id, current_qty = row
                new_qty = current_qty + 1
                cursor.execute("UPDATE Countstock_scan_data SET qty=?, scan_date=? WHERE id=?", (new_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), scan_id))
                conn.commit()
                self.ids.lbl_product_name.text = f"✓ [ยิงซ้ำ +1] รวม: {new_qty} {unit_name}"
            else:
                insert_scan_result_to_db(location, staff, product_code, barcode_input, 1)
                
            conn.close()
            self.play_sound(success=True) # เสียงยิงสำเร็จ
        except Exception as e:
            print(f"Error Saving Scan: {e}")

        self.update_recent_list()

    def update_recent_list(self):
        self.ids.list_recent_scans.clear_widgets()
        from kivy.factory import Factory
        
        recent_data = get_recent_scans_from_table(limit=5)
        for row in recent_data:
            b_code = row[0]
            p_name = row[1] if row[1] else "ไม่ทราบชื่อสินค้า"
            quantity = row[2]
            s_date = row[3] if row[3] else "-"
            
            item_text = f"{p_name} (จำนวน: {quantity}) ✏️"
            item_secondary = f"บาร์โค้ด: {b_code} | เวลาสแกน: {s_date}"
            
            list_item = Factory.ThaiTwoLineListItem(text=item_text, secondary_text=item_secondary)
            list_item.bind(on_release=lambda x, b=b_code, q=quantity, l=row[4], n=p_name: self.open_edit_dialog(b, q, l, n))
            self.ids.list_recent_scans.add_widget(list_item)

    def open_edit_dialog(self, barcode, current_qty, location, product_name):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel

        dialog_layout = MDBoxLayout(orientation="vertical", spacing="12dp", size_hint_y=None, height="140dp")
        lbl_title = MDLabel(text=f"แก้ไขจำนวน: {product_name}", font_name="ThaiFont", font_style="Subtitle1", size_hint_y=None, height="40dp")
        self.edit_text_field = MDTextField(text=str(current_qty), input_filter="int", hint_text="Edit QTY", font_name="ThaiFont", size_hint_y=None, height="50dp")
        dialog_layout.add_widget(lbl_title)
        dialog_layout.add_widget(self.edit_text_field)
        
        self.current_edit_data = {"barcode": barcode, "location": location}
        btn_cancel = MDFlatButton(text="ยกเลิก", font_name="ThaiFont")
        btn_save = MDRaisedButton(text="บันทึก", font_name="ThaiFont")
        btn_cancel.bind(on_release=lambda x: self.edit_dialog.dismiss())
        btn_save.bind(on_release=lambda x: self.save_edited_qty())

        self.edit_dialog = MDDialog(type="custom", content_cls=dialog_layout, buttons=[btn_cancel, btn_save])
        self.edit_dialog.open()

    def save_edited_qty(self):
        new_qty_text = self.edit_text_field.text.strip()
        if not new_qty_text: return
            
        try:
            new_qty = int(new_qty_text)
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE Countstock_scan_data SET qty=?, scan_date=? WHERE location=? AND barcode=?", 
                           (new_qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.current_edit_data["location"], self.current_edit_data["barcode"]))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error Editing Qty: {e}")
            
        self.edit_dialog.dismiss()
        self.update_recent_list()

class ExportScreen(MDScreen):
    confirm_clear_dialog = None

    def go_back(self):
        self.manager.current = 'menu_screen'

    def export_data(self, target_server_table):
        config = get_config()
        if not config:
            MDApp.get_running_app().show_alert("❌ ข้อผิดพลาด", "ไม่พบข้อมูลการตั้งค่า")
            return
            
        iis_ip = config[6] # ดึงเฉพาะ IP ของ Server
        db_name = config[2]    # ชื่อ Database ที่ตั้งค่าไว้ในหน้าจอ Config
        
        # ดึงข้อมูลจาก SQLite ในเครื่อง
        lite_conn = sqlite3.connect('inventory.db')
        lite_cursor = lite_conn.cursor()
        lite_cursor.execute("SELECT location, staff_name, product_code, barcode, qty, scan_date FROM Countstock_scan_data")
        rows = lite_cursor.fetchall()
        lite_conn.close()
        
        if not rows:
            MDApp.get_running_app().show_alert("⚠️ ไม่มีข้อมูล", "ไม่พบรายการค้างส่ง")
            return

        # แปลงข้อมูลเป็น List of Dictionaries เพื่อส่งผ่าน JSON
        current_time = datetime.now().strftime('%Y/%m/%d')
        data_to_send = [
            {'location': r[0], 'staff': r[1], 'p_code': r[2], 'barcode': r[3], 'qty': r[4], 'date': r[5],'export_date': current_time} 
            for r in rows
        ]
       
        
        payload = {
        'table': target_server_table, 
        'db_server_ip': config[1], # db_server_ip ที่ดึงมาจาก SQLite
        'db_name': config[2], 
        'data': data_to_send
    }
        # ส่งผ่าน API ไปที่ IIS ที่ไฟล์ Export.ashx
        try:
            # ใช้ iis_ip ที่ดึงมาจากฐานข้อมูล
            url = f"http://{iis_ip}/API_HWK_CountStock_Data/Export.ashx" 
            
            response = requests.post(url, json=payload, timeout=300)
            
            if response.status_code == 200:
                self.show_export_success_dialog(target_server_table, len(rows))
            else:
                 # เพิ่มการตรวจจับข้อความ Error ที่เราส่งมาจาก C#
                error_msg = response.text
                if "SQL_ERROR:" in error_msg:
                    # ตัดเอาเฉพาะข้อความหลัง SQL_ERROR: มาโชว์
                    clean_msg = error_msg.split("SQL_ERROR:")[1].strip()
                    MDApp.get_running_app().show_alert("❌ Server Error", clean_msg)
                else:
                    # ถ้าไม่ใช่ Error จาก SQL ให้โชว์ Error ปกติ
                    MDApp.get_running_app().show_alert("❌ ส่งออกล้มเหลว", "เกิดข้อผิดพลาดที่ Server")
        except Exception as e:
            MDApp.get_running_app().show_alert("❌ เชื่อมต่อไม่ได้", f"ตรวจสอบ IP Server ({iis_ip}): {e}")
            
    def show_export_success_dialog(self, table_name, record_count):
        btn_no = MDFlatButton(text="เก็บข้อมูลไว้ก่อน", font_name="ThaiFont")
        btn_yes = MDRaisedButton(text="ยืนยัน ลบข้อมูลในเครื่อง", font_name="ThaiFont", md_bg_color=[0.8, 0.2, 0.2, 1])
        btn_no.bind(on_release=lambda x: self.confirm_clear_dialog.dismiss())
        btn_yes.bind(on_release=lambda x: self.clear_pda_table())

        self.confirm_clear_dialog = MDDialog(
            title="✅ ส่งออกข้อมูลครบถ้วนสมบูรณ์",
            text=f"ส่งข้อมูลไปยังตาราง {table_name} บนเซิร์ฟเวอร์ครบทั้ง {record_count:,} รายการแล้ว\n\nต้องการลบข้อมูลชุดนี้ออกจากเครื่อง PDA หรือไม่?",
            buttons=[btn_no, btn_yes]
        )
        self.confirm_clear_dialog.open()

    def clear_pda_table(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Countstock_scan_data")
            conn.commit()
            conn.close()
            self.confirm_clear_dialog.dismiss()
            MDApp.get_running_app().show_alert("✓ สำเร็จ", "ล้างข้อมูลในเครื่อง PDA เรียบร้อยแล้ว")
        except Exception as e:
            print(f"Error Clearing Table: {e}")

# --- โครงสร้างเชื่อมต่อ Java Class สำหรับการทำงานแบบ Background Intent Receiver ---
def create_android_receiver(callback):
    if platform != 'android':
        return None
    
    class AndroidBarcodeReceiver(PythonJavaClass):
        __javainterfaces__ = ['android/content/BroadcastReceiver']
        __javacontext__ = 'app'

        def __init__(self, cb):
            super(AndroidBarcodeReceiver, self).__init__()
            self.cb = cb

        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, context, intent):
            # ดึงข้อมูลจาก String Extra ที่กำหนดใน ReaderConfig
            barcode_data = intent.getStringExtra("com.cipherlab.barcode.queue_string")
            if barcode_data:
                Clock.schedule_once(lambda dt: self.cb(str(barcode_data)), 0)

    return AndroidBarcodeReceiver(callback)

class InventoryApp(MDApp):
    dialog = None

    def build(self):
        init_db() 
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Orange"
        self.theme_cls.material_design_icons = "font"
        font_path = os.path.join(CUR_DIR, "fonts", "Kanit-Regular.ttf")
        if not os.path.exists(font_path):
            font_path = os.path.join(CUR_DIR, "Kanit-Regular.ttf")

        try:
            LabelBase.register(name="ThaiFont", fn_regular=font_path)
            for style in list(self.theme_cls.font_styles.keys()):
                if style not in ["Icons"]:
                    self.theme_cls.font_styles[style] = [
                        "ThaiFont",
                        self.theme_cls.font_styles[style][1],
                        self.theme_cls.font_styles[style][2],
                        self.theme_cls.font_styles[style][3]
                    ]
        except Exception as e:
            print(f"Font Error: {e}")

        kv_path = os.path.join(CUR_DIR, "main_design.kv")
        return Builder.load_file(kv_path)

    def show_alert(self, title, text):
        if self.dialog:
            self.dialog.dismiss()

        self.dialog = MDDialog(
            title=title,
            text=text,
            buttons=[MDRaisedButton(text="ตกลง", font_name="ThaiFont", on_release=lambda x: self.dialog.dismiss())]
        )
        self.dialog.open()

if __name__ == "__main__":
    Window.size = (380, 680)
    InventoryApp().run()