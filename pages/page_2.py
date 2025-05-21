
import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np

# --- Vision API 클라이언트와 임시 인증 파일 경로를 session_state에서 가져오기 ---
vision_client = st.session_state.get('vision_client')
temp_credentials_path = st.session_state.get('temp_credentials_path')
logged_in = st.session_state.get('logged_in', False)
username = st.session_state.get('username', 'Guest')

# --- 로그인 확인 및 리디렉션 로직 (이전과 동일) ---
if not logged_in:
    st.warning("로그인이 필요한 페이지입니다. 로그인 페이지로 이동해주세요.")
    st.page_link("pages/page_1.py", label="로그인 페이지로 이동")
    st.stop()
elif vision_client is None:
    st.error("Google Cloud Vision API 클라이언트가 초기화되지 않았습니다. 메인 페이지를 확인하거나 앱을 다시 시작해주세요.")
    st.stop()


# --- DB 설정 및 함수 (이미지 처리 결과 저장용 - 기존과 동일) ---
DB_FILE_IMAGE_RESULTS = "image_results.db"

def init_image_results_db():
    conn = sqlite3.connect(DB_FILE_IMAGE_RESULTS)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS image_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_name TEXT,
            extracted_text TEXT,
            parsed_data JSON,
            prediction_proba REAL,
            risk_level TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_image_result(image_name, extracted_text, parsed_data, prediction_proba, risk_level):
    conn = sqlite3.connect(DB_FILE_IMAGE_RESULTS)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO image_data (image_name, extracted_text, parsed_data, prediction_proba, risk_level)
            VALUES (?, ?, ?, ?, ?)
        """, (image_name, extracted_text, json.dumps(parsed_data), prediction_proba, risk_level))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"이미지 처리 결과 저장 중 오류 발생: {e}")
        return False
    finally:
        conn.close()

if 'image_results_db_initialized' not in st.session_state:
    init_image_results_db()
    st.session_state.image_results_db_initialized = True
# -----------------------------------------------


# --- vision_ai.ipynb 노트북에서 가져온 함수들 (여기서는 간결화를 위해 생략, 실제로는 그대로 포함) ---
# 기존 app.py에 있던 parse_health_data_from_ocr, preprocess_and_engineer_features,
# prepare_model_input, classify_risk_level 함수들을 여기에 그대로 붙여넣어야 합니다.

def parse_health_data_from_ocr(text):
    data = {}
    age_gender_match = re.search(r'나이성별\s*(\d+)\s*(여성|남성)', text)
    if age_gender_match: data['나이'] = int(age_gender_match.group(1)); data['성별'] = age_gender_match.group(2).strip()
    else: data['나이'] = None; data['성별'] = None
    height_weight_match = re.search(r'키\\(cm\\)/몸무게\\(kg\\)\\s*(\\d+)\\(cm\\)/(\\d+)\\(kg\\)', text)
    if height_weight_match: data['신장'] = int(height_weight_match.group(1)); data['체중'] = int(height_weight_match.group(2))
    else: data['신장'] = None; data['체중'] = None
    bp_match = re.search(r'고혈압\s*(\d+)/(\d+)\s*mmHg', text)
    if bp_match: data['수축기 혈압'] = int(bp_match.group(1)); data['이완기 혈압'] = int(bp_match.group(2))
    else: data['수축기 혈압'] = None; data['이완기 혈압'] = None
    patterns = {
        '혈색소': r'혈색소\(g/dL\)\s*(\d+(\.\d+)?)', '공복 혈당': r'공복혈당\(mg/dL\)\s*(\d+(\.\d+)?)',
        '총 콜레스테롤': r'총콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)', 'HDL 콜레스테롤': r'고밀도 콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)',
        '트리글리세라이드': r'중성지방\(mg/dL\)\s*(\d+(\.\d+)?)', 'LDL 콜레스테롤': r'저밀도 콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)',
        '혈청 크레아티닌': r'혈청 크레아티닌\(mg/dL\)\s*(\d+(\.\d+)?)', 'AST': r'AST\(SGOT\)\(IU/L\)\s*(\d+(\.\d+)?)',
        'ALT': r'ALT\(SGPT\)\(IU/L\)\s*(\d+(\.\d+)?)', '감마지티피': r'감마지티피\(XGTP\)\(IU/L\)\s*(\d+(\.\d+)?)',
        '요단백': r'요단백\s*([가-힣]+)', '흡연 상태': None, '음주 여부': None
    }
    for key, pattern in patterns.items():
        if pattern is None: data[key] = None; continue
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            try: data[key] = float(value_str)
            except ValueError: data[key] = value_str.strip()
            except IndexError:
                try:
                    value_str = text[match.end():].splitlines()[0].strip()
                    num_match = re.search(r'\\d+(\\.\\d+)?', value_str)
                    if num_match: data[key] = float(num_match.group(0))
                    else: data[key] = value_str
                except Exception: data[key] = None
        else: data[key] = None
    return data

def preprocess_and_engineer_features(raw_data):
    processed_data = {}
    processed_data['fasting_blood_glucose'] = raw_data.get('공복 혈당'); processed_data['total_cholesterol'] = raw_data.get('총 콜레스테롤')
    processed_data['triglycerides'] = raw_data.get('triglycerides'); processed_data['hdl_cholesterol'] = raw_data.get('HDL 콜레스테롤')
    processed_data['ldl_cholesterol'] = raw_data.get('LDL 콜레스테롤'); processed_data['hemoglobin'] = raw_data.get('혈색소')
    processed_data['serum_creatinine'] = raw_data.get('혈청 크레아티닌'); processed_data['ast'] = raw_data.get('AST')
    processed_data['alt'] = raw_data.get('ALT'); processed_data['gamma_gtp'] = raw_data.get('감마지티피')
    gender = raw_data.get('성별')
    if gender == '남성': processed_data['gender_code'] = 1
    elif gender == '여성': processed_data['gender_code'] = 2
    else: processed_data['gender_code'] = None
    processed_data['smoking_status'] = 1
    urine_protein = raw_data.get('요단백')
    if urine_protein == '정상': processed_data['urine_protein'] = 0
    else: processed_data['urine_protein'] = None
    age = raw_data.get('나이')
    if age is not None: processed_data['age_group_5yr'] = (age // 5) * 5
    else: processed_data['age_group_5yr'] = None
    height = raw_data.get('신장'); weight = raw_data.get('체중')
    if height is not None and weight is not None and height > 0: processed_data['BMI'] = weight / ((height / 100.0) ** 2)
    else: processed_data['BMI'] = None
    systolic_bp = raw_data.get('수축기 혈압'); diastolic_bp = raw_data.get('이완기 혈압')
    if systolic_bp is not None and diastolic_bp is not None: processed_data['pulse_pressure'] = systolic_bp - diastolic_bp
    else: processed_data['pulse_pressure'] = None
    ldl = processed_data.get('ldl_cholesterol'); hdl = processed_data.get('hdl_cholesterol')
    if ldl is not None and hdl is not None and hdl != 0: processed_data['ldl_hdl_ratio'] = ldl / hdl
    else: processed_data['ldl_hdl_ratio'] = None
    ggtp = processed_data.get('gamma_gtp'); alt = processed_data.get('alt')
    if ggtp is not None and alt is not None and alt != 0: processed_data['ggtp_alt_ratio'] = ggtp / alt
    else: processed_data['ggtp_alt_ratio'] = None
    triglycerides = processed_data.get('triglycerides'); hdl = processed_data.get('hdl_cholesterol')
    if triglycerides is not None and hdl is not None and hdl != 0: processed_data['triglyc_hdl_ratio'] = triglycerides / hdl
    else: processed_data['triglyc_hdl_ratio'] = None
    alt = processed_data.get('alt'); ast = raw_data.get('ast')
    if alt is not None and ast is not None and ast != 0: processed_data['alt_ast_ratio'] = alt / ast
    else: processed_data['alt_ast_ratio'] = None
    return processed_data

def prepare_model_input(processed_data, model_features_order):
    df_sample = pd.DataFrame([processed_data])
    try:
        for col in model_features_order:
            if col not in df_sample.columns: df_sample[col] = None
        df_model_input = df_sample[model_features_order]
    except KeyError as e: st.error(f"오류: 모델에 필요한 피처가 데이터에 없습니다: {e}"); st.write(f"데이터에 있는 피처: {df_sample.columns.tolist()}"); st.write(f"모델에 필요한 피처 순서: {model_features_order}"); return None
    except Exception as e: st.error(f"모델 입력 데이터 준비 중 오류 발생: {e}"); return None
    return df_model_input

def classify_risk_level(prediction_proba):
    if prediction_proba is None: return "분류 불가 (데이터 부족)"
    if prediction_proba <= 0.59: return "정상"
    elif prediction_proba <= 0.74: return "주의"
    elif prediction_proba <= 0.89: return "위험"
    else: return "고위험"

# --- 모델 학습 시 사용된 최종 피처 목록 및 순서 정의 ---
model_features_order = [
    'ggtp_alt_ratio',
    'triglyc_hdl_ratio',
    'ldl_hdl_ratio',
    'alt_ast_ratio',
    'age_group_5yr',
    'fasting_blood_glucose',
    'smoking_status',
    'pulse_pressure'
]


# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---

# --- CSS 추가 (이 페이지 전용) ---
st.markdown("""
<style>
/* 기본 앱 배경은 app.py에서 설정됨 */

