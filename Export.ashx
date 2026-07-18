<%@ WebHandler Language="C#" Class="ExportHandler" %>
using System;
using System.Web;
using System.Data.SqlClient;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;

public class ExportHandler : IHttpHandler {

    public void ProcessRequest (HttpContext context) {
        // ทดสอบการเรียกใช้งานเบื้องต้น
        // หากลองเข้าผ่าน Browser แล้วไม่ขึ้นข้อความนี้ แสดงว่าไม่ได้เรียกไฟล์นี้จริง
        // context.Response.Write("Handler is working!"); 
        
        if (context.Request.HttpMethod == "POST") {
            try {
                string jsonString = new StreamReader(context.Request.InputStream).ReadToEnd();
                var serializer = new JavaScriptSerializer();
                var data = serializer.Deserialize<Dictionary<string, object>>(jsonString);
                
                // ตรวจสอบข้อมูลเบื้องต้น
                if (data == null || !data.ContainsKey("db_server_ip")) {
                    throw new Exception("Invalid request data.");
                }

                string dbServer = data["db_server_ip"].ToString();
                string dbName = data["db_name"].ToString();
                string connString = string.Format("Server={0};Database={1};User Id=sa;Password=Hwkingp@ss;Connection Timeout=10;", dbServer, dbName);

                using (SqlConnection conn = new SqlConnection(connString)) {
                    conn.Open();

                    string action = data.ContainsKey("action") ? data["action"].ToString() : "export";

                    if (action == "test_connection") {
                        context.Response.StatusCode = 200;
                        context.Response.Write("Success");
                    } 
                    else {
                        string tableName = data["table"].ToString();
                        foreach (var item in (System.Collections.ArrayList)data["data"]) {
                            var row = (Dictionary<string, object>)item;
                            string sql = "INSERT INTO " + tableName + " (location, staff_name, product_code, barcode, qty, scan_date,export_date) VALUES (@loc, @staff, @code, @bar, @qty, @date, @export_date)";
                            SqlCommand cmd = new SqlCommand(sql, conn);
                            cmd.Parameters.AddWithValue("@loc", row["location"]);
                            cmd.Parameters.AddWithValue("@staff", row["staff"]);
                            cmd.Parameters.AddWithValue("@code", row["p_code"]);
                            cmd.Parameters.AddWithValue("@bar", row["barcode"]);
                            cmd.Parameters.AddWithValue("@qty", row["qty"]);
                            cmd.Parameters.AddWithValue("@date", row["date"]);
                            cmd.Parameters.AddWithValue("@export_date", row["export_date"]);
                            cmd.ExecuteNonQuery();
                        }
                        context.Response.StatusCode = 200;
                        context.Response.Write("Success");
                    }
                }
            } catch (Exception ex) {
                context.Response.StatusCode = 500;
                context.Response.Write("Error: " + ex.Message);
            }
        }
    }

    public bool IsReusable { 
        get { return false; } 
    }
}