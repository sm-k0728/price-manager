import streamlit as st
import pandas as pd
from datetime import datetime
import pytesseract
from PIL import Image, ImageOps
import re

# 페이지 설정
st.set_page_config(page_title="거래명세서 단가 관리 프로그램", layout="wide")

# 세션 상태 초기화
if 'db' not in st.session_state:
    st.session_state['db'] = pd.DataFrame(columns=['item_name', 'spec', 'price', 'supplier', 'date'])

if 'form_data' not in st.session_state:
    st.session_state['form_data'] = {
        'item_name': '', 'spec': '', 'price': 0, 'supplier': '', 'date': datetime.today()
    }

def parse_ocr_text(text):
    parsed = {'item_name': '', 'spec': '', 'price': 0, 'supplier': ''}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 단가 추출 (숫자 패턴)
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

st.title("📦 거래명세서 단가 관리 프로그램 (자동 입력 테스트)")
st.markdown("사진을 올리면 텍스트를 추출하고 입력창에 자동으로 채워집니다!")

tab1, tab2 = st.tabs(["📝 단가 등록 / 수정", "📊 단가 DB 조회"])

with tab1:
    st.subheader("1. 📷 사진 업로드 및 자동 분석")
    uploaded_file = st.file_uploader("영수증/거래명세서 사진 업로드", type=["png", "jpg", "jpeg"])
    
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            image = ImageOps.exif_transpose(image)
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            st.image(image, caption="업로드된 사진", width=300)
            
            if st.button("⚡ 사진 분석하고 입력창에 채우기"):
                with st.spinner("텍스트 추출 및 분석 중..."):
                    # 한글+영문 OCR 실행
                    text = pytesseract.image_to_string(image, lang='kor+eng')
                    extracted = parse_ocr_text(text)
                    
                    # 세션 상태에 저장하여 입력 폼에 즉시 반영
                    st.session_state['form_data']['item_name'] = extracted['item_name']
                    st.session_state['form_data']['spec'] = extracted['spec']
                    st.session_state['form_data']['price'] = extracted['price']
                    st.session_state['form_data']['supplier'] = extracted['supplier']
                    st.session_state['extracted_text'] = text
                    
                    st.success("✨ 분석 완료! 아래 입력창을 확인해 주세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")

    if 'extracted_text' in st.session_state:
        with st.expander("🔍 OCR 원본 텍스트 전체보기"):
            st.text(st.session_state['extracted_text'])

    st.markdown("---")
    st.subheader("2. ✍️ 정보 확인 및 임시 저장")

    with st.form("test_form"):
        col1, col2 = st.columns(2)
        with col1:
            item_name = st.text_input("품목명", value=st.session_state['form_data']['item_name'])
            price = st.number_input("단가", min_value=0, step=100, value=int(st.session_state['form_data']['price']))
            supplier = st.text_input("공급처", value=st.session_state['form_data']['supplier'])
        with col2:
            spec = st.text_input("규격", value=st.session_state['form_data']['spec'])
            date = st.date_input("등록일자", value=st.session_state['form_data']['date'])
            
        submitted = st.form_submit_button("임시 저장하기")
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
                st.session_state['db'] = pd.concat([st.session_state['db'], new_row], ignore_index=True)
                st.success(f"🎉 [{item_name}] 저장 완료!")
                
                # 저장 후 입력폼 초기화
                st.session_state['form_data'] = {
                    'item_name': '', 'spec': '', 'price': 0, 'supplier': '', 'date': datetime.today()
                }
                st.rerun()

with tab2:
    st.subheader("📊 임시 저장된 DB 목록")
    st.dataframe(st.session_state['db'], use_container_width=True)
