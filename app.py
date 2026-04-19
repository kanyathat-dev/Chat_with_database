import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from google import genai
from google.genai import types

# 1. การตั้งค่า API (ต้องตั้งค่าใน Streamlit Cloud > Secrets)
if "gemini_api_key" not in st.secrets:
    st.error("กรุณาตั้งค่า 'gemini_api_key' ในไฟล์ secrets ของ Streamlit")
    st.stop()

gmn_client = genai.Client(api_key=st.secrets["gemini_api_key"])

# 2. การกำหนดที่อยู่ไฟล์ Database ให้แม่นยำ
# ใช้ os.path เพื่อระบุตำแหน่งไฟล์ให้ชัดเจนว่าอยู่ที่เดียวกับ app.py
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, 'test_database.db')

data_table = 'transactions'
data_dict_text = """
- trx_date: วันที่ทำธุรกรรม
- trx_no: หมายเลขธุรกรรม
- member_code: รหัสสมาชิกของลูกค้า
- branch_code: รหัสสาขา
- branch_region: ภูมิภาคที่สาขาตั้งอยู่
- branch_province: จังหวัดที่สาขาตั้งอยู่
- product_code: รหัสสินค้า
- product_category: หมวดหมู่หลักของสินค้า
- product_group: กลุ่มของสินค้า
- product_type: ประเภทของสินค้า
- order_qty: จำนวนชิ้น/หน่วย ที่ลูกค้าสั่งซื้อ
- unit_price: ราคาขายของสินค้าต่อ 1 หน่วย
- cost: ต้นทุนของสินค้าต่อ 1 หน่วย
- item_discount: ส่วนลดเฉพาะรายการสินค้านั้นๆ
- customer_discount: ส่วนลดจากสิทธิของลูกค้า
- net_amount: ยอดขายสุทธิของรายการนั้น
- cost_amount: ต้นทุนรวมของรายการนั้น
"""

# 3. HELPER FUNCTIONS
def query_to_dataframe(sql_query):
    # ตรวจสอบว่าไฟล์มีอยู่จริงไหมก่อนเชื่อมต่อ (เพื่อป้องกัน Error)
    if not os.path.exists(db_path):
        return f"Database Error: ไม่พบไฟล์ฐานข้อมูลที่ {db_path}. ไฟล์ที่มีในโฟลเดอร์คือ {os.listdir(current_dir)}"
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return df
    except Exception as e:
        return f"Database Error: {e}"

def ask_gemini(prompt, is_json=False):
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if is_json else "text/plain"
        )
        response = gmn_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# 4. CORE LOGIC
def process_user_query(user_question):
    script_prompt = f"""
    ### Goal: แปลงคำถามภาษาธรรมชาติให้เป็น SQL สำหรับตาราง {data_table}
    ### Schema: {data_dict_text}
    ### Input: {user_question}
    ### Output: ตอบกลับเป็น JSON เท่านั้นในรูปแบบ {{"script": "SELECT ..."}}
    """
    
    sql_json = ask_gemini(script_prompt, is_json=True)
    try:
        # ตัดส่วนที่เป็น markdown code block ออกถ้ามี
        clean_json = sql_json.replace("```json", "").replace("```", "").strip()
        sql_query = json.loads(clean_json)['script']
    except:
        return f"ขออภัย ผมไม่สามารถสร้างคำสั่ง SQL สำหรับคำถามนี้ได้ (Debug: {sql_json})"

    df = query_to_dataframe(sql_query)
    if isinstance(df, str): return df

    answer_prompt = f"""
    ### Context: คำถามคือ '{user_question}'
    ### ข้อมูลที่ได้: {df.to_string()}
    ### Task: สรุปคำตอบจากข้อมูลนี้ให้เป็นภาษาไทยแบบเป็นกันเอง
    """
    return ask_gemini(answer_prompt)

# 5. USER INTERFACE
st.title('📊 Gemini Database Chatbot')

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("ถามคำถามเกี่ยวกับยอดขายได้ที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner('กำลังคิด...'):
            response = process_user_query(prompt)
            st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
