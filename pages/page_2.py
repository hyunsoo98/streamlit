import streamlit as st
import numpy as np

# st.set_page_config는 app.py에서 이미 호출되었으므로 여기서는 제거합니다.
# st.set_page_config(page_title="고혈압 위험도 예측 결과", layout="centered")

# --- CSS 추가 (이 페이지 전용) - 제거됨 ---
# app.py에서 전역적으로 CSS를 적용하므로 여기서는 제거합니다.
# st.markdown("""...""")

# --- 고혈압 위험 등급 분류 함수 ---
def classify_risk_level(prediction_proba):
    if prediction_proba is None:
        return "분류 불가", "#CCCCCC" # 회색

    # 04_modeling.ipynb에서 Threshold 0.48로 조정되었으므로, 이를 반영하여 분류
    # 이 분류 로직은 예측 확률을 4단계로 나누는 것이므로, 0.48은 '정상'과 '주의'를 나누는 기준으로만 적용
    if prediction_proba < 0.48: # 0.48 미만이면 '정상'으로 분류 (양성 예측을 줄임)
        return "정상", "#38ADA9"  # 초록색
    elif prediction_proba <= 0.59: # 0.48 이상 0.59 이하
        return "주의", "#F7D400"  # 노란색
    elif prediction_proba <= 0.74: # 0.59 초과 0.74 이하
        return "위험", "#F79C00"  # 주황색
    else: # prediction_proba > 0.74
        return "고위험", "#FF4D4D"  # 빨간색

# --- Streamlit 앱 메인 로직 ---

st.title("고혈압 위험도 예측 결과")
st.write("모델 예측 확률에 따른 고혈압 위험 등급입니다.")

# prediction_proba와 risk_level을 session_state에서 가져옴
prediction_proba_from_session = st.session_state.get('prediction_proba')
risk_level_from_session = st.session_state.get('risk_level')

if prediction_proba_from_session is not None and risk_level_from_session is not None:
    # 예측 확률에 따라 등급과 색상 결정 (다시 계산)
    # page_1.py에서 이미 계산된 등급을 가져와 사용해도 됨
    risk_level, color = classify_risk_level(prediction_proba_from_session)

    # 원형 그래프 표시
    st.markdown(
        f"""
        <div class="circle-chart-container" style="background-color: {color};">
            <div class="chart-center-text">고혈압 지수</div>
            <div class="chart-level-text">{risk_level} ({prediction_proba_from_session:.2f})</div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.info("예측 결과가 없습니다. '이미지 분석 시작하기' 페이지에서 이미지를 업로드하여 분석을 먼저 진행해주세요.")
    # page_1.py로 돌아가는 버튼 추가
    st.page_link("pages/page_1.py", label="이미지 분석 시작하기", icon="🚀")


st.markdown("---")
st.write("이 페이지는 예측 결과 시각화를 위한 것입니다.")
