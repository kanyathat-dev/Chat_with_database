import streamlit as st
import pandas as pd
import sqlite3
import json
from google import genai
from google.genai import types

# 1. การตั้งค่า API (ต้องตั้งค่าใน Streamlit Cloud > Settings > Secrets)
if "gemini_api_key" not in st.secrets:
    st.error("กรุณาตั้งค่า 'gemini_api_key' ในไฟล์ secrets ของ Streamlit")
    st.stop()

gmn_client = genai.Client(api_key=st.secrets["gemini_api_key"])

# 2. Schema ข้อมูลสำหรับอ้างอิง AI
data_dict_text = """
- trx_date, trx_no, member_code, branch_code, branch_region, branch_province, 
- product_code, product_category, product_group, product_type, 
- order_qty, unit_price, cost, item_discount, customer_discount, net_amount, cost_amount
"""

# 3. ฟังก์ชันดึงข้อมูลจาก CSV (แปลงเป็น SQL ให้ AI ใช้งาน)
def query_to_dataframe(sql_query):
    try:
        # อ่านไฟล์ CSV โดยให้ระบบตรวจหาตัวคั่น (sep) อัตโนมัติ
        df = pd.read_csv('test_transactions_2026.csv', sep=None, engine='python')
        
        # สร้าง SQL Database ในหน่วยความจำเพื่อรองรับคำสั่ง SQL
        conn = sqlite3.connect(':memory:')
        df.to_sql('transactions', conn, if_exists='replace', index=False)
        
        # รัน Query
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Database Error: {e}"

# 4. ฟังก์ชันเรียก AI
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

# 5. Core Logic
def generate_summary_answer(user_question):
    script_prompt = f"""
    ### Goal: แปลงคำถามให้เป็น SQL สำหรับตารางชื่อ 'transactions'
    ### Schema: {data_dict_text}
    ### Input: {user_question}
    ### Output: ตอบกลับเป็น JSON เท่านั้นในรูปแบบ {{"script": "SELECT ... FROM transactions ..."}}
    """
    
    response_text = generate_gemini_answer(script_prompt, is_json=True)
    try:
        # ลบ Markdown ป้องกันกรณี AI ส่งมาใน block code
        clean_json = response_text.replace("```json", "").replace("```", "").strip()
        sql_script = json.loads(clean_json)['script']
    except:
        return f"ขออภัย ไม่สามารถสร้างคำสั่ง SQL ได้: {response_text}"

    df_result = query_to_dataframe(sql_script)
    if isinstance(df_result, str): return df_result

    answer_prompt = f"จากข้อมูลนี้: {df_result.to_string()} สรุปคำตอบให้หน่อย: {user_question}"
    return generate_gemini_answer(answer_prompt, is_json=False)

# 6. User Interface
st.title('📊 Gemini Database Chatbot')

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("ถามคำถามเกี่ยวกับยอดขายที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner('กำลังหาคำตอบ...'):
            response = generate_summary_answer(prompt)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
