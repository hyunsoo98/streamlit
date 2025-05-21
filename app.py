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
    layout="centered",
    initial_sidebar_state="collapsed"
)

def apply_custom_css():
    st.markdown("""
    <style>
    /* 전체 앱 배경색 및 폰트 설정 */
    .stApp {
        background-color: #FFFFFF;
        font-family: "Poppins", sans-serif;
        overflow-x: hidden;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 0 !important; /* stApp 자체의 모든 패딩 제거 */
    }

    /* Streamlit의 주요 내부 컨테이너에 대한 강제 중앙 정렬 및 패딩/마진 제거 */
    /* 개발자 도구 스크린샷을 기반으로 하여, 로고를 감싸는 상위 div들에 적용 */
    .main .block-container,
    .stBlock,
    .stVerticalBlock,
    .stMarkdownContainer { /* stMarkdownContainer 추가: 로고 이미지를 직접 감싸는 div */
        display: flex;
        flex-direction: column; /* 세로로 쌓되, flexbox 정렬 활용 */
        justify-content: center; /* 수직 중앙 정렬 */
        align-items: center; /* 수평 중앙 정렬 */
        width: 100% !important; /* 부모 너비에 꽉 채우도록 */
        padding: 0 !important; /* 내부 패딩 제거 */
        margin: 0 !important; /* 내부 마진 제거 */
    }

    /* 로고 이미지와 텍스트를 감싸는 커스텀 컨테이너 */
    /* 이 컨테이너는 이제 Streamlit이 자동 생성하는 div들의 중앙 정렬을 따름 */
    .logo-elements-wrapper {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%; /* 부모에 맞춰 너비 사용 */
        margin-bottom: 20px; /* 아래 내용과의 간격 */
    }

    /* CareBite 텍스트 스타일 */
    .carebite-text {
        color: #333333;
        font-family: "Poppins", sans-serif;
        font-size: 80px;
        line-height: 1;
        font-weight: 600;
        white-space: nowrap;
        text-align: center;
        margin-top: 20px; /* 이미지와의 간격 */
    }

    /* CareBite- 이미지 스타일 */
    .carebite-image {
        width: 150px; /* 로고 이미지 크기 키움 (조절 가능) */
        height: auto;
        object-fit: contain;
        display: block; /* 블록 요소로 설정 */
        /* margin: auto; 는 부모가 text-align: center; 이거나 flex justify-content: center; 일 때 작동 */
    }

    /* Streamlit 내부의 <img> 태그 기본 스타일 오버라이드 (선택 사항) */
    /* 로고 이미지 자체에 overflow: clip; 이 적용되어 있다면 강제 제거 */
    img {
        overflow-clip-margin: content-box; /* 기존 CSS 유지 */
        overflow: clip; /* 기존 CSS 유지 */
        /* 만약 이미지가 잘린다면, overflow: visible; !important; 로 변경 시도 */
    }

    /* Streamlit 기본 제목/텍스트 스타일 */
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

# 로고 이미지와 텍스트를 감싸는 래퍼
st.markdown('<div class="logo-elements-wrapper">', unsafe_allow_html=True)

image_path = "carebite-.png"

if os.path.exists(image_path):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # st.markdown은 자동으로 <p> 태그나 다른 블록 요소를 생성할 수 있습니다.
        # <p> 태그가 이미지를 감싸지 않도록 <img> 태그를 직접 삽입.
        # 이 img 태그를 감싸는 div는 .stMarkdownContainer 클래스를 가지게 됩니다.
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
# 마찬가지로 텍스트를 감싸는 <p> 태그가 .stMarkdownContainer 클래스를 가지게 됩니다.
st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True) # logo-elements-wrapper 닫기

# 나머지 앱 내용
st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# ... (임시 인증 파일 삭제 로직)
if temp_credentials_path and os.path.exists(temp_credentials_path):
    try:
        os.remove(temp_credentials_path)
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")