/* 메인 사각형 (rectangle-116) */
.main-rectangle {
    width: 281px;
    height: 279px;
    box-shadow: 3px 6px 10px 0px rgba(0, 0, 0, 0.3);
    border-radius: 45px;
    background: #FFFFFF;
    margin-top: 118px; /* top: 118px */
    margin-left: 50px; /* left: 50px */
    position: relative; /* 내부 absolute 요소의 기준 */
    /* Streamlit의 중앙 정렬 때문에 margin-left를 auto로 변경하거나,
       상위 flex 컨테이너에서 flex-start + padding-left로 조절하는게 더 현실적 */
}

/* 하단 버튼 */
.bottom-button-style {
    width: 325px;
    height: 50px;
    border-radius: 12px;
    background: #38ADA9;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #FFFFFF;
    font-family: "Poppins", sans-serif;
    font-size: 14px;
    line-height: 16.38px;
    font-weight: 500;
    text-align: center;
    cursor: pointer;
    border: none;
    margin-top: auto; /* 하단으로 밀어냄 */
    margin-bottom: 20px; /* 하단 여백 */
}

/* 자동 조절 버튼 (auto-adjustment) */
.auto-adjustment-style {
    width: 319px;
    height: 43px;
    border-radius: 12px;
    display: flex;
    justify-content: space-between; /* 양 끝 정렬 */
    align-items: center;
    padding: 12px 15px;
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    margin-top: 40px; /* 위치 조절 */
}
.auto-adjustment-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 16px;
    line-height: 18.72px;
    font-weight: 500;
    white-space: nowrap;
}

