import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

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
st.title("📦 거래명세서 단가 관리 프로그램 (구글 시트 영구 연동)")
st.markdown("데이터가 구글 스프레드시트에 안전하게 영구 보존됩니다!")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("새로운 단가 정보 입력")
    
    with st.form("price_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("품목명 (item_name)")
            price = st.number_input("단가 (price)", min_value=0, step=100)
            supplier = st.text_input("공급처 (supplier)")
        with col2:
            spec = st.text_input("규격 (spec)")
            date = st.date_input("등록일자 (date)", value=datetime.today())
            
        submitted = st.form_submit_button("💾 구글 시트에 영구 저장하기")
        
        if submitted:
            if not item_name.strip():
                st.warning("품목명을 입력해주세요!")
            else:
                new_row = pd.DataFrame({
                    'item_name': [item_name],
                    'spec': [spec],
                    'price': [price],
                    'supplier': [supplier],
                    'date': [str(date)]
                })
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success(f"[{item_name}] 단가 정보가 구글 시트에 성공적으로 저장되었습니다!")
                st.rerun()

with tab2:
    st.subheader("저장된 단가 DB 목록")
    if df.empty:
        st.info("아직 저장된 데이터가 없습니다. 단가를 등록해 보세요!")
    else:
        st.dataframe(df, use_container_width=True)
        
        if not df.empty:
            st.markdown("---")
            st.subheader("🗑️ 데이터 삭제")
            del_index = st.selectbox("삭제할 행 번호 선택", options=df.index)
            if st.button("선택한 행 삭제"):
                df = df.drop(del_index).reset_index(drop=True)
                save_data(df)
                st.success("선택한 데이터가 삭제되었습니다!")
                st.rerun()
