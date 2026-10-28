import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import easyocr
import numpy as np
from PIL import Image

# 페이지 설정
st.set_page_config(page_title="거래명세서 단가 관리 프로그램", layout="wide")

# --- [구글 시트 연동 설정] ---
@st.cache_resource
def init_connection():
    creds_dict = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client

try:
    client = init_connection()
    sheet = client.open("거래명세서_단가DB").sheet1
except Exception as e:
    st.error(f"구글 시트 연결에 실패했습니다. Secrets 설정을 다시 확인해주세요.\n\n에러 내용: {e}")
    st.stop()

# --- [OCR 모델 로드 (한국어/영어 지원)] ---
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['ko', 'en'])

with st.spinner("AI 텍스트 인식 엔진을 불러오는 중입니다... 잠시만 기다려주세요!"):
    reader = load_ocr_reader()

# --- [데이터 불러오기 및 저장 함수] ---
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    expected_columns
