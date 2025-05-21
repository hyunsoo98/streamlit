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
    else: processed_data['urine_protein']
