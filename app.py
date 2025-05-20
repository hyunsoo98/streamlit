import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np
from joblib import load # 모델 로드를 위해 joblib 임포트

# 페이지 설정
st.set_page_config(page_title="이미지 건강 데이터 추출 및 분석", layout="centered")

st.title("Google Cloud Vision API를 이용한 이미지 건강 데이터 추출 및 분석")
st.write("건강검진 결과 이미지를 업로드하면 Vision API로 텍스트를 추출하고, 추출된 데이터를 분석하여 고혈압 위험도를 예측합니다.")
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

# 임시 인증 파일 경로 초기화 (try 블록 외부에서 정의)
temp_credentials_path = None
vision_client = None # Vision API 클라이언트 초기화

# Google Cloud 인증 정보 설정
# Streamlit secrets를 사용하여 안전하게 관리합니다.
# .streamlit/secrets.toml 파일에 Google Cloud 서비스 계정 정보가 설정되어 있어야 합니다.
try:
    # secrets.toml에서 Google Cloud 서비스 계정 정보 로드
    google_cloud_settings = st.secrets["google_cloud"]

    # 인증 정보 JSON 문자열 생성
    google_credentials_json = json.dumps({
        "type": google_cloud_settings["type"],
        "project_id": google_cloud_settings["project_id"],
        "private_key_id": google_cloud_settings["private_key_id"],
        "private_key": google_cloud_settings["private_key"],
        "client_email": google_cloud_settings["client_email"],
        "client_id": google_cloud_settings["client_id"],
        "auth_uri": google_cloud_settings["auth_uri"],
        "token_uri": google_cloud_settings["token_uri"],
        "auth_provider_x509_cert_url": google_cloud_settings["auth_provider_x509_cert_url"],
        "client_x509_cert_url": google_cloud_settings["client_x509_cert_url"],
        "universe_domain": google_cloud_settings["universe_domain"]
    })

    # 임시 파일에 인증 정보 저장 (Vision API 클라이언트가 읽을 수 있도록)
    temp_credentials_path = "temp_credentials.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_credentials_path
    with open(temp_credentials_path, "w") as f:
        f.write(google_credentials_json)

    # Vision API 클라이언트 초기화
    @st.cache_resource
    def get_vision_client():
        """Vision API 클라이언트를 초기화하고 캐시합니다."""
        return vision.ImageAnnotatorClient()

    vision_client = get_vision_client()
    st.success("Google Cloud Vision API 클라이언트가 성공적으로 초기화되었습니다.")

except Exception as e:
    st.error(f"Google Cloud 인증 정보를 로드하는 데 실패했습니다. `.streamlit/secrets.toml` 파일을 확인해주세요: {e}")
    # 초기화 실패 시 vision_client는 None 상태 유지

# --- vision_ai.ipynb 노트북에서 가져온 함수들 ---

def parse_health_data_from_ocr(text):
    """
    OCR 추출 텍스트에서 건강 지표 및 개인 정보를 파싱합니다.
    이 함수는 제공된 OCR 텍스트 형식에 맞춰 작성되었습니다.
    실제 사용 시에는 다양한 OCR 결과 및 문서 형식을 고려하여 수정해야 합니다.
    """
    data = {}

    # 나이 및 성별 파싱 (예: "나이성별45여성" 패턴 수정)
    age_gender_match = re.search(r'나이성별\s*(\d+)\s*(여성|남성)', text)
    if age_gender_match:
        data['나이'] = int(age_gender_match.group(1))
        data['성별'] = age_gender_match.group(2).strip()
    else:
        data['나이'] = None
        data['성별'] = None

    # 키 및 몸무게 파싱 (예: "155(cm)/70(kg)" 패턴)
    # 정규표현식에서 백슬래시를 두 번 사용하여 이스케이프해야 합니다.
    height_weight_match = re.search(r'키\\(cm\\)/몸무게\\(kg\\)\\s*(\\d+)\\(cm\\)/(\\d+)\\(kg\\)', text)
    if height_weight_match:
        data['신장'] = int(height_weight_match.group(1))
        data['체중'] = int(height_weight_match.group(2))
    else:
        data['신장'] = None
        data['체중'] = None

    # 혈압 파싱 (예: "139/89 mmHg" 패턴)
    bp_match = re.search(r'고혈압\s*(\d+)/(\d+)\s*mmHg', text)
    if bp_match:
        data['수축기 혈압'] = int(bp_match.group(1))
        data['이완기 혈압'] = int(bp_match.group(2))
    else:
        data['수축기 혈압'] = None
        data['이완기 혈압'] = None

    # 기타 혈액 검사 및 기능 검사 결과 파싱
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
                # 그룹이 하나만 있는 경우 (값만 있는 경우)
                try:
                    value_str = text[match.end():].splitlines()[0].strip()
                    num_match = re.search(r'\d+(\.\d+)?', value_str)
                    if num_match:
                        data[key] = float(num_match.group(0))
                    else:
                        data[key] = value_str
                except Exception:
                    data[key] = None
        else:
            data[key] = None

    return data

