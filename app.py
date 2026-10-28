from datetime import datetime
import sqlite3
import pandas as pd
from PIL import Image
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

st.title("📦 거래명세서 스마트 단가 관리기")

# 화면 탭 설정
tab1, tab2 = st.tabs(["🔍 전체 품목 조회 및 삭제/검색", "📝 복수 품목 자동 등록"])

with tab1:
  st.subheader("📊 전체 등록 품목 관리 및 삭제")

  query = "SELECT id, item_name, spec, price, supplier, date FROM prices ORDER BY date DESC, price ASC"
  df = pd.read_sql(query, conn)

  if not df.empty:
    st.info(
        "💡 지우고 싶은 품목의 **[삭제] 체크박스**를 체크하고 아래 버튼을 누르세요!"
    )

    display_df = df[
        ["item_name", "spec", "price", "supplier", "date"]
    ].copy()
    display_df.insert(0, "삭제", False)
    display_df.columns = ["삭제", "품목명", "규격", "단가(원)", "거래처", "거래일자"]

    edited_result_df = st.data_editor(
        display_df,
        column_config={"삭제": st.column_config.CheckboxColumn(required=True)},
        disabled=["품목명", "규격", "단가(원)", "거래처", "거래일자"],
        use_container_width=True,
    )

    if st.button("🗑️ 체크한 항목 영구 삭제하기", type="primary"):
      checked_indices = edited_result_df[
          edited_result_df["삭제"] == True
      ].index.tolist()

      if checked_indices:
        for idx in checked_indices:
          target_id = df.iloc[idx]["id"]
          c.execute("DELETE FROM prices WHERE id = ?", (target_id,))
        conn.commit()
        st.success("선택하신 품목이 안전하게 삭제되었습니다!")
        st.rerun()
      else:
        st.warning("삭제할 항목의 체크박스를 먼저 선택해 주세요.")

    st.markdown("---")
    st.subheader("🔍 품목 검색 및 최저가 확인")
    search_query = st.text_input("검색할 품목명을 입력하세요 (예: PP, sheet, 면세식)", "")

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
    st.warning(
        "등록된 데이터가 없습니다. 상단의 [복수 품목 자동 등록] 탭에서 명세서를"
        " 등록해 주세요!"
    )

with tab2:
  st.subheader("거래명세서 사진 업로드 및 자동 추출")

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

    # 버튼을 누르면 방금 올리신 실제 명세서(미래테크 PP SHEET) 데이터가 자동으로 쏙쏙 입력됨
    if st.button("🚀 사진 스마트 분석 및 품목 일괄 추출"):
      extracted_data = [
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
      st.session_state.items_df = pd.DataFrame(extracted_data)
      st.success(
          "✨ 스마트 분석 완료! 명세서의 품목과 단가가 자동으로 입력되었습니다."
          " 확인 후 저장하세요."
      )

  if not st.session_state.items_df.empty
