import pickle
import numpy as np
import Orange
import streamlit as st

st.set_page_config(page_title="예측 모델 웹 앱", layout="centered")
st.title("📊 Orange3 회귀 모델 예측")


# 모델 로딩 속도 최적화를 위해 캐싱 적용
@st.cache_resource
def load_model():
  with open("model.pkcls", "rb") as f:
    return pickle.load(f)


model = load_model()

st.write("값을 입력한 뒤 **예측하기** 버튼을 눌러주세요.")

# 모델의 입력 변수(attributes)를 자동으로 불러와 입력 폼 생성
input_values = []
with st.form("predict_form"):
  for attr in model.domain.attributes:
    if attr.is_continuous:
      val = st.number_input(f"{attr.name}", value=0.0, format="%.4f")
      input_values.append(val)
    elif attr.is_discrete:
      choice = st.selectbox(f"{attr.name}", options=attr.values)
      input_values.append(attr.to_val(choice))

  submitted = st.form_submit_button("예측하기")

# 예측 수행 및 결과 출력
if submitted:
  input_domain = Orange.data.Domain(model.domain.attributes)
  input_data = np.array([input_values], dtype=float)
  input_table = Orange.data.Table.from_numpy(input_domain, input_data)

  prediction = model(input_table)
  target_name = (
      model.domain.class_var.name if model.domain.class_var else "예측값"
  )

  st.success(f"**{target_name}:** {prediction[0]:.4f}")