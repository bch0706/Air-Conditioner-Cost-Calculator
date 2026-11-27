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

st.sidebar.header("⚙️ 사용 환경 및 패턴 설정")
st.sidebar.caption("값을 조절하면 오른쪽 예상 결과가 즉시 바뀝니다.")

raw_dict = {}
tags = []

for attr in raw_attrs:
  orig_name = attr.name
  label = LABEL_MAP.get(orig_name.lower(), orig_name)

  if attr.is_discrete:
    options = list(attr.values)
    if len(options) <= 3:
      choice = st.sidebar.radio(label, options=options)
    else:
      choice = st.sidebar.selectbox(label, options=options)
    raw_dict[orig_name] = float(attr.to_val(choice))
    tags.append(f"**{choice}**")

  elif attr.is_continuous:
    lower_name = orig_name.lower()
    if any(k in lower_name for k in ["일수", "일", "day"]):
      val = st.sidebar.slider(label, 1, 31, 25, 1)
      tags.append(f"**월 {val}일**")
    elif any(k in lower_name for k in ["시간", "hour", "time"]):
      val = st.sidebar.slider(label, 0.0, 24.0, 5.0, 0.5)
      tags.append(f"**일 {val}시간**")
    elif any(k in lower_name for k in ["가구원", "인원", "명", "member"]):
      val = st.sidebar.slider(label, 1, 8, 3, 1)
      tags.append(f"**{val}인 가구**")
    elif any(k in lower_name for k in ["대수", "대", "count", "num", "unit"]):
      val = st.sidebar.slider(label, 1, 5, 1, 1)
      tags.append(f"**{val}대**")
    elif any(k in lower_name for k in ["평", "면적", "area"]):
      val = st.sidebar.slider(label, 10, 60, 30, 1)
      tags.append(f"**{val}평**")
    elif any(k in lower_name for k in ["온도", "temp"]):
      val = st.sidebar.slider(label, 18.0, 30.0, 24.0, 0.5)
      tags.append(f"**{val}°C**")
    else:
      val = st.sidebar.slider(label, 0, 100, 10, 1)
      tags.append(f"**{val}**")

    raw_dict[orig_name] = float(val)


# 2단계 이상 중첩된 오렌지 전처리(원-핫 인코딩 + 정규화)를 끝까지 추적해 계산
def eval_var(var, data_dict):
  if var.name in data_dict:
    return float(data_dict[var.name])
  cv = getattr(var, "compute_value", None)
  if cv is not None and hasattr(cv, "variable"):
    base_val = eval_var(cv.variable, data_dict)
    if hasattr(cv, "value"):
      val = 1.0 if base_val == cv.value else 0.0
    else:
      val = float(base_val)
    offset = getattr(cv, "offset", 0.0) or 0.0
    scale = getattr(cv, "scale", 1.0)
    if scale is None or scale == 0:
      scale = 1.0
    return (val - offset) * scale
  return 0.0


def predict_safely(orange_model, data_dict):
  encoded = [eval_var(m_attr, data_dict) for m_attr in orange_model.domain.attributes]
  X = np.array([encoded], dtype=float)
  return float(orange_model.skl_model.predict(X)[0])


st.title("❄️ 에어컨 예상 전기요금 계산기")
st.markdown("선택 조건 | " + " · ".join(tags))
st.divider()

try:
  prediction = predict_safely(model, raw_dict)
  target_class = raw_domain.class_var or model.domain.class_var
  target_name = target_class.name if target_class else "예상 전기요금"

  st.markdown(
      f"""
        <div style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:36px; text-align:center; margin-bottom:20px;">
            <div style="font-size:16px; color:#64748b; margin-bottom:10px;">AI 모델 예측 결과 ({target_name})</div>
            <div style="font-size:48px; font-weight:800; color:#2563eb;">{prediction:,.0f}원</div>
            <div style="font-size:13px; color:#94a3b8; margin-top:8px;">정밀 예측값: {prediction:,.2f}</div>
        </div>
        """,
      unsafe_allow_html=True,
  )
  st.info(
      "💡 왼쪽 사이드바의 옵션을 조절하면 예상 요금이 실시간으로 계산됩니다."
  )

except Exception as e:
  st.error(f"예측 계산 중 오류가 발생했습니다: {e}")
