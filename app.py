import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np

# --- Creatie.ai CSS 적용 시작 ---
def apply_creatie_css():
    st.markdown("""
    <style>
    /* 전체 앱 배경색 및 폰트 설정 (welcome 클래스 역할) */
    .stApp {
        background-color: #38ADA9; /* welcome의 background */
        font-family: "Poppins", sans-serif; /* carebite의 폰트 */
        /* width와 height는 Streamlit 앱 전체에 고정하기 어려우므로 적용하지 않음.
           반응형 디자인을 위해 Streamlit의 기본 레이아웃을 따르도록 함. */
        overflow-x: hidden; /* 가로 스크롤 방지 */
    }

    /* Streamlit의 기본 제목 스타일 오버라이드 (선택 사항) */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF; /* 제목 색상 흰색으로 변경 */
        font-family: "Poppins", sans-serif;
    }

    /* 로고 컨테이너 (logo 클래스 역할) */
    /* Streamlit에서 absolute position은 사용하기 어려우므로,
       가운데 정렬 등의 다른 방식으로 로고를 배치하는 것을 고려합니다.
       여기서는 flexbox를 이용한 가운데 정렬을 시도합니다. */
    .logo-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%; /* Streamlit 컨테이너에 맞춰 너비 설정 */
        /* padding-top은 실제 디자인에 따라 조절. 원래 368px은 너무 김 */
        padding-top: 20px; /* 상단 여백 (조절 가능) */
        padding-bottom: 20px; /* 하단 여백 (조절 가능) */
        row-gap: 5px;
        column-gap: 5px;
        /* absolute position 관련 CSS는 Streamlit에 직접 적용하기 어려움 */
        /* top: calc(100% - 812px + 368px); left: calc(100% - 375px + 116.5px); */
    }

    /* CareBite 텍스트 스타일 (carebite 클래스 역할) */
    .carebite-text {
        color: #FFFFFF;
        font-family: "Poppins", sans-serif;
        font-size: 32px;
        line-height: 37.44px;
        font-weight: 600;
        white-space: nowrap; /* 개행 방지 */
        flex-shrink: 0; /* flex 컨테이너 내에서 크기 축소 방지 */
    }

    /* group-1 스타일 (이 부분은 Streamlit에서 직접 매핑하기 어려움) */
    /* 이 클래스는 특정 HTML 요소에 직접 적용되어야 하지만,
       Streamlit의 기본 레이아웃에서 고정 위치의 작은 그룹은 이미지로 처리하거나,
       복잡한 커스텀 컴포넌트를 사용해야 합니다.
       여기서는 시각적 구분을 위해 임시 배경색과 크기만 적용합니다.
       실제 애플리케이션에서는 이 부분을 이미지로 대체하거나 다른 방식으로 구현해야 합니다. */
    .group-1-style {
        /* position: absolute; top: 299px; left: 158px; */
        width: 48px;
        height: 76px;
        /* background-color: rgba(255, 255, 255, 0.2); */ /* 시각적 확인을 위한 임시 배경 (주석 처리) */
        margin-left: auto; /* 가운데 정렬 또는 특정 위치 조정 시 사용 */
        margin-right: auto;
        display: block; /* 블록 요소로 중앙 정렬 */
    }

    /* Streamlit의 기본 버튼 스타일 변경 (선택 사항) */
    .stButton > button {
        background-color: #4CAF50; /* 예시 색상, 디자인에 맞게 변경 */
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        font-family: "Poppins", sans-serif;
        font-weight: 600;
    }

    /* Streamlit의 텍스트 입력 필드 스타일 변경 (선택 사항) */
    .stTextInput > div > div > input {
        border: 2px solid #D3D3D3; /* 테두리 색상 */
        border-radius: 8px; /* 둥근 모서리 */
        padding: 10px;
        font-family: "Poppins", sans-serif;
    }

    /* Streamlit의 성공/경고/오류 메시지 스타일 변경 (선택 사항) */
    .stAlert {
        font-family: "Poppins", sans-serif;
    }

    /* Google Fonts Poppins 임포트 */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    </style>
    """, unsafe_allow_html=True)

# CSS 적용 함수 호출
apply_creatie_css()
# --- Creatie.ai CSS 적용 끝 ---


# 페이지 설정
st.set_page_config(page_title="이미지 건강 데이터 추출 및 분석", layout="centered")

