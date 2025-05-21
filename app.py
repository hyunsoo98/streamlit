import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np
import base64

# st.set_page_config는 항상 첫 번째 Streamlit 명령이어야 합니다.
st.set_page_config(
    page_title="이미지 건강 데이터 추출 및 분석",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def apply_custom_css():
    st.markdown("""
    <style>
    /* 1. 전체 앱 배경색 및 폰트 설정 (welcome 클래스 역할) */
    .stApp {
        background-color: #FFFFFF;
        font-family: "Poppins", sans-serif;
        overflow-x: hidden;
        display: flex; /* body를 flex container로 설정 */
        justify-content: center; /* 수평 중앙 정렬 */
        align-items: flex-start; /* 수직 상단 정렬 (필요에 따라 변경) */
        min-height: 100vh; /* 최소 높이를 뷰포트 높이로 설정 */
        padding-top: 50px; /* 상단 여백 추가 (필요에 따라 조절) */
    }

    /* 2. 사각형 컨테이너 스타일 (rectangle-117 클래스 역할) */
    .rectangle-container {
        width: 216px; /* 고정 너비 */
        height: 207px; /* 고정 높이 */
        box-shadow: 5px 10px 10px 0px rgba(0, 0, 0, 0.3);
        border-radius: 45px;
        background: #FFFFFF;
        border: 3px solid #000000;
        display: flex; /* 내부 요소를 중앙에 배치하기 위함 */
        flex-direction: column;
        justify-content: center;
        align-items: center;
        /* margin-top: 283px; /* 더 이상 필요 없음 (body flex 정렬 사용) */
    }

    /* 3. 로고 영역 스타일 (logo 클래스 역할) */
    .logo-inside-container {
        width: 190px;
        height: 62px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        row-gap: 5px;
        column-gap: 5px;
        /* margin-top: 40px; /* rectangle-container 안에서의 위치 조절 */
    }

    /* 4. CareBite 텍스트 스타일 (carebite 클래스 역할) */
    .carebite-text {
        color: #333333;
        font-family: "Poppins", sans-serif;
        font-size: 80px; /* 32px * 2.5 = 80px */
        line-height: 1; /* 텍스트 크기 증가에 따라 line-height 조절 */
        font-weight: 600;
        white-space: nowrap;
        flex-shrink: 0;
        width: 100%; /* 부모 컨테이너에 맞춰 너비 사용 */
        text-align: center; /* 텍스트 중앙 정렬 */
        /* height는 font-size에 맞춰 자동으로 조절되므로 제거하거나 적절히 조절 */
        /* height: 38px; */
    }

    /* 5. CareBite- 이미지 스타일 (carebite- 클래스 역할) */
    .carebite-image {
        width: 80px; /* 로고 크기 조절 (예시) */
        height: auto;
        object-fit: contain; /* 이미지가 비율을 유지하며 컨테이너에 맞도록 */
        margin-bottom: 10px; /* 텍스트와의 간격 조절 */
    }

    /* Streamlit 기본 스타일 오버라이드 */
    h1, h2, h3, h4, h5, h6, p, label, .stText, .stMarkdown, .stButton > button, .stTextInput > div > div > input, .stAlert {
        color: #333333;
        font-family: "Poppins", sans-serif;
    }

    .stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        font-weight: 600;
    }

    .stTextInput > div > div > input {
        border: 2px solid #D3D3D3;
        border-radius: 8px;
        padding: 10px;
    }

    .stAlert {
        font-family: "Poppins", sans-serif;
    }

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    </style>
    """, unsafe_allow_html=True)

# CSS 적용 함수 호출
apply_custom_css()

# --- Google Cloud Vision API 클라이언트 초기화 (동일) ---
temp_credentials_path = None
vision_client = None

try:
    google_cloud_settings = st.secrets["google_cloud"]
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

    temp_credentials_path = "temp_credentials.json"
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_credentials_path
    with open(temp_credentials_path, "w") as f:
        f.write(google_credentials_json)

    @st.cache_resource
    def get_vision_client():
        return vision.ImageAnnotatorClient()

    vision_client = get_vision_client()
except Exception as e:
    st.error(f"Google Cloud 인증 정보를 로드하는 데 실패했습니다: {e}")

st.session_state['vision_client'] = vision_client
st.session_state['temp_credentials_path'] = temp_credentials_path

# --- 앱의 초기 로딩 화면 (환영 페이지) ---
with st.container():
    st.markdown('<div class="rectangle-container">', unsafe_allow_html=True)

    image_path = "carebite-.png"

    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            # 로고 이미지를 상자 안에 배치
            st.markdown(
                f"""
                <img src="data:image/png;base64,{image_base64}" class="carebite-image">
                """,
                unsafe_allow_html=True,
            )

            # 로고 텍스트 (상자 안에 배치)
            st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)

        except Exception as e:
            st.error(f"이미지 '{image_path}' 로딩 오류: {e}")
            st.warning(f"이미지 파일 '{image_path}'을(를) 확인하세요.")
    else:
        st.warning(f"이미지 파일 '{image_path}'을(를) 찾을 수 없습니다.")

    st.markdown('</div>', unsafe_allow_html=True)

st.write("")
st.write("---")

st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로
