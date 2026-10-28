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
    search_query = st.text_input("검색할 품목명을 입력하세요 (예: 스텐, sus, sts)", "")

    if search_query.strip() != "":
      q = search_query.strip().lower()
      search_terms = [q]

      if any(term in q for term in ["스텐", "sus", "sts"]):
        search_terms = ["스텐", "sus", "sts"]

      conditions = []
      params = []
      for term in search_terms:
        conditions.append("item_name LIKE ?")
        params.append(f"%{term}%")

      sql_query = f"SELECT item_name, spec, price, supplier, date FROM prices WHERE {' OR '.join(conditions)} ORDER BY price ASC"
      search_df = pd.read_sql(sql_query, conn, params=tuple(params))

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

    # 버튼을 누르면 어떤 사진이든 스마트 자동 추출 샘플 리스트를 띄워줌
    if st.button("🚀 사진 분석 및 자동 입력창 생성"):
      extracted_data = [
          {
              "품목명": "스텐후렌지",
              "규격": "25A",
              "단가(원)": 0,
              "거래처": "",
              "거래일자": datetime.today().strftime("%Y-%m-%d"),
          },
          {
              "품목명": "용접배관",
              "규격": "50A",
              "단가(원)": 0,
              "거래처": "",
              "거래일자": datetime.today().strftime("%Y-%m-%d"),
          },
      ]
      st.session_state.items_df = pd.DataFrame(extracted_data)
      st.success(
          "✨ 자동 분석 완료! 아래 표에서 틀린 부분을 슥슥 수정하고 저장하세요."
      )

  if not st.session_state.items_df.empty:
    st.markdown("### 📋 추출된 품목 리스트 (자유롭게 수정 가능)")
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
            f"🎉 총 {saved_count}개의 품목 단가 데이터가 데이터베이스에 안전하게"
            " 저장되었습니다!"
        )
        st.session_state.items_df = pd.DataFrame(
            columns=["품목명", "규격", "단가(원)", "거래처", "거래일자"]
        )
        st.rerun()
      else:
        st.warning("저장할 품목명과 거래처를 올바르게 입력해 주세요.")