# 기존 st.title 및 st.write 대신 커스텀 CSS 적용을 위한 로고 및 제목 섹션
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)
# group-1에 해당하는 요소가 있다면 여기에 추가 (예: 아이콘 이미지)
# st.markdown('<div class="group-1-style"></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 나머지 제목 및 설명 (기존의 st.title, st.write는 위에 정의된 h1/p 스타일을 따름)
st.title("Google Cloud Vision API를 이용한 이미지 건강 데이터 추출 및 분석")
st.write("건강검진 결과 이미지를 업로드하면 Vision API로 텍스트를 추출하고, 추출된 데이터를 분석하여 고혈압 위험도를 예측합니다.")
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

# 임시 인증 파일 경로 초기화 (try 블록 외부에서 정의)
temp_credentials_path = None
client = None # Vision API 클라이언트 초기화

# Google Cloud 인증 정보 설정
# Streamlit secrets를 사용하여 안전하게 관리합니다.
# .streamlit/secrets.toml 파일에 Google Cloud 서비스 계정 정보가 설정되어 있어야 합니다.
try:
    # secrets.toml에서 Google Cloud 서비스 계정 정보 로드
    google_cloud_settings = st.secrets["google_cloud"]

    # 인증 정보 JSON 문자열 생성
    # Vision API 클라이언트가 GOOGLE_APPLICATION_CREDENTIALS 환경 변수를 통해 인증 정보를 찾도록 설정
    # 실제 서비스에서는 Secret Manager 등 더 안전한 방법을 고려하세요.
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
    temp_credentials_path = "temp_credentials.json" # 성공 시 경로 할당
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_credentials_path
    with open(temp_credentials_path, "w") as f:
        f.write(google_credentials_json)

    # Vision API 클라이언트 초기화
    @st.cache_resource
    def get_vision_client():
        """Vision API 클라이언트를 초기화하고 캐시합니다."""
        return vision.ImageAnnotatorClient()

    client = get_vision_client()
    st.success("Google Cloud Vision API 클라이언트가 성공적으로 초기화되었습니다.")

except Exception as e:
    st.error(f"Google Cloud 인증 정보를 로드하는 데 실패했습니다. `.streamlit/secrets.toml` 파일을 확인해주세요: {e}")
    # 초기화 실패 시 client는 None 상태 유지

# --- vision_ai.ipynb 노트북에서 가져온 함수들 ---

def parse_health_data_from_ocr(text):
    """
    OCR 추출 텍스트에서 건강 지표 및 개인 정보를 파싱합니다.
    이 함수는 제공된 OCR 텍스트 형식에 맞춰 작성되었습니다.
    실제 사용 시에는 다양한 OCR 결과 및 문서 형식을 고려하여 수정해야 합니다.
    """
    data = {}

    # 나이 및 성별 파싱 (예: "나이성별45여성" 패턴 수정)
    # 나이성별 뒤에 숫자(\d+), 그 뒤에 '여성' 또는 '남성'이 오는 패턴을 찾습니다.
    age_gender_match = re.search(r'나이성별\s*(\d+)\s*(여성|남성)', text)
    if age_gender_match:
        data['나이'] = int(age_gender_match.group(1))
        data['성별'] = age_gender_match.group(2).strip()
    else:
        data['나이'] = None
        data['성별'] = None


    # 키 및 몸무게 파싱 (예: "155(cm)/70(kg)" 패턴)
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
    # OCR 결과의 실제 텍스트 패턴에 맞춰 정규표현식을 조정했습니다.
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
        '요단백': r'요단백\s*([가-힣]+)', # '정상', '경계', '단백뇨 의심' 등
        # 흡연 상태, 음주 여부는 제공된 텍스트에서 명확히 추출하기 어려움.
        # 모델 입력에 필요하다면 다른 방법으로 얻거나 기본값/결측치 처리 필요.
        '흡연 상태': None, # 텍스트에서 직접 추출 어려움
        '음주 여부': None  # 텍스트에서 직접 추출 어려움
    }

    for key, pattern in patterns.items():
        if pattern is None:
            data[key] = None # 패턴이 없는 경우는 None
            continue

        # re.DOTALL: . 문자가 줄바꿈 문자를 포함하도록 함
        # re.IGNORECASE: 대소문자 구분 없이 매칭
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            # 첫 번째 캡처 그룹이 보통 값에 해당합니다.
            value_str = match.group(1)
            try:
                # 숫자 값인 경우 float으로 변환 시도
                data[key] = float(value_str)
            except ValueError:
                # 숫자가 아닌 경우 문자열 그대로 저장 (예: 요단백)
                data[key] = value_str.strip()
            except IndexError:
                 # 그룹이 하나만 있는 경우 (값만 있는 경우)
                try:
                     # 항목명 뒤의 값을 파싱 시도
                     value_str = text[match.end():].splitlines()[0].strip()
                     # 값 부분에서 숫자만 추출
                     num_match = re.search(r'\\d+(\\.\\d+)?', value_str)
                     if num_match:
                         data[key] = float(num_match.group(0))
                     else:
                         data[key] = value_str # 숫자 없으면 문자열 그대로
                except Exception:
                    data[key] = None # 예외 발생 시 None

        else:
            data[key] = None # 값을 찾지 못한 경우 None으로 표시

    return data

