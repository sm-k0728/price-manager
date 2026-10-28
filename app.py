from datetime import datetime
import sqlite3
import pandas as pd
from PIL import Image, ImageOps
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
    page_title="거래명세서 단가 관리 프로그램", page_icon="📦", layout="wide"
)

st.title("📦 거래명세서 단가 관리 프로그램")

# 화면 탭 설정
tab1, tab2 = st.tabs(
    ["🔍 전체 품목 조회 및 수정/삭제", "📝 거래명세서 등록 (사진 참고용)"]
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

    edited_result_df = st.data_editor(
        display_df,
        column_config={
            "삭제": st.column_config.CheckboxColumn(required=True),
            "id": None,
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
    st.subheader("🔍 품목 통합 검색 및 최저가 확인")
    search_query = st.text_input(
        "검색할 품목명을 입력하세요 (예: 스텐 -> SUS, STS 자동 포함 검색)", ""
    )

    if search_query.strip() != "":
      q = search_query.strip().lower()

      search_terms = set([q])
      if any(k in q for k in ["스텐", "sus", "sts"]):
        search_terms.update(["스텐", "sus", "sts"])

      conditions = []
      params = []
      for term in search_terms:
        conditions.append("(item_name LIKE ? OR spec LIKE ?)")
        params.extend([f"%{term}%", f"%{term}%"])

      sql_query = f"""
          SELECT item_name, spec, price, supplier, date 
          FROM prices 
          WHERE {' OR '.join(conditions)} 
          ORDER BY price ASC
      """

      search_df = pd.read_sql(sql_query, conn, params=params)

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
  st.subheader("📝 거래명세서 사진 참조 및 단가 등록")

  # 좌우 화면 분할 (왼쪽: 사진 보기, 오른쪽: 데이터 입력 표)
  col_img, col_form = st.columns([1, 1])

  with col_img:
    st.markdown("### 📷 명세서 사진 원본")
    uploaded_file = st.file_uploader(
        "거래명세서 사진 업로드", type=["png", "jpg", "jpeg"]
    )
    if uploaded_file is not None:
      image = Image.open(uploaded_file)
      image = ImageOps.exif_transpose(image)
      if image.mode != "RGB":
        image = image.convert("RGB")
      st.image(image, caption="업로드된 명세서", use_container_width=True)
    else:
      st.info(
          "사진을 업로드하시면 좌측에 명세서 원본이 표시됩니다. 보면서"
          " 입력하세요!"
      )

  with col_form:
    st.markdown("### ⌨️ 품목 정보 입력")
    st.info(
        "💡 아래 표에서 직접 품목명, 규격, 단가, 거래처를 입력하거나 행을"
        " 추가(`+`)하여 한 번에 저장하세요."
    )

    if "manual_df" not in st.session_state:
      st.session_state.manual_df = pd.DataFrame([{
          "품목명": "",
          "규격": "",
          "단가(원)": 0.0,
          "거래처": "",
          "거래일자": datetime.today().strftime("%Y-%m-%d"),
      }])

    edited_manual_df = st.data_editor(
        st.session_state.manual_df,
        num_rows="dynamic",
        use_container_width=True,
    )

    if st.button("💾 입력한 품목 데이터베이스에 일괄 저장하기", type="primary"):
      saved_count = 0
      for idx, row in edited_manual_df.iterrows():
        if row["품목명"] and row["거래처"] and float(row["단가(원)"]) > 0:
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
        st.session_state.manual_df = pd.DataFrame([{
            "품목명": "",
            "규격": "",
            "단가(원)": 0.0,
            "거래처": "",
            "거래일자": datetime.today().strftime("%Y-%m-%d"),
        }])
        st.rerun()
      else:
        st.warning(
            "저장된 항목이 없습니다. 품목명, 거래처, 단가를 정확히 입력했는지"
            " 확인해 주세요."
        )
