import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pickle
import numpy as np
import Orange
import streamlit as st

st.set_page_config(
    page_title="에어컨 예상 전기요금 계산기", page_icon="❄️", layout="wide"
)


@st.cache_resource
def load_model():
  with open("Air Conditioner Cost Calculator.pkcls", "rb") as f:
    return pickle.load(f)


model = load_model()

# --- 왼쪽 사이드바: 조건 입력 영역 ---
st.sidebar.header("⚙️ 사용 환경 및 패턴 설정")
st.sidebar.caption("값을 조절하면 오른쪽 예상 결과가 즉시 바뀝니다.")

input_values = []
summary_tags = []

for attr in model.domain.attributes:
  name = attr.name

  # 1. 선택형(범주형) 변수 -> 라디오 버튼 또는 드롭다운
  if attr.is_discrete:
    options = list(attr.values)
    if len(options) <= 3:
      choice = st.sidebar.radio(name, options=options)
    else:
      choice = st.sidebar.selectbox(name, options=options)
    input_values.append(attr.to_val(choice))
    summary_tags.append(f"{name}: **{choice}**")

  # 2. 숫자형 변수 -> 변수 이름에 맞춰 슬라이더로 자동 변환
  elif attr.is_continuous:
    lower_name = name.lower()

    if any(k in lower_name for k in ["일수", "일", "day"]):
      val = st.sidebar.slider(name, min_value=1, max_value=31, value=25, step=1)
      display_val = f"{val}일"
    elif any(k in lower_name for k in ["시간", "hour", "time"]):
      val = st.sidebar.slider(
          name, min_value=0.0, max_value=24.0, value=5.0, step=0.5
      )
      display_val = f"{val}시간"
    elif any(k in lower_name for k in ["가구원", "인원", "명"]):
      val = st.sidebar.slider(name, min_value=1, max_value=8, value=3, step=1)
      display_val = f"{val}명"
    elif any(k in lower_name for k in ["대수", "대", "count", "num"]):
      val = st.sidebar.slider(name, min_value=1, max_value=5, value=1, step=1)
      display_val = f"{val}대"
    elif any(k in lower_name for k in ["평", "면적", "area"]):
      val = st.sidebar.slider(name, min_value=10, max_value=60, value=30, step=1)
      display_val = f"{val}평"
    elif any(k in lower_name for k in ["온도", "temp"]):
      val = st.sidebar.slider(
          name, min_value=18.0, max_value=30.0, value=24.0, step=0.5
      )
      display_val = f"{val}°C"
    elif getattr(attr, "number_of_decimals", 2) == 0:
      val = st.sidebar.slider(name, min_value=0, max_value=100, value=10, step=1)
      display_val = f"{val}"
    else:
      val = st.sidebar.number_input(name, value=0.0, step=1.0, format="%.1f")
      display_val = f"{val:.1f}"

    input_values.append(float(val))
    summary_tags.append(f"{name}: **{display_val}**")

# --- 실시간 예측 계산 ---
input_domain = Orange.data.Domain(model.domain.attributes)
input_data = np.array([input_values], dtype=float)
input_table = Orange.data.Table.from_numpy(input_domain, input_data)
prediction = float(model(input_table)[0])

target_name = (
    model.domain.class_var.name
    if model.domain.class_var
    else "예상 전기요금"
)

# --- 오른쪽 메인 화면: 결과 대시보드 ---
st.title("❄️ 에어컨 예상 전기요금 계산기")
st.markdown("선택 조건 | " + " · ".join(summary_tags))
st.divider()

# 강조 카드 스타일 적용
st.markdown(
    f"""
    <div style="
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 32px;
        text-align: center;
        margin-bottom: 20px;
    ">
        <div style="font-size: 16px; color: #64748b; margin-bottom: 8px;">
            AI 모델 예측 결과 ({target_name})
        </div>
        <div style="font-size: 46px; font-weight: 800; color: #2563eb;">
            {prediction:,.0f}원
        </div>
        <div style="font-size: 13px; color: #94a3b8; margin-top: 8px;">
            정밀 예측값: {prediction:,.2f}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "💡 왼쪽 사이드바의 슬라이더와 옵션을 움직이면 예측 결과가 실시간으로 반영됩니다."
)
