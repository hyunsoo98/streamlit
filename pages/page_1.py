import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np
from joblib import load # 모델 로드를 위해 joblib 임포트

# st.set_page_config는 app.py에서 이미 호출되었으므로 여기서는 제거합니다.
# st.set_page_config(page_title="이미지 건강 데이터 추출 및 분석", layout="centered")

# --- Vision API 클라이언트와 임시 인증 파일 경로를 session_state에서 가져오기 ---
# app.py에서 초기화된 client를 사용합니다.
vision_client = st.session_state.get('vision_client')
temp_credentials_path = st.session_state.get('temp_credentials_path')

# 클라이언트가 제대로 초기화되지 않았을 경우 오류 메시지 표시
if vision_client is None:
    st.error("Google Cloud Vision API 클라이언트가 초기화되지 않았습니다. 메인 페이지를 확인하거나 앱을 다시 시작해주세요.")
    st.stop()

# --- DB 설정 및 함수 (이미지 처리 결과 저장용) - 제거됨 ---
# 이 부분은 이 요청에서 필요하지 않으므로 제거합니다.
# DB_FILE_IMAGE_RESULTS = "image_results.db"
# def init_image_results_db(): ...
# def save_image_result(...): ...
# if 'image_results_db_initialized' not in st.session_state: ...

# --- Creatie.ai CSS 적용 시작 - 제거됨 ---
# app.py에서 전역적으로 CSS를 적용하므로 여기서는 제거합니다.
# def apply_creatie_css(): ...
# apply_creatie_css()

# Google Cloud 인증 정보 설정 (이미 app.py에서 처리되었으므로 여기서는 제거)
# try: ... except Exception as e: ...
# client = get_vision_client() (-> vision_client로 변경되었고, app.py에서 가져옴)

# --- 텍스트 파싱 함수 ---
def parse_health_data_from_ocr(text):
    data = {}

    # 나이 및 성별 파싱
    age_gender_match = re.search(r'나이성별\s*(\d+)\s*(여성|남성)', text)
    if age_gender_match:
        data['나이'] = int(age_gender_match.group(1))
        data['성별'] = age_gender_match.group(2).strip()
    else:
        data['나이'] = None
        data['성별'] = None

    # 키 및 몸무게 파싱 (괄호 이스케이프 수정)
    height_weight_match = re.search(r'키\(cm\)/몸무게\(kg\)\s*(\d+)\(cm\)/(\d+)\(kg\)', text)
    if height_weight_match:
        data['신장'] = int(height_weight_match.group(1))
        data['체중'] = int(height_weight_match.group(2))
    else:
        data['신장'] = None
        data['체중'] = None

    # 혈압 파싱 (고혈압' 키워드를 포함하지 않고 패턴 찾기)
    bp_match = re.search(r'(\d+)/(\d+)\s*mmHg', text)
    if bp_match:
        data['수축기 혈압'] = int(bp_match.group(1))
        data['이완기 혈압'] = int(bp_match.group(2))
    else:
        data['수축기 혈압'] = None
        data['이완기 혈압'] = None

    patterns = {
        '혈색소': r'혈색소\(g/dL\)\s*(\d+(\.\d+)?)',
        '공복 혈당': r'공복혈당\(mg/dL\)\s*(\d+(\.\d+)?)',
        '총 콜레스테롤': r'총콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)',
        'HDL 콜레스테롤': r'고밀도 콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)',
        '트리글리세라이드': r'중성지방\(mg/dL\)\s*(\d+(\.\d+)?)',
        'LDL 콜레스테롤': r'저밀도 콜레스테롤\(mg/dL\)\s*(\d+(\.\d+)?)',
        '혈청 크레아티닌': r'혈청 크레아티닌\(mg/dL\)\s*(\d+(\.\d+)?)',
        'AST': r'AST\(SGOT\)\(IU/L\)\s*(\d+(\.\d+)?)',
        'ALT': r'ALT\(SGPT\)\(IU/L\)\s*(\d+(\.\d+)?)',
        '감마지티피': r'감마지티피\(XGTP\)\(IU/L\)\s*(\d+(\.\d+)?)',
        '요단백': r'요단백\s*([가-힣]+)',
        '흡연 상태': None,
        '음주 여부': None
    }

    for key, pattern in patterns.items():
        if pattern is None:
            data[key] = None
            continue

        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            value_str = match.group(1)
            try:
                data[key] = float(value_str)
            except ValueError:
                data[key] = value_str.strip()
            except IndexError:
                try:
                    start_index = match.end()
                    rest_of_text = text[start_index:].splitlines()[0].strip()
                    num_match = re.search(r'\d+(\.\d+)?', rest_of_text)
                    if num_match:
                        data[key] = float(num_match.group(0))
                    else:
                        data[key] = None
                except Exception:
                    data[key] = None
        else:
            data[key] = None
    return data

