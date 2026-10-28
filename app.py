import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pytesseract
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

# --- [데이터 불러오기 및 저장 함수] ---
def load_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    expected_columns = ['item_name', 'spec', 'price', 'supplier', 'date']
    if df.empty or not all(col in df.columns for col in expected_columns):
        df = pd.DataFrame(columns=expected_columns)
    return df

def save_data(df):
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

df = load_data()

# --- [화면 UI 구성] ---
st.title("📦 거래명세서 단가 관리 프로그램 (사진 인식 + 구글 시트 연동)")
st.markdown("영수증이나 거래명세서 사진을 올리면 글자를 인식하고, 구글 시트에 영구 보존됩니다!")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("새로운 단가 정보 입력 (사진 업로드 가능)")
    
    # 사진 업로드 영역
    uploaded_file = st.file_uploader("📷 거래명세서/영수증 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 사진", width=300)
