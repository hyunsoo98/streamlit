import streamlit as st
from google.cloud import vision
import io
import os
import json
import re # 정규표현식 라이브러리 임포트
import pandas as pd # 데이터 처리를 위한 pandas 임포트
import numpy as np # prepare_model_input에서 np.nan 사용 가능성을 위해 임포트

# --- Vision API 클라이언트와 임시 인증 파일 경로를 session_state에서 가져오기 ---
vision_client = st.session_state.get('vision_client')
temp_credentials_path = st.session_state.get('temp_credentials_path')
logged_in = st.session_state.get('logged_in', False) # 로그인 상태 가져오기
username = st.session_state.get('username', 'Guest') # 사용자 이름 가져오기

# --- 로그인 확인 및 리디렉션 로직 ---
if not logged_in:
    st.warning("로그인이 필요한 페이지입니다. 로그인 페이지로 이동해주세요.")
    st.page_link("pages/page_1.py", label="로그인 페이지로 이동")
    st.stop() # 로그인되지 않았으면 여기서 앱 실행 중단
elif vision_client is None:
    st.error("Google Cloud Vision API 클라이언트가 초기화되지 않았습니다. 메인 페이지를 확인하거나 앱을 다시 시작해주세요.")
    st.stop() # 클라이언트가 없으면 실행 중단


# --- vision_ai.ipynb 노트북에서 가져온 함수들 (여기에 그대로 붙여넣어야 함) ---
# 기존 app.py에 있던 parse_health_data_from_ocr, preprocess_and_engineer_features,
# prepare_model_input, classify_risk_level 함수들을 여기에 그대로 붙여넣어야 합니다.

def parse_health_data_from_ocr(text):
    """
    OCR 추출 텍스트에서 건강 지표 및 개인 정보를 파싱합니다.
    """
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
    """
    처리된 데이터를 모델 입력에 맞는 DataFrame 형태로 변환하고 피처 순서를 맞춥니다.
    """
    df_sample = pd.DataFrame([processed_data])

    try:
        for col in model_features_order:
            if col not in df_sample.columns: df_sample[col] = None
        df_model_input = df_sample[model_features_order]
    except KeyError as e: st.error(f"오류: 모델에 필요한 피처가 데이터에 없습니다: {e}"); st.write(f"데이터에 있는 피처: {df_sample.columns.tolist()}"); st.write(f"모델에 필요한 피처 순서: {model_features_order}"); return None
    except Exception as e: st.error(f"모델 입력 데이터 준비 중 오류 발생: {e}"); return None
    return df_model_input

def classify_risk_level(prediction_proba):
    """
    모델의 예측 확률(0~1)을 4단계 고혈압 위험 등급으로 분류합니다.
    """
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
st.write(f"환영합니다, {username}님! 건강검진 결과 이미지를 업로드하여 분석할 수 있습니다.") # 로그인 정보 표시
st.write("⚠️ **주의:** 이 앱은 예시 목적으로, 실제 의료 진단에 사용될 수 없습니다. 예측 결과는 참고용입니다.")

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

# 임시 인증 파일 삭제 (이 페이지에서 직접 삭제하지 않고, app.py에서 관리하는 것이 더 좋습니다.)
# if temp_credentials_path and os.path.exists(temp_credentials_path):
#     try:
#         os.remove(temp_credentials_path)
#     except OSError as e:
#         st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")


st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# 로그아웃 버튼
if logged_in:
    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun() # 로그아웃 후 페이지 다시 로드
