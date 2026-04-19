import streamlit as st
import pandas as pd

# ลองรันเฉพาะการอ่านไฟล์
try:
    df = pd.read_csv('test_transactions_2026.csv')
    st.success("อ่านไฟล์สำเร็จ!")
    st.write("ข้อมูลคอลัมน์ที่พบในไฟล์:", df.columns.tolist())
    st.write("ตัวอย่างข้อมูล:", df.head())
except Exception as e:
    st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
