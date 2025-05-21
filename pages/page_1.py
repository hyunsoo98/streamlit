import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np
import sqlite3 # DB 사용을 위해 sqlite3 임포트

# --- Vision API 클라이언트와 임시 인증 파일 경로를 session_state에서 가져오기 ---
vision_client = st.session_state.get('vision_client')
temp_credentials_path = st.session_state.get('temp_credentials_path')

# 클라이언트가 제대로 초기화되지 않았을 경우 오류 메시지 표시
if vision_client is None:
    st.error("Google Cloud Vision API 클라이언트가 초기화되지 않았습니다. 메인 페이지를 확인하거나 앱을 다시 시작해주세요.")
    st.stop()


# --- DB 설정 및 함수 (이미지 처리 결과 저장용) ---
# 예시: 이미지 처리 결과를 저장할 테이블
# 사용자 데이터베이스와 분리되어야 합니다.
DB_FILE_IMAGE_RESULTS = "image_results.db"

def init_image_results_db():
    """이미지 처리 결과를 저장할 데이터베이스를 초기화합니다."""
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
    """이미지 처리 결과를 데이터베이스에 저장합니다."""
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

# 앱 시작 시 DB 초기화 (한 번만 실행되도록)
if 'image_results_db_initialized' not in st.session_state:
    init_image_results_db()
    st.session_state.image_results_db_initialized = True
# -----------------------------------------------


# --- vision_ai.ipynb 노트북에서 가져온 함수들 ---
# (이전 page_1.py에 있던 함수들 그대로 유지)
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
st.title("Google Cloud Vision API를 이용한 이미지 건강 데이터 추출 및 분석")
st.write("건강검진 결과 이미지를 업로드하면 Vision API로 텍스트를 추출하고, 추출된 데이터를 분석하여 고혈압 위험도를 예측합니다.")
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

# 이미지 업로드 위젯
uploaded_file = st.file_uploader("건강검진 결과 이미지를 선택하세요...", type=["jpg", "jpeg", "png", "gif", "bmp"])

# 이미지가 업로드되면 처리 시작
if uploaded_file is not None and vision_client is not None:
    # 업로드된 이미지 표시
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

                # 예시: 모델 로드 (주석 처리)
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

                # 이미지 처리 결과 DB에 저장 (예시)
                # 예측 결과가 있다면 저장
                if "prediction_proba" in locals(): # prediction_proba 변수가 정의되었다면
                    if save_image_result(uploaded_file.name, texts.text, raw_health_data, prediction_proba[0], risk_level):
                        st.success("이미지 분석 결과가 데이터베이스에 저장되었습니다.")
                    else:
                        st.error("이미지 분석 결과 저장에 실패했습니다.")

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