/* 인스턴트 기능 버튼들 컨테이너 */
.instant-features-container {
    width: 325px;
    height: 85px;
    display: flex;
    flex-direction: row;
    justify-content: center; /* 가운데 정렬 */
    align-items: center;
    column-gap: 15px;
    margin-top: 40px; /* 위치 조절 */
}

/* 개별 인스턴트 기능 버튼 (cool, air, hot, eco) */
.feature-button {
    flex-shrink: 0;
    width: 70px;
    height: 85px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    row-gap: 5px;
    padding: 10px;
    background: #FFFFFF;
    border: 1px solid #EEEEEE; /* 기본 테두리 */
    box-shadow: 2px 2px 30px 0px rgba(0, 0, 0, 0.1); /* cool 버튼만 그림자 있음 */
    cursor: pointer;
}
/* cool 버튼만 그림자 유지 */
.feature-button.cool-shadow {
    box-shadow: 2px 2px 30px 0px rgba(0, 0, 0, 0.1);
}
.feature-button-text {
    color: #333333; /* cool 버튼 텍스트 색상 */
    font-family: "Poppins", sans-serif;
    font-size: 12px;
    line-height: 14.04px;
    font-weight: 500;
    text-align: center;
    white-space: nowrap;
}
/* air, hot, eco 버튼 텍스트 색상 */
.feature-button:not(.cool-shadow) .feature-button-text {
    color: #666666;
}
.feature-icon { /* 아이콘 크기 (임시) */
    width: 20px;
    height: 20px;
    object-fit: contain;
}

/* 원형 AC 컨트롤러 (ac-volume) - 복잡하므로 단순화하거나 이미지 사용 권장 */
.ac-volume-container {
    width: 219px;
    height: 214px;
    position: relative; /* 내부 요소의 절대 위치 기준 */
    margin-top: 152px; /* top: 152px */
    margin-left: auto; /* 중앙 정렬 시도 */
    margin-right: auto;
    /* 이 컨테이너는 .main-rectangle 안에 중첩될 수 있습니다. */
}
/* 내부 원들 (ellipse) - SVG 또는 이미지로 대체하는 것이 가장 좋음 */
/* HTML Div로 구현 시 매우 복잡해지며 정밀한 위치 지정 어려움 */
/* 여기서는 가장 바깥 원과 중앙 텍스트만 대략적으로 표현 */
.outer-circle {
    width: 210px;
    height: 210px;
    border-radius: 50%;
    border: 1px solid #ccc; /* 예시 */
    display: flex;
    justify-content: center;
    align-items: center;
    position: absolute; /* 이 자체는 absolute지만 부모에 대한 상대적 위치 */
    top: 0; left: 8.5px; /* 원본 left: calc(100% - 219px + 8.5px); */
}
.ac-center-text {
    color: #333333;
    font-family: "Poppins";
    font-size: 32px;
    line-height: 37.44px;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
    position: absolute;
    top: 81px; /* 원본 top */
    left: 35.5px; /* 원본 left */
    width: 155px; /* 원본 width */
    height: 38px; /* 원본 height */
    /* top, left는 .ac-volume-container 내에서의 상대 위치 */
}
.ac-small-text {
    color: #666666;
    font-family: "Poppins";
    font-size: 15px;
    line-height: 17.55px;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
    position: absolute;
}
.ac-small-text.top-left { top: 0px; left: 7.5px; }
.ac-small-text.top-right { top: 0px; left: 191px; }
.ac-small-text.bottom-left { top: 196px; left: 0px; width: 42px;}
.ac-small-text.bottom-right { top: 192px; left: 191px; }


