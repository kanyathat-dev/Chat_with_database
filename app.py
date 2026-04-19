import streamlit as st
import pandas as pd
import sqlite3
import json
from google import genai
from google.genai import types

# ดึง API Key
gemini_api_key = st.secrets["gemini_api_key"]
gmn_client = genai.Client(api_key=gemini_api_key)

# รายละเอียดตาราง
data_table = 'transactions'
data_dict_text = """
- trx_date: วันที่ทำธุรกรรม, trx_no: หมายเลขธุรกรรม, member_code: รหัสสมาชิก, 
- branch_code: รหัสสาขา, branch_region: ภูมิภาค, branch_province: จังหวัด, 
- product_code: รหัสสินค้า, product_category: หมวดหมู่หลัก, product_group: กลุ่มของสินค้า, 
- product_type: ประเภทของสินค้า, order_qty: จำนวน, unit_price: ราคาขาย, 
- cost: ต้นทุน, item_discount: ส่วนลดสินค้า, customer_discount: ส่วนลดลูกค้า, 
- net_amount: ยอดขายสุทธิ, cost_amount: ต้นทุนรวม
"""

# HELPER FUNCTIONS (คงเดิม)
def query_to_dataframe(sql_query):
    try:
        # อ่าน CSV แทน .db
        df = pd.read_csv('test_transactions_2026.csv', sep=None, engine='python')
        conn = sqlite3.connect(':memory:')
        df.to_sql(data_table, conn, index=False)
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Database Error: {e}"

def generate_gemini_answer(prompt, is_json=False):
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if is_json else "text/plain" 
        )
        response = gmn_client.models.generate_content(
            model='gemini-1.5-flash', # ปรับให้เป็นรุ่นที่รองรับทั่วไป
            contents=prompt,
            config=config)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# PROMPT TEMPLATES (คงเดิมแต่ใส่ตัวแปรให้ครบ)
script_prompt = "คำถาม: {question} \nSchema: {data_dict} \nตอบเป็น JSON: {{\"script\": \"SELECT ...\"}}"
answer_prompt = "คำถาม: {question} \nข้อมูล: {raw_data} \nสรุปคำตอบเป็นภาษาไทย"

# CORE LOGIC
def generate_summary_answer(user_question):
    # 1. สร้าง SQL
    prompt = script_prompt.format(question=user_question, data_dict=data_dict_text)
    sql_json_text = generate_gemini_answer(prompt, is_json=True)
    try:
        sql_script = json.loads(sql_json_text.replace("```json","").replace("```",""))['script']
    except:
        return "ขออภัย ไม่สามารถสร้างคำสั่ง SQL ได้"

    # 2. Query ข้อมูล
    df_result = query_to_dataframe(sql_script)
    if isinstance(df_result, str): return df_result

    # 3. สรุปคำตอบ
    prompt_ans = answer_prompt.format(question=user_question, raw_data=df_result.to_string())
    return generate_gemini_answer(prompt_ans, is_json=False)

# USER INTERFACE (แก้การเยื้องให้ตรง)
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title('📊Gemini Chat with Database')

# แสดงประวัติการสนทนา
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# รับ Input
if prompt := st.chat_input("พิมพ์คำถามที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner('กำลังหาคำตอบ...'):
            response = generate_summary_answer(prompt)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
