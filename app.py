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
      val = st.sidebar.slider(label, 1, 31, 25, 1)
      display_dict["days"] = f"월 {val}일"
      tags.append(f"**월 {val}일**")
    elif any(k in key_lower for k in ["시간", "hour", "time"]):
      val = st.sidebar.slider(label, 0.0, 24.0, 5.0, 0.5)
      display_dict["hours"] = f"일 {val}시간"
      tags.append(f"**일 {val}시간**")
    elif any(k in key_lower for k in ["가구원", "인원", "명", "member"]):
      val = st.sidebar.slider(label, 1, 8, 3, 1)
      display_dict["members"] = f"{val}인 가구"
      tags.append(f"**{val}인 가구**")
    elif any(k in key_lower for k in ["대수", "대", "count", "num", "unit"]):
      val = st.sidebar.slider(label, 1, 5, 1, 1)
      display_dict["units"] = f"{val}대"
      tags.append(f"**{val}대**")
    elif any(k in key_lower for k in ["평", "면적", "area"]):
      val = st.sidebar.slider(label, 10, 60, 30, 1)
      display_dict["area"] = f"{val}평"
      tags.append(f"**{val}평**")
    elif any(k in key_lower for k in ["온도", "temp"]):
      val = st.sidebar.slider(label, 18.0, 30.0, 24.0, 0.5)
      display_dict["temp"] = f"{val}°C"
      tags.append(f"**{val}°C**")
    else:
      val = st.sidebar.slider(label, 0, 100, 10, 1)
      tags.append(f"**{val}**")

    raw_dict[orig_name] = float(val)


# --- 2. 오렌지3 모델 안전 예측 함수 ---
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
  return max(0.0, float(orange_model.skl_model.predict(X)[0]))


# --- 3. 나의 예측 요금 / 동일 조건 평균 요금 / 절약 시뮬레이션 계산 ---
my_cost = predict_safely(model, raw_dict)

