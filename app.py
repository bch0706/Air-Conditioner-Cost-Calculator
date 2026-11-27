import os

# 리눅스 웹 서버에서 Orange3/신경망 실행 시 멈춤(스레드 충돌) 방지
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import pickle
import numpy as np
import Orange
import streamlit as st

st.set_page_config(
    page_title="에어컨 예상 전기요금 계산기", page_icon="❄️", layout="wide"
)

# 영어 변수명을 깔끔한 한글 라벨로 변환
LABEL_MAP = {
    "members": "👥 가구원 수",
    "area": "🏠 주택 평형",
    "ac_type": "❄️ 에어컨 종류",
    "drive_type": "⚙️ 냉방 방식",
    "days": "📅 월 사용 일수 (일)",
    "hours": "⏰ 일평균 가동 시간 (시간)",
    "wind": "💨 바람 세기",
    "temp": "🌡️ 희망 온도 (°C)",
    "count": "🔢 가동 대수 (대)",
}


@st.cache_resource
def load_model():
  with open("Air Conditioner Cost Calculator.pkcls", "rb") as f:
    return pickle.load(f)


model = load_model()
raw_domain = getattr(model, "original_domain", None) or model.domain
raw_attrs = raw_domain.attributes

# --- 1. 왼쪽 사이드바: 조건 입력 ---
st.sidebar.header("⚙️ 사용 환경 및 패턴 설정")
st.sidebar.caption("값을 조절하면 오른쪽 예상 결과가 즉시 바뀝니다.")

input_values = []
summary_tags = []

for attr in raw_attrs:
  orig_name = attr.name
  label = LABEL_MAP.get(orig_name.lower(), orig_name)

  if attr.is_discrete:
    options = list(attr.values)
    if len(options) <= 3:
      choice = st.sidebar.radio(label, options=options)
    else:
      choice = st.sidebar.selectbox(label, options=options)
    input_values.append(attr.to_val(choice))
    summary_tags.append(f"**{choice}**")

  elif attr.is_continuous:
    lower_name = orig_name.lower()
    if any(k in lower_name for k in ["일수", "일", "day"]):
      val = st.sidebar.slider(
          label, min_value=1, max_value=31, value=25, step=1
      )
      display_val = f"월 {val}일"
    elif any(k in lower_name for k in ["시간", "hour", "time"]):
      val = st.sidebar.slider(
          label, min_value=0.0, max_value=24.0, value=5.0, step=0.5
      )
      display_val = f"일 {val}시간"
    elif any(k in lower_name for k in ["가구원", "인원", "명", "member"]):
      val = st.sidebar.slider(label, min_value=1, max_value=8, value=3, step=1)
      display_val = f"{val}인 가구"
    elif any(k in lower_name for k in ["대수", "대", "count", "num"]):
      val = st.sidebar.slider(label, min_value=1, max_value=5, value=1, step=1)
      display_val = f"{val}대"
    elif any(k in lower_name for k in ["평", "면적", "area"]):
      val = st.sidebar.slider(
          label, min_value=10, max_value=60, value=30, step=1
      )
      display_val = f"{val}평"
    elif any(k in lower_name for k in ["온도", "temp"]):
      val = st.sidebar.slider(
          label, min_value=18.0, max_value=30.0, value=24.0, step=0.5
      )
      display_val = f"{val}°C"
    elif getattr(attr, "number_of_decimals", 2) == 0:
      val = st.sidebar.slider(
          label, min_value=0, max_value=100, value=10, step=1
      )
      display_val = f"{val}"
    else:
      val = st.sidebar.number_input(label, value=0.0, step=1.0, format="%.1f")
      display_val = f"{val:.1f}"

    input_values.append(float(val))
    summary_tags.append(f"**{display_val}**")

#