/* 상단 메뉴 (menu) */
.top-menu-container {
    width: 325px;
    height: 45px;
    display: flex;
    flex-direction: row;
    justify-content: space-between; /* 양 끝 정렬 */
    align-items: center;
    column-gap: 15px;
    margin-top: 44px; /* top: 44px */
    margin-left: auto; /* 중앙 정렬 */
    margin-right: auto;
}
.menu-icon { /* 아이콘 크기 (임시) */
    width: 45px;
    height: 45px;
    object-fit: contain;
    cursor: pointer;
}
.menu-title-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 20px;
    line-height: 23.4px;
    font-weight: 600;
    text-align: center;
    flex-grow: 1; /* 남은 공간을 채워 중앙으로 밀어냄 */
}

</style>
""", unsafe_allow_html=True)


# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---
st.title("AC Control Panel (Design Test)")
st.write(f"환영합니다, {username}님! 에어컨 제어판 디자인을 테스트합니다.") # 로그인 정보 표시

# --- 상단 메뉴 ---
with st.container():
    col1, col2, col3 = st.columns([1, 4, 1]) # 아이콘-제목-아이콘 비율
    with col1:
        st.markdown('<div class="menu-icon">⬅️</div>', unsafe_allow_html=True) # 뒤로가기 아이콘 (임시)
    with col2:
        st.markdown('<p class="menu-title-text">Air Conditioner</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">...</div>', unsafe_allow_html=True) # 더보기 아이콘 (임시)


# --- 메인 사각형 (rectangle-116) 및 AC 볼륨 컨트롤러 ---
with st.container():
    st.markdown('<div class="main-rectangle">', unsafe_allow_html=True)

    # AC 볼륨 컨트롤러 (ac-volume) - 복잡하므로 이미지나 SVG로 대체 권장
    # 여기서는 HTML/CSS로 대략적인 모양만 시도
    st.markdown('<div class="ac-volume-container">', unsafe_allow_html=True)
    st.markdown('<div class="outer-circle"></div>', unsafe_allow_html=True)
    st.markdown('<p class="ac-center-text">24°C</p>', unsafe_allow_html=True) # 중앙 온도 텍스트 (예시)
    st.markdown('<p class="ac-small-text top-left">Off</p>', unsafe_allow_html=True) # 예시 텍스트
    st.markdown('<p class="ac-small-text top-right">Auto</p>', unsafe_allow_html=True)
    st.markdown('<p class="ac-small-text bottom-left">Low</p>', unsafe_allow_html=True)
    st.markdown('<p class="ac-small-text bottom-right">High</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # ac-volume-container 닫기

    st.markdown('</div>', unsafe_allow_html=True) # main-rectangle 닫기


# --- 자동 조절 버튼 ---
with st.container():
    st.markdown(
        """
        <div class="auto-adjustment-style">
            <p class="auto-adjustment-text">Auto Adjustment</p>
            <div>🎛️</div> </div>
        """,
        unsafe_allow_html=True,
    )

# --- 인스턴트 기능 버튼들 ---
with st.container():
    st.markdown('<div class="instant-features-container">', unsafe_allow_html=True)
    
    # Cool 버튼
    st.markdown(
        """
        <div class="feature-button cool-shadow">
            <div>❄️</div> <p class="feature-button-text">Cool</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Air 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>💨</div> <p class="feature-button-text">Air</p>
        </div>
        """, unsafe_allow_html=True)

    # Hot 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>🔥</div> <p class="feature-button-text">Hot</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Eco 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>🌱</div> <p class="feature-button-text">Eco</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # instant-features-container 닫기


# --- 하단 버튼 (Save Changes) ---
# st.button을 사용하면 Streamlit 위젯 기능을 쉽게 연결 가능
if st.button("Save Changes", key="save_changes_button", use_container_width=True):
    st.success("변경 사항이 저장되었습니다!")

# --- 기타 앱 정보 (필요시) ---
st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")

# 로그아웃 버튼 (선택 사항)
if logged_in:
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun() # 로그아웃 후 페이지 다시 로드