# --- 피처 엔지니어링 및 전처리 함수 ---
def preprocess_and_engineer_features(raw_data):
    processed_data = {}

    processed_data['식전혈당(공복혈당)'] = raw_data.get('공복 혈당')
    processed_data['총콜레스테롤'] = raw_data.get('총 콜레스테롤')
    processed_data['혈색소'] = raw_data.get('혈색소')
    processed_data['혈청크레아티닌'] = raw_data.get('혈청 크레아티닌')
    processed_data['감마지티피'] = raw_data.get('감마지티피')
    processed_data['요단백'] = raw_data.get('요단백')

    gender = raw_data.get('성별')
    if gender == '남성':
        processed_data['성별코드'] = 1
    elif gender == '여성':
        processed_data['성별코드'] = 2
    else:
        processed_data['성별코드'] = np.nan

    processed_data['흡연상태'] = 1 # 예시로 비흡연자(1) 설정

    age = raw_data.get('나이')
    if age is not None:
        processed_data['연령대코드(5세단위)'] = (age // 5) * 5
    else:
        processed_data['연령대코드(5세단위)'] = np.nan

    # 시력(평균)은 OCR에서 추출되지 않으므로 NaN 처리
    processed_data['시력(평균)'] = np.nan

    height = raw_data.get('신장')
    weight = raw_data.get('체중')
    if height is not None and weight is not None and height > 0:
        processed_data['bmi'] = weight / ((height / 100.0) ** 2)
    else:
        processed_data['bmi'] = np.nan

    # 파생 변수 계산
    alt = processed_data.get('alt') if processed_data.get('alt') is not None else raw_data.get('ALT')
    ast = processed_data.get('ast') if processed_data.get('ast') is not None else raw_data.get('AST')
    if alt is not None and ast is not None and ast != 0:
        processed_data['alt_ast_ratio'] = alt / ast
    else:
        processed_data['alt_ast_ratio'] = np.nan

    triglycerides = processed_data.get('triglycerides') if processed_data.get('triglycerides') is not None else raw_data.get('트리글리세라이드')
    hdl = processed_data.get('hdl_cholesterol') if processed_data.get('hdl_cholesterol') is not None else raw_data.get('HDL 콜레스테롤')
    if triglycerides is not None and hdl is not None and hdl != 0:
        processed_data['tg_hdl_ratio'] = triglycerides / hdl
    else:
        processed_data['tg_hdl_ratio'] = np.nan

    ggtp = processed_data.get('gamma_gtp') if processed_data.get('gamma_gtp') is not None else raw_data.get('감마지티피')
    alt = processed_data.get('alt') if processed_data.get('alt') is not None else raw_data.get('ALT')
    if ggtp is not None and alt is not None and alt != 0:
        processed_data['ggtp_alt_ratio'] = ggtp / alt
    else:
        processed_data['ggtp_alt_ratio'] = np.nan

    ldl = processed_data.get('ldl_cholesterol') if processed_data.get('ldl_cholesterol') is not None else raw_data.get('LDL 콜레스테롤')
    hdl = processed_data.get('hdl_cholesterol') if processed_data.get('hdl_cholesterol') is not None else raw_data.get('HDL 콜레스테롤')
    if ldl is not None and hdl is not None and hdl != 0:
        processed_data['ldl_hdl_ratio'] = ldl / hdl
    else:
        processed_data['ldl_hdl_ratio'] = np.nan

    # `04_modeling.ipynb`의 `df.columns`에서 확인된 피처 리스트 (타겟 제외)
    required_features_from_notebook = [
        '성별코드', '연령대코드(5세단위)', '시력(평균)', '식전혈당(공복혈당)', '총콜레스테롤', '혈색소', '요단백',
        '혈청크레아티닌', '감마지티피', '흡연상태', '음주여부', 'bmi', 'alt_ast_ratio',
        'tg_hdl_ratio', 'ggtp_alt_ratio', 'ldl_hdl_ratio'
    ]

    for feature in required_features_from_notebook:
        if feature not in processed_data:
            if feature == '요단백':
                processed_data[feature] = None
            elif feature == '음주여부':
                processed_data[feature] = None
            else:
                processed_data[feature] = np.nan

    # '요단백' 값을 모델에 맞게 변환 (정상 -> 0)
    if processed_data.get('요단백') == '정상':
        processed_data['요단백'] = 0
    else:
        processed_data['요단백'] = np.nan

    return processed_data

def prepare_model_input(processed_data, model_features_order):
    df_sample = pd.DataFrame([processed_data])

    try:
        # 04_modeling.ipynb의 `numeric_features` 정의를 참고하여 컬럼 선택
        # 이들은 StandardScaler를 통과하는 피처들입니다.
        numeric_features = [
            '연령대코드(5세단위)', '시력(평균)', '식전혈당(공복혈당)', '혈색소', '요단백',
            '혈청크레아티닌', '감마지티피', 'bmi', 'alt_ast_ratio', 'tg_hdl_ratio',
            'ggtp_alt_ratio', 'ldl_hdl_ratio'
        ]

        df_model_input = df_sample[numeric_features].copy()

        for col in df_model_input.columns:
            df_model_input[col] = pd.to_numeric(df_model_input[col], errors='coerce')

        return df_model_input

    except KeyError as e:
        st.error(f"오류: 모델에 필요한 피처가 데이터에 없습니다: {e}")
        st.write(f"데이터에 있는 피처: {df_sample.columns.tolist()}")
        st.write(f"예상되는 피처 순서 (numeric_features): {model_features_order}")
        return None
    except Exception as e:
        st.error(f"모델 입력 데이터 준비 중 오류 발생: {e}")
        return None

def classify_risk_level(prediction_proba):
    if prediction_proba is None:
        return "분류 불가"

    # 04_modeling.ipynb에서 Threshold 0.48로 조정되었으므로, 이를 반영하여 분류
    # 이 분류 로직은 예측 확률을 4단계로 나누는 것이므로, 0.48은 '정상'과 '주의'를 나누는 기준으로만 적용
    if prediction_proba < 0.48:
        return "정상"
    elif prediction_proba <= 0.59:
        return "주의"
    elif prediction_proba <= 0.74:
        return "위험"
    else:
        return "고위험"

# 모델 학습 시 사용된 최종 피처 목록 및 순서는 `prepare_model_input` 내 `numeric_features`에 명시됨
# 이 변수는 이제 사용되지 않으므로 제거합니다.
# model_features_order = [...]


# --- Streamlit 앱 메인 로직 ---
st.title("Google Cloud Vision API를 이용한 이미지 건강 데이터 추출 및 분석")
st.write("건강검진 결과 이미지를 업로드하면 Vision API로 텍스트를 추출하고, 추출된 데이터를 분석하여 고혈압 위험도를 예측합니다.")
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

# 모델 및 스케일러 로드 (앱 시작 시 한 번만 로드하도록 캐시)
@st.cache_resource
def load_prediction_assets():
    model_path = 'model/logistic_model.pkl'
    scaler_path = 'model/scaler.pkl'

    loaded_model = None
    loaded_scaler = None

    if os.path.exists(model_path) and os.path.exists(scaler_path):
        try:
            loaded_model = load(model_path)
            loaded_scaler = load(scaler_path)
            st.success(f"모델({model_path}) 및 스케일러({scaler_path})가 성공적으로 로드되었습니다.")
            return loaded_model, loaded_scaler
        except Exception as e:
            st.error(f"모델 또는 스케일러 로드 중 오류 발생: {e}")
            st.warning("모델/스케일러 파일이 손상되었거나 호환되지 않는 버전으로 저장되었을 수 있습니다.")
            return None, None
    else:
        st.warning(f"모델 또는 스케일러 파일을 찾을 수 없습니다. 모델: {model_path}, 스케일러: {scaler_path}")
        st.write("모델/스케일러 파일 경로를 확인하고 앱과 같은 위치 또는 접근 가능한 경로에 두세요.")
        return None, None

loaded_model, loaded_scaler = load_prediction_assets()

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

        if texts and texts.text:
            st.subheader("1. Vision API 추출 텍스트:")
            st.text_area("추출된 원본 텍스트", texts.text, height=300)

            st.subheader("2. 텍스트 파싱 결과:")
            raw_health_data = parse_health_data_from_ocr(texts.text)
            st.json(raw_health_data)

            st.subheader("3. 데이터 전처리 및 피처 엔지니어링 결과:")
            processed_health_data = preprocess_and_engineer_features(raw_health_data)
            st.json(processed_health_data)

            st.subheader("4. 모델 입력 데이터 준비:")
            # model_features_order 변수 제거
            model_input_df = prepare_model_input(processed_health_data, []) # model_features_order는 이제 prepare_model_input 내부에서 정의

            if model_input_df is not None and not model_input_df.empty: # DataFrame이 비어있지 않은지 확인
                st.dataframe(model_input_df)

                st.subheader("5. 고혈압 위험 예측:")
                if loaded_model is not None and loaded_scaler is not None:
                    try:
                        scaled_input = loaded_scaler.transform(model_input_df)
                        prediction_proba = loaded_model.predict_proba(scaled_input)[:, 1]
                        st.write(f"예측된 고혈압 확률: **{prediction_proba[0]:.4f}**")

                        risk_level = classify_risk_level(prediction_proba[0])
                        st.write(f"고혈압 위험 등급: **{risk_level}**")

                        # 예측 결과를 session_state에 저장하여 page_2.py로 전달
                        st.session_state['prediction_proba'] = prediction_proba[0]
                        st.session_state['risk_level'] = risk_level

                        st.page_link("pages/page_2.py", label="결과 보기", icon="📈")

                    except Exception as e:
                        st.error(f"모델 예측 중 오류 발생: {e}")
                        st.warning("모델 입력 데이터의 형식이나 피처가 모델의 기대치와 다를 수 있습니다.")
                else:
                    st.warning("모델 또는 스케일러가 로드되지 않아 예측을 수행할 수 없습니다.")
            else:
                st.warning("모델 입력 데이터 준비 실패 또는 데이터가 비어있습니다. 예측을 수행할 수 없습니다.")
        else:
            st.info("이미지에서 텍스트를 찾을 수 없습니다.")

        if response.error.message:
            st.error(f"Vision API 오류 발생: {response.error.message}")

    except Exception as e:
        st.error(f"텍스트 추출 또는 데이터 처리 중 오류 발생: {e}")

st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# 임시 인증 파일 삭제 (app.py에서 처리되므로 여기서는 제거)
# if temp_credentials_path and os.path.exists(temp_credentials_path): ...
