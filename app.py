import os

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

LABEL_MAP = {
    "members": "👥 가구원 수",
    "area": "🏠 주택 평형",
    "ac_type": "❄️ 에어컨 종류",
    "drive_type": "⚙️ 냉방 방식",
    "units": "🔢 가동 대수 (대)",
    "days": "📅 월 사용 일수 (일)",
    "hours": "⏰ 일평균 가동 시간 (시간)",
    "wind": "💨 바람 세기",
    "temp": "🌡️ 희망 온도 (°C)",
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
st.sidebar.caption("값을 조절하면 오른쪽 예상 결과와 피드백이 즉시 바뀝니다.")

raw_dict = {}
display_dict = {}
tags = []

for attr in raw_attrs:
  orig_name = attr.name
  key_lower = orig_name.lower()
  label = LABEL_MAP.get(key_lower, orig_name)

  if attr.is_discrete:
    options = list(attr.values)
    if len(options) <= 3:
      choice = st.sidebar.radio(label, options=options)
    else:
      choice = st.sidebar.selectbox(label, options=options)
    raw_dict[orig_name] = float(attr.to_val(choice))
    display_dict[key_lower] = choice
    tags.append(f"**{choice}**")

  elif attr.is_continuous:
    if any(k in key_lower for k in ["일수", "일", "day"]):
      val = st.sidebar.slider(label, 1,
