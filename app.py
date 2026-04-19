import streamlit as st
import pandas as pd
import sqlite3
import json
from google import genai
from google.genai import types

if "gemini_api_key" not in st.secrets:
    st.error("กรุณาตั้งค่า 'gemini_api_key' ในไฟล์ secrets")
    st.stop()

gmn_client = genai.Client(api_key=st.secrets["gemini_api_key"])

def process_user_query(user_question):
    # 1. ให้ AI สร้าง SQL
    prompt = f"""
    ตาราง transactions มี Schema ดังนี้:
    trx_date, trx_no, member_code, branch_code, branch_region, branch_province, product_code, product_category, product_group, product_type, order_qty, unit_price, cost, item_discount, customer_discount, net_amount, cost_amount
    
    คำถาม: {user_question}
    ให้ตอบเป็น JSON เท่านั้นในรูปแบบ {{"script": "SELECT ... FROM transactions WHERE ..."}}
    """
    
    try:
        response = gmn_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        sql_data = json.loads(response.text)
        sql_query = sql_data['script']
    except Exception as e:
        return f"AI ปฏิเสธการสร้าง SQL หรือ JSON ผิดพลาด: {e} \n\nสิ่งที่ AI ส่งมาคือ: {response.text if 'response' in locals() else 'ไม่มีการตอบกลับ'}"

    # 2. Query
    try:
        df = pd.read_csv('test_transactions_2026.csv')
        conn = sqlite3.connect(':memory:')
        df.to_sql('transactions', conn, index=False)
        result = pd.read_sql_query(sql_query, conn)
        conn.close()
    except Exception as e:
        return f"SQL Error: {e}"

    # 3. สรุปคำตอบ
    return f"จากข้อมูล SQL ที่รัน: \n\n{result.to_string()}"

# UI
st.title('📊 Gemini Database Chatbot')
if prompt := st.chat_input("ถามคำถาม..."):
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner('กำลังวิเคราะห์...'):
            ans = process_user_query(prompt)
            st.markdown(ans)
