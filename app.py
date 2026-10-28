from datetime import datetime
import json
import os
import sqlite3
import pandas as pd
from PIL import Image, ImageOps
from google import genai
import streamlit as st

# ==========================================
# 🔑 최신 google-genai 클라이언트 초기화
# ==========================================
try:
  api_key = st.secrets["GEMINI_API_KEY"]
  os.environ["GEMINI_API_KEY"] = api_key
  # 최신 SDK 표준 클라이언트 생성
  client = genai.Client()
except Exception:
  client = None

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

st.title("📦 거래명세서 AI 스마트 단가 관리기")

# 화면 탭 설정
tab1, tab2 = st.tabs(
    ["🔍 전체 품목 조회 및 수정/삭제", "📝 AI 사진 자동 분석 및 등록"]
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
  st.subheader("📝 AI 비전 기반 거래명세서 자동 인식")

  uploaded_file = st.file_uploader(
      "거래명세서 사진 업로드", type=["png", "jpg", "jpeg"]
  )

  if "items_df" not in st.session_state:
    st.session_state.items_df = pd.DataFrame(
        columns=["품목명", "규격", "단가(원)", "거래처", "거래일자"]
    )

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    if image.mode != "RGB":
      image = image.convert("RGB")
    st.image(image, caption="업로드된 거래명세서", use_container_width=True)

    if st.button("✨ Gemini AI로 명세서 자동 분석하기", type="primary"):
      if client is None:
        st.error(
            "Streamlit Secrets에 `GEMINI_API_KEY`가 설정되어 있는지 확인해"
            " 주세요!"
        )
      else:
        with st.spinner(
            "Gemini AI가 명세서의 품목, 규격, 단가를 정밀 분석하는 중입니다..."
        ):
          try:
            prompt = """
                        이 거래명세서 이미지에 적힌 품목 표와 공급자 정보를 분석하여 아래 JSON 형식의 리스트로만 추출해 주세요. 다른 설명은 절대 적지 마세요.
                        - item_name: 품목명
                        - spec: 규격 (예: 25A, 25*20A, 없으면 "-")
                        - price: 단가 (숫자만, 콤마 제외)
                        - supplier: 공급자(거래처) 상호명
                        - date: 거래일자 (YYYY-MM-DD 형식, 연도가 없으면 올해 2026년 기준)

                        출력 포맷 예시:
                        [
                          {"item_name": "스텐후렌지", "spec": "25A", "price": 17000, "supplier": "전주배관", "date": "2026-09-12"}
                        ]
                        """
            # 최신 SDK 비전 모델 호출
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=[image, prompt]
            )
            clean_text = (
                response.text.replace("```json", "")
                .replace("```", "")
                .strip()
            )
            parsed_data = json.loads(clean_text)

            if parsed_data:
              st.session_state.items_df = pd.DataFrame(parsed_data)
              st.success(
                  "✨ AI 자동 분석 완료! 아래 표에서 내용을 확인하고"
                  " 저장하세요."
              )
            else:
              st.warning("추출된 품목이 없습니다. 직접 입력해 주세요.")
          except Exception as e:
            st.error(f"AI 분석 중 오류가 발생했습니다: {e}")

  if st.session_state.items_df.empty:
    st.session_state.items_df = pd.DataFrame([{
        "품목명": "",
        "규격": "",
        "단가(원)": 0.0,
        "거래처": "",
        "거래일자": datetime.today().strftime("%Y-%m-%d"),
    }])

  st.markdown(
      "### 📋 등록할 품목 리스트 (클릭해서 수정 가능, 아래 `+`로 행 추가 가능)"
  )
  edited_df = st.data_editor(
      st.session_state.items_df, num_rows="dynamic", use_container_width=True
  )

  if st.button("💾 모든 품목 데이터베이스에 일괄 저장하기"):
    saved_count = 0
    for idx, row in edited_df.iterrows():
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
      st.session_state.items_df = pd.DataFrame(
          columns=["품목명", "규격", "단가(원)", "거래처", "거래일자"]
      )
      st.rerun()
    else:
      st.warning("저장할 유효한 데이터가 없습니다.")