def preprocess_and_engineer_features(raw_data):
    """
    파싱된 원시 데이터를 모델 입력에 맞는 피처로 변환하고 파생 변수를 계산합니다.
    hypertension.ipynb 모델의 최종 피처 목록 및 변환 방식을 따라야 합니다.
    """
    processed_data = {}

    # --- 기본 피처 변환 및 매핑 ---
    # 모델 노트북에서 사용된 피처 이름과 일치시킵니다.
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

    # 범주형 피처 변환 (모델 학습 시 사용된 인코딩 방식 적용)
    # hypertension.ipynb 노트북의 인코딩 방식을 확인하여 여기에 반영해야 합니다.
    # 예: 성별 (남성: 1, 여성: 2)
    gender = raw_data.get('성별')
    if gender == '남성':
        processed_data['gender_code'] = 1
    elif gender == '여성':
        processed_data['gender_code'] = 2
    else:
        processed_data['gender_code'] = None # 또는 결측치 처리 방식에 따름

    # 예: 흡연 상태 (비흡연자: 1, 과거 흡연자: 2, 현재 흡연자: 3)
    # 제공된 텍스트에 흡연 상태 정보가 없으므로 임의의 기본값(예: 비흡연자) 또는 None 처리
    # 실제 사용 시에는 문서에서 추출하거나 사용자 입력을 받아야 합니다.
    # 여기서는 예시로 비흡연자(1)로 가정합니다. (모델의 인코딩 방식 확인 필요)
    processed_data['smoking_status'] = 1 # 예시: 비흡연자

    # 예: 요단백 (음성: 0, 양성: 1 등) - 실제 모델의 인코딩 확인 필요
    urine_protein = raw_data.get('요단백')
    if urine_protein == '정상': # OCR 결과 '정상'으로 감지
        processed_data['urine_protein'] = 0
    # OCR 결과에 '경계'나 '단백뇨 의심'이 있다면 해당 값에 맞는 인코딩 추가
    # 예: elif urine_protein in ['경계', '단백뇨 의심']: processed_data['urine_protein'] = 1
    else:
        processed_data['urine_protein'] = None # 또는 모델의 결측치 처리 방식에 따름

    # 나이 그룹 (5세 단위) 계산 - 모델의 'age_group_5yr' 피처에 맞게 변환
    age = raw_data.get('나이')
    if age is not None:
        processed_data['age_group_5yr'] = (age // 5) * 5 # 예: 45세 -> 40
    else:
        processed_data['age_group_5yr'] = None


    # --- 파생 변수 계산 ---
    # hypertension.ipynb 노트북의 최종 모델 ('selected_features_final_pruned')에서 사용된 파생 변수 계산
    # BMI = 체중(kg) / (신장(m))^2
    height = raw_data.get('신장')
    weight = raw_data.get('체중')
    if height is not None and weight is not None and height > 0:
         processed_data['BMI'] = weight / ((height / 100.0) ** 2)
    else:
         processed_data['BMI'] = None # 신장 또는 체중 정보 없으면 BMI 계산 불가

    # 맥압 (수축기 혈압 - 이완기 혈압)
    systolic_bp = raw_data.get('수축기 혈압')
    diastolic_bp = raw_data.get('이완기 혈압')
    if systolic_bp is not None and diastolic_bp is not None:
        processed_data['pulse_pressure'] = systolic_bp - diastolic_bp
    else:
        processed_data['pulse_pressure'] = None

    # LDL/HDL 비율
    ldl = processed_data.get('ldl_cholesterol')
    hdl = processed_data.get('hdl_cholesterol')
    if ldl is not None and hdl is not None and hdl != 0:
        processed_data['ldl_hdl_ratio'] = ldl / hdl
    else:
        processed_data['ldl_hdl_ratio'] = None

    # 감마지티피/ALT 비율
    ggtp = processed_data.get('gamma_gtp')
    alt = processed_data.get('alt')
    if ggtp is not None and alt is not None and alt != 0:
        processed_data['ggtp_alt_ratio'] = ggtp / alt
    else:
        processed_data['ggtp_alt_ratio'] = None

    # 트리글리세라이드/HDL 비율
    triglycerides = processed_data.get('triglycerides')
    hdl = processed_data.get('hdl_cholesterol')
    if triglycerides is not None and hdl is not None and hdl != 0:
        processed_data['triglyc_hdl_ratio'] = triglycerides / hdl
    else:
        processed_data['triglyc_hdl_ratio'] = None

    # ALT/AST 비율
    alt = processed_data.get('alt')
    ast = raw_data.get('ast')
    if alt is not None and ast is not None and ast != 0:
        processed_data['alt_ast_ratio'] = alt / ast
    else:
        processed_data['alt_ast_ratio'] = None

    # 모델 노트북의 최종 피처 목록에 포함된 다른 파생 변수가 있다면 여기에 추가 계산 로직을 넣어야 합니다.
    # 예: 'bmi_systolic_ratio' 등이 있다면 계산 로직 추가

    # --- 결측치 처리 (모델 학습 시 사용된 방식 적용) ---
    # 모델 학습 시 결측치를 특정 값으로 채웠다면 여기에서도 동일하게 처리해야 합니다.
    # 예를 들어, 평균값으로 채웠다면 해당 피처의 학습 데이터 평균값을 사용하여 채웁니다.
    # 여기서는 간단히 None 상태로 둡니다. 모델이 결측치를 처리할 수 있어야 합니다 (예: XGBoost의 missing=None).

    return processed_data

def prepare_model_input(processed_data, model_features_order):
    """
    처리된 데이터를 모델 입력에 맞는 DataFrame 형태로 변환하고 피처 순서를 맞춥니다.
    """
    # 딕셔너리를 DataFrame의 한 행으로 변환
    df_sample = pd.DataFrame([processed_data])

    # 모델 학습 시 사용된 최종 피처 순서대로 컬럼을 재정렬합니다.
    # hypertension.ipynb 파일의 최종 모델 학습 코드 셀 (예: XGBoost 최종 모델)에서
    # X 변수를 구성할 때 사용된 컬럼 목록을 정확히 확인하여 순서대로 입력하세요.
    # notebook의 마지막 셀 근처에 정의된 'selected_features_final_pruned' 리스트를 참고했습니다.
    try:
        # 모델 피처 순서에 없는 컬럼은 제거하고, 있는 컬럼만 순서대로 가져옵니다.
        # model_features_order에 있는 모든 컬럼이 df_sample에 있는지 확인하고, 없으면 None 또는 np.nan으로 채웁니다.
        for col in model_features_order:
            if col not in df_sample.columns:
                df_sample[col] = None # 또는 np.nan (모델이 결측치를 처리하는 방식에 따름)

        df_model_input = df_sample[model_features_order]

        # 필요시 데이터 타입 확인 및 변환 (모델 학습 시 사용된 타입과 일치시켜야 함)
        # 예: df_model_input = df_model_input.astype(float)
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
    hypertension.ipynb 노트북의 예측 확률 분포를 참고하여 임계값을 설정했습니다.
    """
    if prediction_proba is None:
        return "분류 불가 (데이터 부족)"

    # 노트북의 확률 분포 및 임계값 분석 결과 참고
    if prediction_proba <= 0.59:
        return "정상"
    elif prediction_proba <= 0.74:
        return "주의"
    elif prediction_proba <= 0.89:
        return "위험"
    else: # prediction_proba > 0.89
        return "고위험"

# --- 모델 학습 시 사용된 최종 피처 목록 및 순서 정의 ---
# hypertension.ipynb 노트북의 'selected_features_final_pruned' 리스트를 참고했습니다.
# 실제 사용 시에는 모델 학습에 사용된 정확한 피처 목록과 순서를 확인하여 여기에 반영해야 합니다.
model_features_order = [
    'ggtp_alt_ratio',
    'triglyc_hdl_ratio',
    'ldl_hdl_ratio',
    'alt_ast_ratio',
    'age_group_5yr',
    'fasting_blood_glucose',
    'smoking_status',
    'pulse_pressure'
    # 모델에 따라 다른 피처가 포함될 수 있습니다.
    # 예: 'BMI', 'gender_code', 'hemoglobin', 'urine_protein', 'serum_creatinine' 등
    # 모델 학습에 사용된 최종 X 변수의 컬럼 순서를 확인하세요.
    # 제공된 노트북에서는 'selected_features_final_pruned'가 마지막 모델 학습에 사용된 것으로 보입니다.
]


# --- Streamlit 앱 메인 로직 ---

# 이미지 업로드 위젯
uploaded_file = st.file_uploader("건강검진 결과 이미지를 선택하세요...", type=["jpg", "jpeg", "png", "gif", "bmp"])

# 이미지가 업로드되면 처리 시작
if uploaded_file is not None and client is not None:
    # 업로드된 이미지 표시
    st.image(uploaded_file, caption="업로드된 이미지", use_column_width=True)

    st.write("텍스트 추출 중...")

    try:
        # 이미지 파일을 바이트 스트림으로 읽기
        image_content = uploaded_file.read()
        image = vision.Image(content=image_content)

        # 텍스트 추출 요청 (DOCUMENT_TEXT_DETECTION은 문서에 최적화되어 상세 정보를 제공)
        response = client.document_text_detection(image=image)

        # 응답에서 전체 텍스트 가져오기
        texts = response.full_text_annotation

        if texts:
            st.subheader("1. Vision API 추출 텍스트:")
            # 전체 텍스트를 텍스트 영역에 표시
            st.text_area("추출된 원본 텍스트", texts.text, height=300)

            # --- 추출된 텍스트를 사용하여 데이터 처리 ---
            st.subheader("2. 텍스트 파싱 결과:")
            raw_health_data = parse_health_data_from_ocr(texts.text)
            st.json(raw_health_data) # 파싱된 원시 데이터 표시

            st.subheader("3. 데이터 전처리 및 피처 엔지니어링 결과:")
            processed_health_data = preprocess_and_engineer_features(raw_health_data)
            st.json(processed_health_data) # 전처리 및 피처 엔지니어링 결과 표시

            st.subheader("4. 모델 입력 데이터 준비:")
            model_input_df = prepare_model_input(processed_health_data, model_features_order)

            if model_input_df is not None:
                st.dataframe(model_input_df) # 모델 입력 DataFrame 표시

                # --- 5. 모델 로드 및 예측 (이 부분은 직접 구현해야 합니다) ---
                st.subheader("5. 고혈압 위험 예측:")
                st.write("모델 로드 및 예측 코드는 현재 주석 처리되어 있습니다.")
                st.write("학습된 모델 파일을 로드하고 `predict_proba` 메서드를 사용하여 예측을 수행하세요.")
                st.write("예측 결과(확률)에 따라 아래 `classify_risk_level` 함수를 호출하여 위험 등급을 표시할 수 있습니다.")

                # 예시: 모델 로드 (실제 파일 경로와 모델 로드 방식에 맞게 수정 필요)
                # try:
                #     from joblib import load
                #     model_path = 'path/to/your/best_hypertension_model.joblib' # <-- 모델 파일 경로 지정
                #     if os.path.exists(model_path):
                #         loaded_model = load(model_path)
                #         st.success("모델 파일이 성공적으로 로드되었습니다.")

                #         # 예측 수행
                #         # 모델의 predict_proba 메서드는 모델 객체에 따라 다를 수 있습니다.
                #         prediction_proba = loaded_model.predict_proba(model_input_df)[:, 1]
                #         st.write(f"예측된 고혈압 확률: **{prediction_proba[0]:.4f}**")

                #         # 위험 등급 분류 및 표시
                #         risk_level = classify_risk_level(prediction_proba[0])
                #         st.write(f"고혈압 위험 등급: **{risk_level}**")

                #     else:
                #         st.warning(f"모델 파일을 찾을 수 없습니다: {model_path}")
                #         st.write("모델 파일 경로를 확인하고 앱과 같은 위치 또는 접근 가능한 경로에 두세요.")

                # except ImportError:
                #     st.error("`joblib` 라이브러리가 설치되지 않았습니다. `pip install joblib` 명령으로 설치하세요.")
                # except Exception as e:
                #     st.error(f"모델 로드 또는 예측 중 오류 발생: {e}")


            else:
                st.warning("모델 입력 데이터 준비 실패. 예측을 수행할 수 없습니다.")


        else:
            st.info("이미지에서 텍스트를 찾을 수 없습니다.")

        # Vision API 응답 에러 처리
        if response.error.message:
            st.error(f"Vision API 오류 발생: {response.error.message}")

    except Exception as e:
        st.error(f"텍스트 추출 또는 데이터 처리 중 오류 발생: {e}")

# 임시 인증 파일 삭제 (필요에 따라 유지하거나 다른 방식으로 관리할 수 있습니다)
# 앱 종료 시 또는 필요 없을 때 삭제하는 것이 좋습니다.
# temp_credentials_path가 None이 아니고 파일이 존재하는 경우에만 삭제 시도
if temp_credentials_path and os.path.exists(temp_credentials_path):
    try:
        os.remove(temp_credentials_path)
        # st.write(f"임시 인증 파일 삭제됨: {temp_credentials_path}") # 선택 사항: 디버깅용
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")


st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")
