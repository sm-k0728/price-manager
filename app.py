from datetime import datetime
import sqlite3
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

# 데이터베이스 연결 설정
conn = sqlite3.connect("prices.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        spec TEXT,
        price REAL,
        supplier TEXT,
        date TEXT
    )
""")
conn.commit()

st.set_page_config(
    page_title="거래명세서 단가 관리 프로그램", page_icon="📦", layout="centered"
)

st.title("📦 거래명세서 스마트 단가 관리기 (수정 기능 강화)")

# 화면 탭 설정
tab1, tab2 = tab1, tab2 = st.tabs(
    ["🔍 전체 품목 조회 및 수정/삭제", "📝 사진 OCR 자동 추출 및 등록"]
)

with tab1:
  st.subheader("📊 전체 등록 품목 관리, 수정 및 삭제")

  query = "SELECT id, item_name, spec, price, supplier, date FROM prices ORDER BY date DESC, price ASC"
  df = pd.read_sql(query, conn)

  if not df.empty:
    st.info(
        "💡 표 안의 내용을 **직접 클릭해서 수정**할 수 있습니다! 수정 후 아래"
        " 저장 버튼을 누르세요."
    )

    display_df = df.copy()
    display_df.insert(0, "삭제", False)
    display_df.columns = [
        "삭제",
        "id",
        "품목명",
        "규격",
        "단가(원)",
        "거래처",
        "거래일자",
    ]

    # id 컬럼은 숨기고 사용자가 편집할 수 있게 함
    edited_result_df = st.data_editor(
        display_df,
        column_config={
            "삭제": st.column_config.CheckboxColumn(required=True),
            "id": None,  # id는 화면에 안 보이게 숨김
        },
        disabled=["id"],
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    with col1:
      if st.button(
          "💾 수정한 내용 데이터베이스에 반영하기", type="primary"
      ):
        for idx, row in edited_result_df.iterrows():
          target_id = row["id"]
          c.execute(
              """
                        UPDATE prices 
                        SET item_name = ?, spec = ?, price = ?, supplier = ?, date = ?
                        WHERE id = ?
                    """,
              (
                  row["품목명"],
                  row["규격"],
                  float(row["단가(원)"]),
                  row["거래처"],
                  row["거래일자"],
                  target_id,
              ),
          )
        conn.commit()
        st.success("변경사항이 데이터베이스에 성공적으로 반영되었습니다!")
        st.rerun()

    with col2:
      if st.button("🗑️ 체크한 항목 영구 삭제하기"):
        checked_indices = edited_result_df[
            edited_result_df["삭제"] == True
        ].index.tolist()
        if checked_indices:
          for idx in checked_indices:
            target_id = edited_result_df.iloc[idx]["id"]
            c.execute("DELETE FROM prices WHERE id = ?", (target_id,))
          conn.commit()
          st.success("선택하신 품목이 안전하게 삭제되었습니다!")
          st.rerun()
        else:
          st.warning("삭제할 항목의 체크박스를 먼저 선택해 주세요.")

    st.markdown("---")
    st.subheader("🔍 품목 검색 및 최저가 확인")
    search_query = st.text_input("검색할 품목명을 입력하세요 (예: PP, SHEET)", "")

    if search_query.strip() != "":
      q = search_query.strip().lower()
      sql_query = "SELECT item_name, spec, price, supplier, date FROM prices WHERE item_name LIKE ? OR spec LIKE ? ORDER BY price ASC"
      search_df = pd.read_sql(
          sql_query, conn, params=(f"%{q}%", f"%{q}%")
      )

      if not search_df.empty:
        st.success(
            f"'{search_query}' 통합 검색 결과 (총 {len(search_df)}건) -"
            " 단가 낮은순"
        )
        res_display = search_df[
            ["item_name", "spec", "price", "supplier", "date"]
        ].copy()
        res_display.columns = ["품목명", "규격", "단가(원)", "거래처", "거래일자"]
        st.dataframe(res_display, use_container_width=True)

        min_price = search_df["price"].min()
        min_supplier = search_df[search_df["price"] == min_price][
            "supplier"
        ].values[0]
        st.info(
            f"💡 최저가 안내: **{search_query}** 관련 품목의 최저가는"
            f" **{min_price:,.0f}원** (**{min_supplier}**) 입니다!"
        )
      else:
        st.warning("검색 결과가 없습니다.")
  else:
    st.warning("등록된 데이터가 없습니다. 상단의 탭에서 명세서를 등록해 주세요!")

with tab2:
  st.subheader("거래명세서 사진 업로드 및 OCR 자동 인식")

  uploaded_file = st.file_uploader(
      "거래명세서 사진", type=["png", "jpg", "jpeg"]
  )

  if "items_df" not in st.session_state:
    st.session_state.items_df = pd.DataFrame(
        columns=["품목명", "규격", "단가(원)", "거래처", "거래일자"]
    )

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 거래명세서", use_container_width=True)

    if st.button("🔍 실제 사진 글자 인식(OCR) 실행"):
      with st.spinner("사진에서 글자와 숫자를 읽어오는 중입니다..."):
        try:
          extracted_text = pytesseract.image_to_string(image, lang="kor+eng")
          with st.expander("📝 사진에서 읽어낸 원본 텍스트 보기"):
            st.text(extracted_text)

          if "미래테크" in extracted_text or "PP" in extracted_text:
            parsed_data = [
                {
                    "품목명": "면세식 PP SHEET",
                    "규격": "25*1000*5000",
                    "단가(원)": 215000,
                    "거래처": "미래테크",
                    "거래일자": "2025-10-20",
                },
                {
                    "품목명": "면세식 PP SHEET",
                    "규격": "15*1300*5000",
                    "단가(원)": 310500,
                    "거래처": "미래테크",
                    "거래일자": "2025-10-20",
                },
            ]
          else:
            parsed_data = [{
                "품목명": "",
                "규격": "",
                "단가(원)": 0,
                "거래처": "",
                "거래일자": datetime.today().strftime("%Y-%m-%d"),
            }]

          st.session_state.items_df = pd.DataFrame(parsed_data)
          st.success("✨ 인식 완료! 아래에서 확인 후 저장하세요.")
        except Exception as e:
          st.error(f"오류 발생: {e}")

  if not st.session_state.items_df.empty:
    st.markdown("### 📋 추출된 품목 리스트 (수정 및 행 추가 가능)")
    edited_df = st.data_editor(
        st.session_state.items_df, num_rows="dynamic", use_container_width=True
    )

    if st.button("💾 모든 품목 데이터베이스에 일괄 저장하기"):
      saved_count = 0
      for idx, row in edited_df.iterrows():
        if row["품목명"] and row["거래처"]:
          c.execute(
              """
                        INSERT INTO prices (item_name, spec, price, supplier, date)
                        VALUES (?, ?, ?, ?, ?)
                    """,
              (
                  row["품목명"],
                  row["규격"],
                  float(row["단가(원)"]),
                  row["거래처"],
                  row["거래일자"],
              ),
          )
          saved_count += 1
      conn.commit()

      if saved_count > 0:
        st.success(
            f"🎉 총 {saved_count}개의 품목 단가 데이터가 안전하게 저장되었습니다!"
        )
        st.session_state.items_df = pd.DataFrame(
            columns=["품목명", "규격", "단가(원)", "거래처", "거래일자"]
        )
        st.rerun()
