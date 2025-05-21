import streamlit as st
from google.cloud import vision
import io
import os
import json
import re
import pandas as pd
import numpy as np

# st.set_page_config는 항상 첫 번째 Streamlit 명령이어야 합니다.
st.set_page_config(
    page_title="이미지 건강 데이터 추출 및 분석",
    layout="wide", # 넓은 레이아웃으로 설정하여 여백 확보
    initial_sidebar_state="collapsed" # 사이드바 초기 상태 (필요에 따라 변경)
)

def apply_custom_css():
    st.markdown("""
    <style>
    /* 1. 전체 앱 배경색 및 폰트 설정 (welcome 클래스 역할) */
    .stApp {
        background-color: #FFFFFF; /* welcome의 background가 흰색으로 변경됨 */
        font-family: "Poppins", sans-serif; /* carebite의 폰트 */
        overflow-x: hidden; /* 가로 스크롤 방지 */
    }

    /* 2. 사각형 컨테이너 스타일 (rectangle-117 클래스 역할) */
    /* Streamlit에서 absolute position의 정확한 구현은 어렵습니다.
       여기서는 st.container()를 사용하여 유사한 박스 효과를 냅니다.
       'margin: auto'와 'max-width'로 가운데 정렬 및 크기 제한.
       'box-shadow', 'border-radius', 'border' 적용. */
    .rectangle-container {
        /* position: absolute; top: 283px; left: calc(100% - 375px + 79px); */
        width: 216px; /* 고정 너비 (작은 화면에 적합) */
        height: 207px; /* 고정 높이 */
        box-shadow: 5px 10px 10px 0px rgba(0, 0, 0, 0.3);
        border-radius: 45px;
        background: #FFFFFF;
        border: 3px solid #000000;
        display: flex; /* 내부 요소를 중앙에 배치하기 위함 */
        flex-direction: column;
        justify-content: center;
        align-items: center;
        margin-left: auto; /* 가운데 정렬 */
        margin-right: auto;
        margin-top: 283px; /* top 값과 유사한 간격 조정 */
    }

    /* 3. 로고 영역 스타일 (logo 클래스 역할) */
    /* rectangle-container 내부에 배치되도록 조정.
       position: absolute 대신 flexbox를 사용하여 가운데 정렬. */
    .logo-inside-container {
        /* position: absolute; top: calc(100% - 812px + 406px); left: calc(100% - 375px + 92px); */
        width: 190px;
        height: 62px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        row-gap: 5px;
        column-gap: 5px;
        /* margin-top: 40px; /* rectangle-container 안에서의 위치 조정 */
    }

    /* 4. CareBite 텍스트 스타일 (carebite 클래스 역할) */
    .carebite-text {
        color: #333333; /* 색상 #333333으로 변경됨 */
        font-family: "Poppins", sans-serif;
        font-size: 32px;
        line-height: 37.44px;
        font-weight: 600;
        white-space: nowrap;
        flex-shrink: 0;
        width: 141px; /* 너비 고정 */
        height: 38px; /* 높이 고정 */
        display: flex; /* 텍스트 자체를 중앙 정렬할 경우 */
        justify-content: center;
        align-items: center;
    }

    /* 5. CareBite- 이미지 스타일 (carebite- 클래스 역할) */
    /* 이 부분은 실제 이미지 파일을 Streamlit에 st.image()로 삽입하고,
       CSS로는 이미지의 스타일을 조절하는 것이 더 현실적입니다.
       여기서는 이미지의 기본 크기와 object-fit만 명시합니다. */
    .carebite-image {
        /* position: absolute; top: 283px; left: 129px; */
        width: 116px;
        height: 123px;
        object-fit: cover; /* 이미지가 부모 요소를 채우도록 */
        display: block; /* 블록 요소로 설정하여 마진 auto 적용 가능 */
        margin-left: auto;
        margin-right: auto;
        margin-top: -150px; /* rectangle-container 위로 올리기 위한 음수 마진 (조절 필요) */
        z-index: 100; /* 다른 요소 위에 오도록 z-index 설정 */
    }

    /* Streamlit의 기본 제목 스타일 오버라이드 (선택 사항) */
    h1, h2, h3, h4, h5, h6 {
        color: #333333; /* 배경색이 흰색이므로 제목색도 어둡게 */
        font-family: "Poppins", sans-serif;
    }
    p, label, .stText, .stMarkdown { /* 일반 텍스트 색상도 조정 */
        color: #333333;
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
apply_custom_css()

# --- Google Cloud Vision API 클라이언트 초기화 (공통적으로 사용되므로 여기에 둘 수 있음) ---
# 임시 인증 파일 경로 초기화
temp_credentials_path = None
vision_client = None # 클라이언트 변수명 변경 (client -> vision_client)

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
    # st.success("Google Cloud Vision API 클라이언트가 성공적으로 초기화되었습니다.") # 메인 페이지에서만 표시
except Exception as e:
    st.error(f"Google Cloud 인증 정보를 로드하는 데 실패했습니다. `.streamlit/secrets.toml` 파일을 확인해주세요: {e}")

# Vision API 클라이언트를 세션 상태에 저장하여 모든 페이지에서 접근 가능하게 합니다.
st.session_state['vision_client'] = vision_client
st.session_state['temp_credentials_path'] = temp_credentials_path # 임시 파일 경로도 저장

# --- 앱의 초기 로딩 화면 (환영 페이지) ---
# .rectangle-117 역할을 하는 컨테이너
with st.container():
    st.markdown('<div class="rectangle-container">', unsafe_allow_html=True)

    # .carebite- 이미지 삽입 (rectangle-container 내부 또는 위로)
    # 이미지 파일이 앱과 같은 디렉토리에 'carebite-.png' (또는 .jpg 등)로 있다고 가정
    # CSS로 위치를 정확히 맞추기 어렵기 때문에, 여기서는 컨테이너 중앙에 배치
    # CSS의 absolute top/left 값은 Streamlit에 적용하기 어렵습니다.
    # 만약 이미지를 박스 위에 겹치게 하고 싶다면, z-index와 margin-top을 사용한 조절이 필요합니다.
    # st.image('carebite-.png', use_column_width=False, output_format="PNG", caption="로고 이미지")
    # 이미지 위에 텍스트를 올리려면, 이미지 대신 background-image를 쓰는 것이 더 좋을 수 있습니다.
    # 혹은 CSS z-index와 position: relative/absolute 조합으로 조정해야 하는데, 이는 Streamlit에서 복잡합니다.

    # 로고 텍스트 (carebite 클래스 역할)
    st.markdown('<div class="logo-inside-container">', unsafe_allow_html=True)
    st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# 로고 이미지 (carebite-)를 사각형 컨테이너 밖에 배치하여 겹치게 만듭니다.
# 'carebite-.png' 파일이 앱과 같은 디렉토리에 있다고 가정합니다.
# 정확한 위치는 CSS의 margin-top 값을 조정하여 시각적으로 맞춰야 합니다.
st.markdown(
    """
    <div style="text-align: center;">
        <img src="data:image/png;base64,{}" class="carebite-image">
    </div>
    """.format(
        base64.b64encode(open("carebite-.png", "rb").read()).decode("utf-8")
    ),
    unsafe_allow_html=True,
)
# base64 인코딩을 위해 `import base64`가 필요합니다. 파일 상단에 추가해주세요.
# 이미지를 직접 넣는 것보다 base64로 인코딩하여 CSS에 직접 삽입하는 것이 안정적일 수 있습니다.

st.write("") # 간격 추가
st.write("---") # 구분선 추가
st.header("앱 내용 시작")
st.write("이곳에 당신의 Streamlit 앱의 다른 요소들을 추가하세요.")

# 예시: 다른 위젯 추가
st.text_input("이름을 입력하세요:")
st.button("제출")


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
