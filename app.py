import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np
import base64 # base64 모듈 임포트

# st.set_page_config는 항상 첫 번째 Streamlit 명령이어야 합니다.
st.set_page_config(
    page_title="이미지 건강 데이터 추출 및 분석",
    layout="centered", # 중앙 정렬을 위해 'centered' 레이아웃 사용
    initial_sidebar_state="collapsed"
)

def apply_custom_css():
    st.markdown("""
    <style>
    /* 1. 전체 앱 배경색 및 폰트 설정 (welcome 클래스 역할) */
    .stApp {
        background-color: #FFFFFF; /* 배경색 흰색 */
        font-family: "Poppins", sans-serif;
        overflow-x: hidden;

        /* body를 flex container로 설정하여 내용물 중앙 정렬 */
        display: flex;
        flex-direction: column; /* 세로 방향으로 요소들을 쌓음 */
        justify-content: center; /* 수직 중앙 정렬 */
        align-items: center; /* 수평 중앙 정렬 */
        min-height: 100vh; /* 최소 높이를 뷰포트 높이로 설정 */
        padding-top: 0; /* stApp 자체의 기본 패딩 제거 */
        padding-bottom: 0; /* stApp 자체의 기본 패딩 제거 */
    }

    /* Streamlit의 기본 컴포넌트의 마진/패딩을 초기화하여 더 세밀한 제어 가능 */
    .stBlock {
        margin: 0 !important;
        padding: 0 !important;
    }
    .stBlock > div {
        margin: 0 !important;
        padding: 0 !important;
    }


.logo-elements-wrapper {
    display: flex; /* flex 컨테이너로 설정 */
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: fit-content; /* 또는 고정 너비. 내용물만큼 너비를 가짐 */
    margin-left: auto; /* 이 래퍼 자체를 중앙 정렬 */
    margin-right: auto;
    margin-bottom: 20px;
}

    /* CareBite 텍스트 스타일 */
    .carebite-text {
        color: #333333;
        font-family: "Poppins", sans-serif;
        font-size: 80px; /* 폰트 크기 크게 (2.5배) */
        line-height: 1; /* 텍스트 줄 간격 조절 */
        font-weight: 600;
        white-space: nowrap; /* 텍스트가 한 줄로 유지되도록 */
        text-align: center; /* 텍스트 자체 중앙 정렬 */
        margin-top: 20px; /* 이미지와의 간격 */
    }

    /* CareBite- 이미지 스타일 */
    .carebite-image {
        width: 150px; /* 로고 이미지 크기 키움 (조절 가능) */
        height: auto; /* 비율 유지 */
        object-fit: contain;
        display: block; /* 중앙 정렬을 위해 블록 요소로 */
    }

    /* Streamlit 기본 제목/텍스트 스타일 (전체 앱에 적용) */
    h1, h2, h3, h4, h5, h6, p, label, .stText, .stMarkdown {
        color: #333333;
        font-family: "Poppins", sans-serif;
    }

    /* 버튼 스타일 */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        border: none;
        font-weight: 600;
        font-family: "Poppins", sans-serif;
    }

    /* 입력 필드 스타일 */
    .stTextInput > div > div > input {
        border: 2px solid #D3D3D3;
        border-radius: 8px;
        padding: 10px;
        font-family: "Poppins", sans-serif;
    }

    /* 알림 메시지 스타일 */
    .stAlert {
        font-family: "Poppins", sans-serif;
    }

    /* Google Fonts Poppins 임포트 */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    </style>
    """, unsafe_allow_html=True)

# CSS 적용 함수 호출
apply_custom_css()

# --- Google Cloud Vision API 클라이언트 초기화 (기존 코드 유지) ---
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

# 로고 이미지와 텍스트를 감싸는 래퍼 (이제 상자가 없으므로 페이지 중앙에 바로 배치)
st.markdown('<div class="logo-elements-wrapper">', unsafe_allow_html=True)

image_path = "carebite-.png" # 이미지 파일 경로 설정

if os.path.exists(image_path):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        st.markdown(
            f"""
            <img src="data:image/png;base64,{image_base64}" class="carebite-image">
            """,
            unsafe_allow_html=True,
        )

    except Exception as e:
        st.error(f"이미지 '{image_path}' 로딩 오류: {e}")
        st.warning(f"이미지 파일 '{image_path}'을(를) 확인하세요.")
else:
    st.warning(f"이미지 파일 '{image_path}'을(를) 찾을 수 없습니다.")

# 로고 텍스트
st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # logo-elements-wrapper 닫기

# 이제 여기에 다른 앱 내용이 오게 됩니다.
# 이미지 캡처에는 보이지 않으므로, 이 부분은 제거하거나 다른 페이지로 이동해야 합니다.
st.markdown("---") # 구분선 유지

# 앱의 메인 기능 시작 (환영 페이지 이후 내용)
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# (이하 기존 코드 동일)
# 예시: 다른 위젯 추가 (이 부분도 환영 페이지라면 필요 없을 수 있습니다)
# st.text_input("이름을 입력하세요:")
# st.button("제출")


# 임시 인증 파일 삭제
if temp_credentials_path and os.path.exists(temp_credentials_path):
    try:
        os.remove(temp_credentials_path)
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")
