import streamlit as st
import sqlite3
import hashlib # For SHA256 (consider bcrypt for production)
import bcrypt # Recommended for secure password hashing
import os
import json # For Google Cloud Vision API related setup

# --- DB 설정 및 함수 ---
DB_FILE = "users.db" # User database file (should be in the root directory)

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def hash_password_bcrypt(password):
    """Hashes the password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password_bcrypt(password, stored_hash):
    """Verifies the input password against the stored bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

def register_user(username, password):
    """Registers a new user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        password_hash = hash_password_bcrypt(password)
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # User already exists
    finally:
        conn.close()

def login_user(username, password):
    """Handles user login."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        stored_hash = result[0]
        return verify_password_bcrypt(password, stored_hash)
    return False

# Initialize DB when this page is loaded (or first time app is run)
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False

# --- Login/Signup Page Content ---

if not st.session_state.logged_in: # Display login/signup form if not logged in
    # Top logo (re-using CSS from app.py)
    st.markdown('<div class="top-logo-container" style="margin-top: 100px; margin-bottom: 20px;">', unsafe_allow_html=True)
    # The carebite logo image should ideally be in a central place if used here.
    # For now, just display the 'CareBite' text.
    st.markdown('<p class="smartly-text">CareBite</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Bottom card
    st.markdown('<div class="card-container">', unsafe_allow_html=True)

    if not st.session_state.show_signup: # Login Form
        st.markdown('<p class="card-title-text">Log in your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        username_input = st.text_input("", placeholder="Enter your email", key="login_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        password_input = st.text_input("", type="password", placeholder="Enter your password", key="login_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) # Close form-container

        if st.button("Sign In", use_container_width=True, key="signin_button"):
            if login_user(username_input, password_input):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.success(f"환영합니다, {username_input}님!")
                # Navigate to page_2.py upon successful login
                st.switch_page("pages/page_2.py") # Direct switch
            else:
                st.error("잘못된 사용자 이름 또는 비밀번호입니다.")

        # "Don't have an account?" link
        st.markdown(
            """
            <div class="signup-text-container">
                <p class="signup-text">Don’t have an account? <a href="#" onclick="Streamlit.setSessionState({'show_signup': true})" class="signup-link">Sign Up</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="or-separator-container">
                <div class="line"></div>
                <p class="sign-in-with-text">Sign in with</p>
                <div class="line"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Social login buttons (placeholders for now)
        st.markdown('<div class="social-login-buttons">', unsafe_allow_html=True)
        # You'll need to handle image loading (e.g., base64 encoding from app.py or direct web URL)
        # For now, using text placeholders.
        st.markdown('<div class="social-icon-button">F</div>', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button">G</div>', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button">A</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else: # Signup Form
        st.markdown('<p class="card-title-text">Create your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        signup_username_input = st.text_input("", placeholder="Enter your email", key="signup_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        signup_password_input = st.text_input("", type="password", placeholder="Create a password", key="signup_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Sign Up", use_container_width=True, key="signup_button"):
            if register_user(signup_username_input, signup_password_input):
                st.success("회원가입이 성공했습니다! 이제 로그인해주세요.")
                st.session_state.show_signup = False # Switch to login form
                st.rerun() # Rerun to display login form
            else:
                st.error("회원가입에 실패했습니다. 사용자 이름이 이미 존재할 수 있습니다.")

        # "Already have an account?" link
        st.markdown(
            """
            <div class="signup-text-container">
                <p class="signup-text">Already have an account? <a href="#" onclick="Streamlit.setSessionState({'show_signup': false})" class="signup-link">Sign In</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True) # Close card-container

else: # Already logged in on this page
    st.success(f"이미 로그인되어 있습니다, {st.session_state.username}님! 이미지 분석 페이지로 이동합니다.")
    st.info("잠시 후 이미지 분석 페이지로 자동 이동합니다.")
    st.switch_page("pages/page_2.py") # Automatically switch to page_2.py

# No need to manage temp_credentials_path here, it's handled in app.py
3. pages/page_2.py (이미지 분석 페이지) 내용:

이 파일은 이제 로그인 후 사용자가 접근하는 핵심 기능 페이지가 됩니다. st.session_state를 통해 로그인 상태를 확인하고, 로그인되지 않았다면 로그인 페이지로 리디렉션하는 로직을 추가하는 것이 좋습니다.

Python

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

# --- 로그인 확인 및 리디렉션 로직 ---
if not logged_in:
    st.warning("로그인이 필요한 페이지입니다. 로그인 페이지로 이동해주세요.")
    st.page_link("pages/page_1.py", label="로그인 페이지로 이동")
    st.stop() # Stop execution if not logged in
elif vision_client is None:
    st.error("Google Cloud Vision API 클라이언트가 초기화되지 않았습니다. 메인 페이지를 확인하거나 앱을 다시 시작해주세요.")
    st.stop()


# --- vision_ai.ipynb 노트북에서 가져온 함수들 (여기에 그대로 붙여넣어야 함) ---
# 이 함수들은 이전 page_1.py (현재 page_2.py)에 있던 내용 그대로입니다.
def parse_health_data_from_ocr(text):
    data = {}
    age_gender_match = re.search(r'나이성별\s*(\d+)\s*(여성|남성)', text)
    if age_gender_match:
        data['나이'] = int(age_gender_match.group(1)); data['성별'] = age_gender_match.group(2).strip()
    else: data['나이'] = None; data['성별'] = None
    height_weight_match = re.search(r'키\\(cm\\)/몸무게\\(kg\\)\\s*(\\d+)\\(cm\\)/(\\d+)\\(kg\\)', text)
    if height_weight_match:
        data['신장'] = int(height_weight_match.group(1)); data['체중'] = int(height_weight_match.group(2))
    else: data['신장'] = None; data['체중'] = None
    bp_match = re.search(r'고혈압\s*(\d+)/(\d+)\s*mmHg', text)
    if bp_match:
        data['수축기 혈압'] = int(bp_match.group(1)); data['이완기 혈압'] = int(bp_match.group(2))
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
    processed_data['triglycerides'] = raw_data.get('트리글리세라이드'); processed_data['hdl_cholesterol'] = raw_data.get('HDL 콜레스테롤')
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

model_features_order = [
    'ggtp_alt_ratio', 'triglyc_hdl_ratio', 'ldl_hdl_ratio', 'alt_ast_ratio',
    'age_group_5yr', 'fasting_blood_glucose', 'smoking_status', 'pulse_pressure'
]

# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---
st.title("Google Cloud Vision API를 이용한 이미지 건강 데이터 추출 및 분석")
st.write(f"환영합니다, {username}님! 건강검진 결과 이미지를 업로드하여 분석할 수 있습니다.") # 로그인 정보 표시
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

# 이미지 업로드 위젯
uploaded_file = st.file_uploader("건강검진 결과 이미지를 선택하세요...", type=["jpg", "jpeg", "png", "gif", "bmp"])

# 이미지가 업로드되면 처리 시작
if uploaded_file is not None and vision_client is not None:
    st.image(uploaded_file, caption="업로드된 이미지", use_column_width=True)
    st.write("텍스트 추출 중...")

    try:
        image_content = uploaded_file.read()
        image = vision.Image(content=image_content)
        response = vision_client.document_text_detection(image=image)
        texts = response.full_text_annotation

        if texts:
            st.subheader("1. Vision API 추출 텍스트:")
            st.text_area("추출된 원본 텍스트", texts.text, height=300)
            st.subheader("2. 텍스트 파싱 결과:")
            raw_health_data = parse_health_data_from_ocr(texts.text)
            st.json(raw_health_data)
            st.subheader("3. 데이터 전처리 및 피처 엔지니어링 결과:")
            processed_health_data = preprocess_and_engineer_features(raw_health_data)
            st.json(processed_health_data)
            st.subheader("4. 모델 입력 데이터 준비:")
            model_input_df = prepare_model_input(processed_health_data, model_features_order)

            if model_input_df is not None:
                st.dataframe(model_input_df)
                st.subheader("5. 고혈압 위험 예측:")
                st.write("모델 로드 및 예측 코드는 현재 주석 처리되어 있습니다.")
                st.write("학습된 모델 파일을 로드하고 `predict_proba` 메서드를 사용하여 예측을 수행하세요.")
                st.write("예측 결과(확률)에 따라 아래 `classify_risk_level` 함수를 호출하여 위험 등급을 표시할 수 있습니다.")

                # 모델 로드 및 예측 (주석 처리)
                # try:
                #     from joblib import load
                #     model_path = 'path/to/your/best_hypertension_model.joblib'
                #     if os.path.exists(model_path):
                #         loaded_model = load(model_path)
                #         st.success("모델 파일이 성공적으로 로드되었습니다.")
                #         prediction_proba = loaded_model.predict_proba(model_input_df)[:, 1]
                #         st.write(f"예측된 고혈압 확률: **{prediction_proba[0]:.4f}**")
                #         risk_level = classify_risk_level(prediction_proba[0])
                #         st.write(f"고혈압 위험 등급: **{risk_level}**")
                #     else:
                #         st.warning(f"모델 파일을 찾을 수 없습니다: {model_path}")
                # except Exception as e:
                #     st.error(f"모델 로드 또는 예측 중 오류 발생: {e}")
            else:
                st.warning("모델 입력 데이터 준비 실패. 예측을 수행할 수 없습니다.")
        else:
            st.info("이미지에서 텍스트를 찾을 수 없습니다.")

        if response.error.message:
            st.error(f"Vision API 오류 발생: {response.error.message}")
    except Exception as e:
        st.error(f"텍스트 추출 또는 데이터 처리 중 오류 발생: {e}")

st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# 로그아웃 버튼
if logged_in:
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun() # 로그아웃 후 페이지 다시 로드
