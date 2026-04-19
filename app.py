import streamlit as st
import pandas as pd
import sqlite3
import json
from google import genai
from google.genai import types

# 1. ตั้งค่า API
if "gemini_api_key" not in st.secrets:
    st.error("กรุณาตั้งค่า 'gemini_api_key' ในไฟล์ secrets")
    st.stop()

gmn_client = genai.Client(api_key=st.secrets["gemini_api_key"])

# 2. Schema ข้อมูล
data_dict_text = """
trx_date, trx_no, member_code, branch_code, branch_region, branch_province, 
product_code, product_category, product_group, product_type, order_qty, 
unit_price, cost, item_discount, customer_discount, net_amount, cost_amount
"""

# 3. ฟังก์ชันดึงข้อมูลจาก CSV
def query_to_dataframe(sql_query):
    try:
        # ใช้ sep=None ให้ Pandas เดาตัวคั่นเองอัตโนมัติ
        df = pd.read_csv('test_transactions_2026.csv', sep=None, engine='python')
        conn = sqlite3.connect(':memory:')
        df.to_sql('transactions', conn, if_exists='replace', index=False)
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Database Error: {e}"

# 4. ฟังก์ชันเรียก Gemini (ใช้ model ที่มีอยู่จริง)
def generate_gemini_answer(prompt, is_json=False):
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

# 5. CORE LOGIC
def generate_summary_answer(user_question):
    script_prompt = f"""
    ตาราง transactions มี schema: {data_dict_text}
    คำถาม: {user_question}
    ให้ตอบเป็น JSON เท่านั้นในรูปแบบ {{"script": "SELECT ... FROM transactions ..."}}
    """
    
    sql_json_text = generate_gemini_answer(script_prompt, is_json=True)
    try:
        # ทำความสะอาด JSON กรณี AI ส่ง Markdown มาด้วย
        clean_json = sql_json_text.replace("```json", "").replace("```", "").strip()
        sql_script = json.loads(clean_json)['script']
    except:
        return f"ขออภัย ไม่สามารถสร้างคำสั่ง SQL ได้: {sql_json_text}"

    df_result = query_to_dataframe(sql_script)
    if isinstance(df_result, str): return df_result

    answer_prompt = f"คำถาม: {user_question}\nข้อมูล: {df_result.to_string()}\nสรุปคำตอบเป็นภาษาไทย"
    return generate_gemini_answer(answer_prompt, is_json=False)

# 6. UI
st.title('📊 Gemini Chat with Database')

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("พิมพ์คำถามที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner('กำลังหาคำตอบ...'):
            response = generate_summary_answer(prompt)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
