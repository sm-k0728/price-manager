import streamlit as st
import pandas as pd
from datetime import datetime
import pytesseract
from PIL import Image

# 페이지 설정
st.set_page_config(page_title="거래명세서 단가 관리 프로그램", layout="wide")

# 세션 상태로 임시 데이터 저장 (메모리 DB)
if 'db' not in st.session_state:
    st.session_state['db'] = pd.DataFrame(columns=['item_name', 'spec', 'price', 'supplier', 'date'])

st.title("📦 거래명세서 단가 관리 프로그램 (초기 기본 버전)")
st.markdown("가장 가볍고 단순하게 작동하는 기본 테스트 화면입니다.")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("1. 📷 사진 업로드 및 텍스트 추출")
    uploaded_file = st.file_uploader("영수증/거래명세서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    extracted_text = ""
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 사진", width=300)
        
        if st.button("🔍 텍스트 추출하기"):
            with st.spinner("텍스트 추출 중..."):
                try:
                    extracted_text = pytesseract.image_to_string(image, lang='kor+eng')
                    st.session_state['raw_text'] = extracted_text
                    st.success("추출 완료!")
                except Exception as e:
                    st.error(f"오류 발생: {e}")

    if 'raw_text' in st.session_state:
        st.subheader("📌 추출된 원본 텍스트")
        st.text_area("OCR 결과", st.session_state['raw_text'], height=150)

    st.markdown("---")
    st.subheader("2. ✍️ 데이터 입력 및 저장")

    with st.form("basic_form"):
        item_name = st.text_input("품목명")
        spec = st.text_input("규격")
        price = st.number_input("단가", min_value=0, step=100)
        supplier = st.text_input("공급처")
        date = st.date_input("등록일자", value=datetime.today())
        
        submitted = st.form_submit_button("저장하기")
        if submitted:
            new_row = pd.DataFrame({
                'item_name': [item_name],
                'spec': [spec],
                'price': [price],
                'supplier': [supplier],
                'date': [str(date)]
            })
            st.session_state['db'] = pd.concat([st.session_state['db'], new_row], ignore_index=True)
            st.success("저장되었습니다!")

with tab2:
    st.subheader("📊 저장된 DB 목록")
    st.dataframe(st.session_state['db'], use_container_width=True)
