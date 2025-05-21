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
    layout="centered", # 중앙 정렬을 위해 'centered' 레이아웃 사용
    initial_sidebar_state="collapsed" # 초기 사이드바는 숨겨두는 것이 시작 페이지에 더 어울릴 수 있습니다.
)

def apply_custom_css():
    st.markdown("""
    <style>
    /* 전체 앱 배경색 및 폰트 설정 */
    .stApp {
        background-color: #FFFFFF; /* 배경색 흰색 */
        font-family: "Poppins", sans-serif;
        overflow-x: hidden;

        /* body를 flex container로 설정하여 모든 내용물 중앙 정렬 */
        display: flex;
        flex-direction: column; /* 세로 방향으로 요소들을 쌓음 */
        justify-content: center; /* 수직 중앙 정렬 (내용물이 적을 때) */
        align-items: center; /* 수평 중앙 정렬 */
        min-height: 100vh; /* 최소 높이를 뷰포트 높이로 설정 */
        padding: 0 !important; /* Streamlit 기본 패딩 제거 */
    }

    /* Streamlit의 주요 내부 컨테이너에 대한 강제 중앙 정렬 및 패딩/마진 제거 */
    .main .block-container,
    .stBlock,
    .stVerticalBlock {
        display: flex;
        flex-direction: column; /* 세로로 쌓되, flexbox 정렬 활용 */
        justify-content: center; /* 수직 중앙 정렬 */
        align-items: center; /* 수평 중앙 정렬 */
        width: 100% !important; /* 부모 너비에 꽉 채우도록 */
        padding: 0 !important; /* 내부 패딩 제거 */
        margin: 0 !important; /* 내부 마진 제거 */
    }

    /* 로고 이미지와 텍스트를 감싸는 커스텀 컨테이너 */
    .logo-elements-wrapper {
        display: flex; /* flex 컨테이너로 설정하여 내부 요소 정렬 */
        flex-direction: column; /* 이미지와 텍스트를 세로로 쌓음 */
        justify-content: center; /* 수직 중앙 정렬 */
        align-items: center; /* 수평 중앙 정렬 */
        width: 100%; /* 부모 너비에 맞춰 */
        margin-bottom: 40px; /* 아래 시작 버튼과의 간격 확보 */
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
        display: block; /* 블록 요소로 설정 */
        margin: auto; /* 블록 요소 중앙 정렬 */
    }

    /* Streamlit이 img 태그에 적용하는 기본 overflow 속성 (유지) */
    img {
        overflow-clip-margin: content-box;
        overflow: clip;
    }

    /* Streamlit의 stMarkdownContainer에 대한 스타일 (핵심 변경) */
    .stMarkdownContainer {
        display: flex; /* flex 컨테이너로 설정 */
        justify-content: center; /* 내부 요소를 수평 중앙 정렬 */
        align-items: center; /* 내부 요소를 수직 중앙 정렬 */
        width: 100% !important; /* 부모 너비에 꽉 채우도록 */
        margin: 0 !important; /* 모든 마진 제거 */
        padding: 0 !important; /* 모든 패딩 제거 */
    }

    /* Streamlit 기본 제목/텍스트 스타일 (전체 앱에 적용) */
    h1, h2, h3, h4, h5, h6, p, label, .stText, .stMarkdown {
        color: #333333;
        font-family: "Poppins", sans-serif;
    }

    /* 버튼 스타일 */
    .stButton > button {
        background-color: #4CAF50; /* 버튼 배경색 */
        color: white;
        padding: 15px 30px; /* 버튼 패딩 크게 */
        border-radius: 10px; /* 버튼 모서리 둥글게 */
        border: none;
        font-weight: 600;
        font-family: "Poppins", sans-serif;
        font-size: 1.2rem; /* 버튼 텍스트 크기 */
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #368d88; /* 호버 시 색상 변경 */
    }
    /* st.page_link 스타일 (st.button과 동일하게 적용되도록) */
    .st-emotion-cache-12t4u4f > a { /* st.page_link가 생성하는 <a> 태그의 상위 div 클래스 */
        display: block; /* 링크를 버튼처럼 보이게 */
        text-decoration: none; /* 밑줄 제거 */
        text-align: center;
        background-color: #4CAF50;
        color: white !important; /* 글자색 강제 흰색 */
        padding: 15px 30px;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        font-family: "Poppins", sans-serif;
        font-size: 1.2rem;
        cursor: pointer;
        transition: background-color 0.3s ease;
        margin-left: auto; /* 페이지 링크 버튼도 중앙 정렬 */
        margin-right: auto; /* 페이지 링크 버튼도 중앙 정렬 */
        width: fit-content; /* 내용에 맞는 너비 */
    }
    .st-emotion-cache-12t4u4f > a:hover {
        background-color: #368d88;
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

# 로고 이미지와 텍스트를 감싸는 래퍼
st.markdown('<div class="logo-elements-wrapper">', unsafe_allow_html=True)

image_path = "carebite-.png" # 이미지 파일 경로 설정

if os.path.exists(image_path):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # 로고 이미지 (img 태그)
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

# --- 시작하기 버튼 (페이지 이동) ---
# st.page_link를 사용하여 'page/page_1.py'로 이동하는 버튼 생성
# 디렉토리 이름과 파일명이 정확히 'page/page_1.py' 여야 합니다.
st.page_link("pages/page_1.py", label="시작하기", icon="🚀")


# 나머지 앱 내용 (환영 페이지 이후에 나타날 부분)
# 이 부분은 "시작하기" 버튼 아래에 위치합니다.
# 만약 환영 페이지에 다른 텍스트나 위젯이 더 필요 없다면 이 부분을 제거하세요.
st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# ... (임시 인증 파일 삭제 로직)
if temp_credentials_path and os.path.exists(temp_credentials_path):
    try:
        os.remove(temp_credentials_path)
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")
