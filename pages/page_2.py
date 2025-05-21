import streamlit as st
import numpy as np

# --- CSS 추가 (이 페이지 전용) ---
st.markdown("""
<style>
/* Streamlit 기본 스타일 재정의 */
.stApp {
    background-color: #FFFFFF; /* 흰색 배경 */
    font-family: "Poppins", sans-serif;
    color: #333333;
}

/* 원형 그래프 컨테이너 스타일 */
.circle-chart-container {
    width: 300px; /* 그래프 너비 */
    height: 300px; /* 그래프 높이 */
    border-radius: 50%; /* 원형으로 만들기 */
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
    margin: 50px auto; /* 중앙 정렬 및 상하 여백 */
    overflow: hidden; /* 넘치는 요소 숨기기 */
    box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1); /* 그림자 추가 */
}

/* 그래프 내부 텍스트 스타일 */
.chart-center-text {
    position: absolute;
    text-align: center;
    font-size: 28px;
    font-weight: 600;
    color: #333333;
    z-index: 2; /* 그래프 위에 표시 */
}

.chart-level-text {
    position: absolute;
    text-align: center;
    font-size: 20px;
    font-weight: 500;
    margin-top: 50px; /* "고혈압 지수" 아래에 오도록 조정 */
    color: #333333;
    z-index: 2;
}

/* Google Fonts Poppins 임포트 */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

</style>
""", unsafe_allow_html=True)

# --- 고혈압 위험 등급 분류 함수 ---
def classify_risk_level(prediction_proba):
    """
    모델의 예측 확률(0~1)을 4단계 고혈압 위험 등급으로 분류합니다.
    """
    if prediction_proba is None:
        return "분류 불가", "#CCCCCC" # 회색

    if prediction_proba <= 0.59:
        return "정상", "#38ADA9"  # 초록색
    elif prediction_proba <= 0.74:
        return "주의", "#F7D400"  # 노란색
    elif prediction_proba <= 0.89:
        return "위험", "#F79C00"  # 주황색
    else: # prediction_proba > 0.89
        return "고위험", "#FF4D4D"  # 빨간색

# --- Streamlit 앱 메인 로직 ---

st.title("고혈압 위험도 예측 결과")
st.write("모델 예측 확률에 따른 고혈압 위험 등급입니다.")

# 예측 확률을 받을 수 있는 입력 위젯 (예시)
# 실제 앱에서는 이 값을 page_1.py에서 모델 예측 결과로 받아와야 합니다.
prediction_proba_input = st.slider(
    "예측 확률을 선택하세요 (0.0 ~ 1.0)",
    min_value=0.0,
    max_value=1.0,
    value=0.65, # 초기값은 '주의' 등급 범위
    step=0.01
)

# 예측 확률에 따라 등급과 색상 결정
risk_level, color = classify_risk_level(prediction_proba_input)

# 원형 그래프 표시
st.markdown(
    f"""
    <div class="circle-chart-container" style="background-color: {color};">
        <div class="chart-center-text">고혈압 지수</div>
        <div class="chart-level-text" style="margin-top: 50px;">{risk_level} ({prediction_proba_input:.2f})</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")
st.write("이 페이지는 예측 결과 시각화를 위한 데모입니다.")