# 동일 주거·기기 환경에서 표준 사용 패턴(월 20일, 일 4시간, 26도, 약풍/자동) 적용 시 평균 요금
avg_dict = raw_dict.copy()
for attr in raw_attrs:
  k = attr.name.lower()
  if any(w in k for w in ["일수", "일", "day"]):
    avg_dict[attr.name] = 20.0
  elif any(w in k for w in ["시간", "hour", "time"]):
    avg_dict[attr.name] = 4.0
  elif any(w in k for w in ["온도", "temp"]):
    avg_dict[attr.name] = 26.0
  elif attr.is_discrete and any(w in k for w in ["바람", "wind"]):
    opts = list(attr.values)
    mild_opt = next(
        (o for o in opts if "약" in o or "자동" in o), opts[len(opts) // 2]
    )
    avg_dict[attr.name] = float(attr.to_val(mild_opt))

avg_cost = predict_safely(model, avg_dict)
diff_cost = my_cost - avg_cost
diff_pct = (diff_cost / avg_cost * 100) if avg_cost > 0 else 0.0

# 절약 팁 시뮬레이션: 희망 온도 +2°C, 일 가동 시간 -1시간
tip_dict = raw_dict.copy()
cur_temp = 24.0
for attr in raw_attrs:
  k = attr.name.lower()
  if any(w in k for w in ["온도", "temp"]):
    cur_temp = tip_dict[attr.name]
    tip_dict[attr.name] = min(30.0, cur_temp + 2.0)
  elif any(w in k for w in ["시간", "hour", "time"]):
    tip_dict[attr.name] = max(0.5, tip_dict[attr.name] - 1.0)

tip_cost = predict_safely(model, tip_dict)
saved_amount = max(0.0, my_cost - tip_cost)
target_temp = min(30, int(cur_temp + 2))

# --- 4. 오른쪽 메인 화면 출력 ---
st.title("❄️ 에어컨 예상 전기요금 계산기")

env_summary = " · ".join(
    filter(
        None,
        [
            display_dict.get("members", ""),
            display_dict.get("area", ""),
            f"{display_dict.get('ac_type', '')} {display_dict.get('units', '')}".strip(),
            display_dict.get("drive_type", ""),
        ],
    )
)
st.caption(f"AI 신경망 회귀 모델 예측 결과 | 조건: {env_summary}")
st.write("")

# 3단 비교 카드
col1, col2, col3 = st.columns(3)

with col1:
  st.markdown(
      f"""
        <div style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:24px; text-align:center;">
            <div style="font-size:14px; color:#64748b; margin-bottom:8px;">나의 월간 에어컨 예상 요금</div>
            <div style="font-size:34px; font-weight:800; color:#2563eb;">{my_cost:,.0f}원</div>
            <div style="font-size:12px; color:#64748b; margin-top:8px;">
                사용 패턴: {display_dict.get('days', '')} · {display_dict.get('hours', '')} ({display_dict.get('temp', '')})
            </div>
        </div>
        """,
      unsafe_allow_html=True,
  )

with col2:
  st.markdown(
      f"""
        <div style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:24px; text-align:center;">
            <div style="font-size:14px; color:#64748b; margin-bottom:8px;">동일 조건 가구 평균 요금</div>
            <div style="font-size:34px; font-weight:800; color:#1e293b;">{avg_cost:,.0f}원</div>
            <div style="font-size:12px; color:#64748b; margin-top:8px;">
                동일 환경 표준 사용 기준 (월 20일 · 일 4.0시간 · 26°C)
            </div>
        </div>
        """,
      unsafe_allow_html=True,
  )

with col3:
  diff_sign = "+" if diff_cost > 0 else ""
  diff_color = (
      "#dc2626" if diff_cost > 500 else ("#16a34a" if diff_cost < -500 else "#1e293b")
  )
  diff_sub = (
      f"평균보다 {abs(diff_pct):.1f}% 더 높은 수준"
      if diff_cost > 500
      else (
          f"평균보다 {abs(diff_pct):.1f}% 절약 중"
          if diff_cost < -500
          else "평균과 비슷한 적정 수준"
      )
  )
  st.markdown(
      f"""
        <div style="background-color:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:24px; text-align:center;">
            <div style="font-size:14px; color:#64748b; margin-bottom:8px;">평균 대비 요금 차이</div>
            <div style="font-size:34px; font-weight:800; color:{diff_color};">{diff_sign}{diff_cost:,.0f}원</div>
            <div style="font-size:12px; color:#64748b; margin-top:8px;">{diff_sub}</div>
        </div>
        """,
      unsafe_allow_html=True,
  )

st.write("")

# 맞춤형 피드백 배너
if diff_cost > 500:
  st.markdown(
      f"""
        <div style="background-color:#fefce8; border:1px solid #fef08a; border-radius:10px; padding:18px 22px; color:#854d0e; font-size:15px; line-height:1.6;">
            ⚠️ <b>절약이 필요해요!</b> 비슷한 주거 환경(<b>{display_dict.get('members', '')}, {display_dict.get('area', '')}</b>)에서 <b>{display_dict.get('ac_type', '')} {display_dict.get('units', '')}</b>를 사용하는 가구 평균보다 약 <b>{diff_cost:,.0f}원 ({diff_pct:.1f}%)</b> 더 나올 것으로 예상됩니다.<br>
            💡 <b>절약 팁:</b> 희망 온도를 <b>2°C 높이고({target_temp}°C)</b> 하루 사용 시간을 <b>1시간만 줄여도</b> 한 달에 약 <b>{saved_amount:,.0f}원</b>을 아낄 수 있습니다.
        </div>
        """,
      unsafe_allow_html=True,
  )
elif diff_cost < -500:
  st.markdown(
      f"""
        <div style="background-color:#f0fdf4; border:1px solid #bbf7d0; border-radius:10px; padding:18px 22px; color:#166534; font-size:15px; line-height:1.6;">
            ✅ <b>아주 알뜰하게 사용하고 계세요!</b> 비슷한 조건의 가구 평균보다 한 달에 약 <b>{abs(diff_cost):,.0f}원 ({abs(diff_pct):.1f}%)</b> 적게 나올 것으로 예상됩니다.<br>
            💡 <b>유지 팁:</b> 현재 설정하신 <b>{display_dict.get('temp', '')}</b>와 <b>{display_dict.get('hours', '')}</b> 가동 패턴을 유지하시면 여름철 누진세 구간 진입을 효과적으로 막을 수 있습니다.
        </div>
        """,
      unsafe_allow_html=True,
  )
else:
  st.markdown(
      f"""
        <div style="background-color:#eff6ff; border:1px solid #bfdbfe; border-radius:10px; padding:18px 22px; color:#1e40af; font-size:15px; line-height:1.6;">
            👍 <b>적정 수준으로 사용하고 계세요!</b> 비슷한 주거 환경의 가구 평균 요금과 거의 일치하는 수준입니다.<br>
            💡 <b>추가 절약 팁:</b> 희망 온도를 <b>2°C 높이고({target_temp}°C)</b> 하루 사용 시간을 <b>1시간 줄이면</b> 한 달에 약 <b>{saved_amount:,.0f}원</b>을 추가로 절약할 수 있습니다.
        </div>
        """,
      unsafe_allow_html=True,
  )
