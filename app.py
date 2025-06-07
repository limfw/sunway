import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gspread"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

try:
    sheet = client.open_by_key("1ONYiSZfhSUhIHU51kTAtuHXDLILLaUnpYlogObG5dA8").worksheet("Sheet1")
    st.success("✅ Successfully connected to Google Sheet!")
except Exception as e:
    st.error(f"❌ Failed to connect: {e}")