def preprocess_and_engineer_features(raw_data):
    """
    파싱된 원시 데이터를 모델 입력에 맞는 피처로 변환하고 파생 변수를 계산합니다.
    hypertension.ipynb 모델의 최종 피처 목록 및 변환 방식을 따라야 합니다.
    """
    processed_data = {}

    # --- 기본 피처 변환 및 매핑 ---
    processed_data['fasting_blood_glucose'] = raw_data.get('공복 혈당')
    processed_data['total_cholesterol'] = raw_data.get('총 콜레스테롤')
    processed_data['triglycerides'] = raw_data.get('트리글리세라이드')
    processed_data['hdl_cholesterol'] = raw_data.get('HDL 콜레스테롤')
    processed_data['ldl_cholesterol'] = raw_data.get('LDL 콜레스테롤')
    processed_data['hemoglobin'] = raw_data.get('혈색소')
    processed_data['serum_creatinine'] = raw_data.get('혈청 크레아티닌')
    processed_data['ast'] = raw_data.get('AST')
    processed_data['alt'] = raw_data.get('ALT')
    processed_data['gamma_gtp'] = raw_data.get('감마지티피')

    # 범주형 피처 변환
    gender = raw_data.get('성별')
    if gender == '남성':
        processed_data['gender_code'] = 1
    elif gender == '여성':
        processed_data['gender_code'] = 2
    else:
        processed_data['gender_code'] = None

    processed_data['smoking_status'] = 1 # 예시: 비흡연자 (실제 추출 필요)

    urine_protein = raw_data.get('요단백')
    if urine_protein == '정상':
        processed_data['urine_protein'] = 0
    else:
        processed_data['urine_protein'] = None

    age = raw_data.get('나이')
    if age is not None:
        processed_data['age_group_5yr'] = (age // 5) * 5
    else:
        processed_data['age_group_5yr'] = None

    # --- 파생 변수 계산 ---
    height = raw_data.get('신장')
    weight = raw_data.get('체중')
    if height is not None and weight is not None and height > 0:
        processed_data['BMI'] = weight / ((height / 100.0) ** 2)
    else:
        processed_data['BMI'] = None

    systolic_bp = raw_data.get('수축기 혈압')
    diastolic_bp = raw_data.get('이완기 혈압')
    if systolic_bp is not None and diastolic_bp is not None:
        processed_data['pulse_pressure'] = systolic_bp - diastolic_bp
    else:
        processed_data['pulse_pressure'] = None

    ldl = processed_data.get('ldl_cholesterol')
    hdl = processed_data.get('hdl_cholesterol')
    if ldl is not None and hdl is not None and hdl != 0:
        processed_data['ldl_hdl_ratio'] = ldl / hdl
    else:
        processed_data['ldl_hdl_ratio'] = None

    ggtp = processed_data.get('gamma_gtp')
    alt = processed_data.get('alt')
    if ggtp is not None and alt is not None and alt != 0:
        processed_data['ggtp_alt_ratio'] = ggtp / alt
    else:
        processed_data['ggtp_alt_ratio'] = None

    triglycerides = raw_data.get('triglycerides')
    hdl = processed_data.get('hdl_cholesterol')
    if triglycerides is not None and hdl is not None and hdl != 0:
        processed_data['triglyc_hdl_ratio'] = triglycerides / hdl
    else:
        processed_data['triglyc_hdl_ratio'] = None

    alt = processed_data.get('alt')
    ast = raw_data.get('ast')
    if alt is not None and ast is not None and ast != 0:
        processed_data['alt_ast_ratio'] = alt / ast
    else:
        processed_data['alt_ast_ratio'] = None

    return processed_data

def prepare_model_input(processed_data, model_features_order):
    """
    처리된 데이터를 모델 입력에 맞는 DataFrame 형태로 변환하고 피처 순서를 맞춥니다.
    """
    df_sample = pd.DataFrame([processed_data])

    try:
        for col in model_features_order:
            if col not in df_sample.columns:
                df_sample[col] = np.nan # 또는 None (모델의 결측치 처리 방식에 따름)

        df_model_input = df_sample[model_features_order]

    except KeyError as e:
        st.error(f"오류: 모델에 필요한 피처가 데이터에 없습니다: {e}")
        st.write(f"데이터에 있는 피처: {df_sample.columns.tolist()}")
        st.write(f"모델에 필요한 피처 순서: {model_features_order}")
        return None
    except Exception as e:
        st.error(f"모델 입력 데이터 준비 중 오류 발생: {e}")
        return None

    return df_model_input

def classify_risk_level(prediction_proba):
    """
    모델의 예측 확률(0~1)을 4단계 고혈압 위험 등급으로 분류합니다.
    """
    if prediction_proba is None:
        return "분류 불가 (데이터 부족)"

    if prediction_proba <= 0.59:
        return "정상"
    elif prediction_proba <= 0.74:
        return "주의"
    elif prediction_proba <= 0.89:
        return "위험"
    else:
        return "고위험"

# --- 모델 학습 시 사용된 최종 피처 목록 및 순서 정의 ---
# 'selected_features_final_pruned' 리스트를 참고했습니다.
# 이 리스트는 실제 모델 학습에 사용된 피처 순서와 정확히 일치해야 합니다.
model_features_order = [
    'ggtp_alt_ratio',
    'triglyc_hdl_ratio',
    'ldl_hdl_ratio',
    'alt_ast_ratio',
    'age_group_5yr',
    'fasting_blood_glucose',
    'smoking_status',
    'pulse_pressure'
    # TODO: hypertension.ipynb의 최종 모델이 사용한 모든 피처(특히 임포트된 것들)를 추가하세요.
    # 예: 'BMI', 'gender_code', 'hemoglobin', 'urine_protein', 'serum_creatinine', 'total_cholesterol', 'triglycerides', 'ldl_cholesterol', 'ast', 'alt', 'gamma_gtp'
    # 노트북의 최종 X_train.columns 또는 feature_names_in_ 등을 확인하여 정확히 일치시켜야 합니다.
]

# --- Streamlit 앱 메인 로직 ---

# 모델 로드 (앱 시작 시 한 번만 로드하도록 캐시)
@st.cache_resource
def load_prediction_model():
    """학습된 고혈압 예측 모델을 로드하고 캐시합니다."""
    # TODO: 여기에 실제 모델 파일 경로를 지정하세요.
    # 모델 파일은 GitHub 레포지토리의 앱과 같은 디렉토리 또는 접근 가능한 하위 디렉토리에 있어야 합니다.
    # 예: 'best_hypertension_model.joblib'
    model_path = 'model/best_hypertension_model.joblib' # 예시 경로: 'model' 폴더 안에 모델이 있다고 가정
    
    if os.path.exists(model_path):
        try:
            loaded_model = load(model_path)
            st.success(f"모델 파일이 성공적으로 로드되었습니다: {model_path}")
            return loaded_model
        except Exception as e:
            st.error(f"모델 로드 중 오류 발생: {e}")
            st.warning("모델 파일이 손상되었거나 호환되지 않는 버전으로 저장되었을 수 있습니다.")
            return None
    else:
        st.warning(f"모델 파일을 찾을 수 없습니다: {model_path}")
        st.write("모델 파일 경로를 확인하고 앱과 같은 위치 또는 접근 가능한 경로에 두세요.")
        return None

# 모델 로드 시도
loaded_prediction_model = load_prediction_model()


# 이미지 업로드 위젯
uploaded_file = st.file_uploader("건강검진 결과 이미지를 선택하세요...", type=["jpg", "jpeg", "png", "gif", "bmp"])

# 이미지가 업로드되면 처리 시작
if uploaded_file is not None and vision_client is not None:
    # 업로드된 이미지 표시
    st.image(uploaded_file, caption="업로드된 이미지", use_column_width=True)

    st.write("텍스트 추출 중...")

    try:
        # 이미지 파일을 바이트 스트림으로 읽기
        image_content = uploaded_file.read()
        image = vision.Image(content=image_content)

        # 텍스트 추출 요청 (DOCUMENT_TEXT_DETECTION은 문서에 최적화되어 상세 정보를 제공)
        response = vision_client.document_text_detection(image=image)

        # 응답에서 전체 텍스트 가져오기
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
            model_input_df = prepare_model_input(processed_health_data, model_features_order)

            if model_input_df is not None:
                st.dataframe(model_input_df)

                # --- 5. 모델 로드 및 예측 ---
                st.subheader("5. 고혈압 위험 예측:")
                if loaded_prediction_model is not None:
                    # 예측 수행
                    # 모델의 predict_proba 메서드는 모델 객체에 따라 다를 수 있습니다.
                    # 일반적으로 이진 분류 모델은 [:, 1]로 양성 클래스(예: 고혈압)의 확률을 가져옵니다.
                    try:
                        prediction_proba = loaded_prediction_model.predict_proba(model_input_df)[:, 1]
                        st.write(f"예측된 고혈압 확률: **{prediction_proba[0]:.4f}**")

                        # 위험 등급 분류 및 표시
                        risk_level = classify_risk_level(prediction_proba[0])
                        st.write(f"고혈압 위험 등급: **{risk_level}**")
                    except Exception as e:
                        st.error(f"모델 예측 중 오류 발생: {e}")
                        st.warning("모델 입력 데이터의 형식이나 피처가 모델의 기대치와 다를 수 있습니다.")
                else:
                    st.warning("모델이 로드되지 않아 예측을 수행할 수 없습니다.")
            else:
                st.warning("모델 입력 데이터 준비 실패. 예측을 수행할 수 없습니다.")
        else:
            st.info("이미지에서 텍스트를 찾을 수 없습니다.")

        # Vision API 응답 에러 처리
        if response.error.message:
            st.error(f"Vision API 오류 발생: {response.error.message}")

    except Exception as e:
        st.error(f"텍스트 추출 또는 데이터 처리 중 오류 발생: {e}")

# 임시 인증 파일 삭제
# 앱 종료 시 또는 필요 없을 때 삭제하는 것이 좋습니다.
if temp_credentials_path and os.path.exists(temp_credentials_path):
    try:
        os.remove(temp_credentials_path)
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")

st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")
