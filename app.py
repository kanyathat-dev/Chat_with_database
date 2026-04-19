import streamlit as st
import pandas as pd
import sqlite3
import json
from google import genai
from google.genai import types

# 1. ตั้งค่า API Key จาก Secrets
if "gemini_api_key" not in st.secrets:
    st.error("กรุณาตั้งค่า 'gemini_api_key' ในไฟล์ secrets ของ Streamlit")
    st.stop()

gmn_client = genai.Client(api_key=st.secrets["gemini_api_key"])

# 2. Schema ข้อมูลสำหรับบอก AI
data_dict_text = """
- trx_date: วันที่ทำธุรกรรม
- trx_no: หมายเลขธุรกรรม
- member_code: รหัสสมาชิก
- branch_code: รหัสสาขา
- branch_region: ภูมิภาค
- branch_province: จังหวัด
- product_code: รหัสสินค้า
- product_category: หมวดหมู่สินค้า
- order_qty: จำนวน
- unit_price: ราคาต่อหน่วย
- net_amount: ยอดขายสุทธิ
"""

# 3. ฟังก์ชันอ่าน CSV และ Query
def query_to_dataframe(sql_query):
    try:
        # อ่าน CSV โดยให้ Pandas ตรวจหาตัวคั่น (sep) เองอัตโนมัติ
        df = pd.read_csv('test_transactions_2026.csv', sep=None, engine='python')
        
        conn = sqlite3.connect(':memory:')
        df.to_sql('transactions', conn, if_exists='replace', index=False)
        
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Database Error: {e}"

# 4. ฟังก์ชันเรียก AI
def ask_gemini(prompt, is_json=False):
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if is_json else "text/plain"
        )
        response = gmn_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
            config=config
        )
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# 5. Core Logic
def process_user_query(user_question):
    prompt = f"""
    ตาราง transactions มี Schema ดังนี้: {data_dict_text}
    คำถาม: {user_question}
    ให้ตอบเป็น JSON เท่านั้นในรูปแบบ {{"script": "SELECT ... FROM transactions ..."}}
    """
    
    response_text = ask_gemini(prompt, is_json=True)
    try:
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        sql_query = json.loads(clean_json)['script']
    except:
        return f"AI ไม่สามารถสร้าง SQL ได้: {response_text}"

    df = query_to_dataframe(sql_query)
    if isinstance(df, str): return df

    return f"ผลลัพธ์ข้อมูล:\n\n{df.to_string()}"

# 6. UI
st.title('📊 Gemini Database Chatbot')

if "messages" not in st.session_state: st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("ถามคำถามเกี่ยวกับยอดขาย..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner('กำลังวิเคราะห์...'):
            ans = process_user_query(prompt)
            st.markdown(ans)
    st.session_state.messages.append({"role": "assistant", "content": ans})
