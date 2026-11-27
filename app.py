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

# 전처리 전 원본 입력 변수(original_domain) 가져오기
raw_domain = getattr(model, "original_domain", None) or model.domain
raw_attrs = raw_domain.attributes

# --- 왼쪽 사이드바: 조건 입력 영역 ---
st.sidebar.header("⚙️ 사용 환경 및 패턴 설정")
st.sidebar.caption("값을 조절하면 오른쪽 예상 결과가 즉시 바뀝니다.")

input_values = []
summary_tags = []

for attr in raw_attrs:
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
      val = st.sidebar
