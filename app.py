import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import pytesseract
from PIL import Image
import re

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
    st.error(f"구글 시트 연결 실패: {e}")
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

# --- [OCR 텍스트 자동 분석 함수] ---
def parse_ocr_text(text):
    parsed = {'item_name': '', 'spec': '', 'price': 0, 'supplier': ''}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 단가 추출
    numbers = re.findall(r'\b\d{1,3}(?:[,\.]\d{3})*\b|\b\d{3,8}\b', text)
    valid_prices = []
    for num in numbers:
        clean_num = int(re.sub(r'[^\d]', '', num))
        if 100 <= clean_num <= 5000000:
            valid_prices.append(clean_num)
    if valid_prices:
        parsed['price'] = valid_prices[0]

    # 공급처 추출
    for line in lines:
        if any(keyword in line for keyword in ['상호', '공급자', '업체', '(주)', '주식회사', '상사', '유통']):
            clean_line = re.sub(r'(상호|공급자|업체명|:|\(|\))', '', line).strip()
            if clean_line:
                parsed['supplier'] = clean_line
                break

    # 품목명 및 규격 추출
    filtered_lines = [l for l in lines if not any(k in l for k in ['공급자', '합계', '금액', '사업자', '날짜', '전화', '주소'])]
    if filtered_lines:
        parsed['item_name'] = filtered_lines[0]
        if len(filtered_lines) > 1:
            parsed['spec'] = filtered_lines[1]
            
    return parsed

df = load_data()

# --- [세션 상태 초기화] ---
if 'form_data' not in st.session_state:
    st.session_state['form_data'] = {
        'item_name': '', 'spec': '', 'price': 0, 'supplier': '', 'date': datetime.today()
    }

# --- [화면 UI 구성] ---
st.title("📦 거래명세서 단가 관리 프로그램")
st.markdown("사진을 올리고 버튼을 누르면 입력창에 자동으로 채워집니다!")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("1. 📷 사진 업로드 및 자동 인식")
    uploaded_file = st.file_uploader("거래명세서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        col_img, col_info = st.columns([1, 2])
        image = Image.open(uploaded_file)
        
        with col_img:
            st.image(image, caption="업로드된 사진", width=250)
            
        with col_info:
            if st.button("⚡ 사진 분석하고 입력창에 채우기"):
                with st.spinner("AI 분석 중..."):
                    try:
                        raw_text = pytesseract.image_to_string(image, lang='kor+eng')
                        extracted = parse_ocr_text(raw_text)
                        
                        st.session_state['form_data']['item_name'] = extracted['item_name']
                        st.session_state['form_data']['spec'] = extracted['spec']
                        st.session_state['form_data']['price'] = extracted['price']
                        st.session_state['form_data']['supplier'] = extracted['supplier']
                        st.session_state['raw_text'] = raw_text
                        
                        st.success("✨ 분석 완료! 아래 입력창을 확인해 주세요.")
                    except Exception as e:
                        st.error(f"인식 실패: {e}")

    if 'raw_text' in st.session_state:
        with st.expander("🔍 원본 텍스트 전체보기"):
            st.text(st.session_state['raw_text'])

    st.markdown("---")
    st.subheader("2. ✍️ 정보 확인 및 구글 시트 저장")

    with st.form("price_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("품목명", value=st.session_state['form_data']['item_name'])
            price = st.number_input("단가", min_value=0, step=100, value=int(st.session_state['form_data']['price']))
            supplier = st.text_input("공급처", value=st.session_state['form_data']['supplier'])
        with col2:
            spec = st.text_input("규격", value=st.session_state['form_data']['spec'])
            date = st.date_input("등록일자", value=st.session_state['form_data']['date'])
            
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
                st.success(f"🎉 [{item_name}] 저장 완료!")
                
                st.session_state['form_data'] = {
                    'item_name': '', 'spec': '', 'price': 0, 'supplier': '', 'date': datetime.today()
                }
                if 'raw_text' in st.session_state:
                    del st.session_state['raw_text']
                st.rerun()

with tab2:
    st.subheader("📊 단가 DB 목록")
    if df.empty:
        st.info("저장된 데이터가 없습니다.")
    else:
        st.dataframe(df, use_container_width=True)
        if not df.empty:
            st.markdown("---")
            del_index = st.selectbox("삭제할 행 선택", options=df.index)
            if st.button("선택한 행 삭제"):
                df = df.drop(del_index).reset_index(drop=True)
                save_data(df)
                st.success("삭제되었습니다!")
                st.rerun()
