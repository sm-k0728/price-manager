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

# --- [텍스트 자동 분석/파싱 함수] ---
def parse_ocr_text(text):
    """
    OCR로 읽어온 텍스트에서 품목, 규격, 단가, 공급처를 자동으로 추정해서 뽑아내는 함수
    """
    parsed = {
        'item_name': '',
        'spec': '',
        'price': 0,
        'supplier': ''
    }
    
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 1. 단가/금액 추출 (숫자 세 자리마다 점/쉼표 있는 패턴 또는 연속된 숫자 중 가장 큰 값)
    numbers = re.findall(r'\b\d{1,3}(?:[,\.]\d{3})*\b|\b\d{3,8}\b', text)
    valid_prices = []
    for num in numbers:
        clean_num = int(re.sub(r'[^\d]', '', num))
        # 일반적으로 100원 ~ 1,000,000원 사이 단가 추정
        if 100 <= clean_num <= 5000000:
            valid_prices.append(clean_num)
    if valid_prices:
        # 추출된 숫자가 있으면 넣어줌
        parsed['price'] = valid_prices[0]

    # 2. 공급처 (상호, 주식회사, 대표 등 포함된 줄 탐색)
    for line in lines:
        if any(keyword in line for keyword in ['상호', '공급자', '업체', '(주)', '주식회사', '상사', '유통']):
            clean_line = re.sub(r'(상호|공급자|업체명|:|\(\vert{}\))', '', line).strip()
            if clean_line:
                parsed['supplier'] = clean_line
                break

    # 3. 품목명 및 규격 (첫 번째나 두 번째 적절한 글자 줄을 품목으로 지정)
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
        'item_name': '',
        'spec': '',
        'price': 0,
        'supplier': '',
        'date': datetime.today()
    }

# --- [화면 UI 구성] ---
st.title("📦 거래명세서 단가 관리 프로그램 (자동 인식 + 구글 시트)")
st.markdown("사진을 업로드하면 글자를 읽어 **입력창에 자동으로 채워집니다!**")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("1. 📷 영수증/거래명세서 사진 분석")
    uploaded_file = st.file_uploader("사진을 올리면 아래 입력창에 값이 자동으로 들어갑니다.", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        col_img, col_info = st.columns([1, 2])
        image = Image.open(uploaded_file)
        
        with col_img:
            st.image(image, caption="업로드된 사진", width=250)
            
        with col_info:
            if st.button("⚡ 사진 분석하고 입력창에 자동으로 채우기"):
                with st.spinner("AI가 텍스트를 읽고 정보를 추출하는 중입니다..."):
                    try:
                        raw_text = pytesseract.image_to_string(image, lang='kor+eng')
                        extracted = parse_ocr_text(raw_text)
                        
                        # 자동 채우기 세션 변수 업데이트
                        st.session_state['form_data']['item_name'] = extracted['item_name']
                        st.session_state['form_data']['spec'] = extracted['spec']
                        st.session_state['form_data']['price'] = extracted['price']
                        st.session_state['form_data']['supplier'] = extracted['supplier']
                        st.session_state['raw_text'] = raw_text
                        
                        st.success("✨ 분석 완료! 아래 입력창에 값이 자동으로 입력되었습니다. (확인 후 수정 가능)")
                    except Exception as e:
                        st.error(f"사진 인식 실패: {e}\n`packages.txt`에 tesseract 설정이 완료되었는지 확인해 주세요.")

    if 'raw_text' in st.session_state:
        with st.expander("🔍 사진에서 읽어낸 원본 전체 텍스트 보기"):
            st.text(st.session_state['raw_text'])

    st.markdown("---")
    st.subheader("2. ✍️ 단가 정보 확인 및 저장")

    # 입력 폼 (사진 분석 결과가 세션에 남아 자동으로 채워짐)
    with st.form("price_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("품목명 (item_name)", value=st.session_state['form_data']['item_name'])
            price = st.number_input("단가 (price)", min_value=0, step=100, value=int(st.session_state['form_data']['price']))
            supplier =
