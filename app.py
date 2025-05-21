import streamlit as st
import os
import json
import base64

# st.set_page_config는 항상 첫 번째 Streamlit 명령이어야 합니다.
st.set_page_config(
    page_title="통합 건강 분석 앱",
    layout="centered", # 중앙 정렬을 위해 'centered' 레이아웃 사용
    initial_sidebar_state="collapsed" # 초기 사이드바는 숨겨둠
)

# --- CSS 적용 함수 (이전과 동일) ---
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
        padding: 0 !important;
    }

    /* Streamlit 내부 컨테이너 마진/패딩 초기화 */
    .main .block-container,
    .stBlock,
    .stVerticalBlock {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* 로고 이미지와 텍스트를 감싸는 컨테이너 */
    .logo-elements-wrapper {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-bottom: 40px; /* 아래 시작 버튼과의 간격 확보 */
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
        display: block;
        margin: auto; /* 블록 요소 중앙 정렬 */
    }

    /* Streamlit이 img 태그에 적용하는 기본 overflow 속성 (유지) */
    img {
        overflow-clip-margin: content-box;
        overflow: clip;
    }

    /* Streamlit의 stMarkdownContainer에 대한 스타일 */
    .stMarkdownContainer {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
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
        padding: 15px 30px;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        font-family: "Poppins", sans-serif;
        font-size: 1.2rem;
        cursor: pointer;
        transition: background-color 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #368d88;
    }
    /* st.page_link 스타일 */
    .st-emotion-cache-12t4u4f > a {
        display: block;
        text-decoration: none;
        text-align: center;
        background-color: #4CAF50;
        color: white !important;
        padding: 15px 30px;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        font-family: "Poppins", sans-serif;
        font-size: 1.2rem;
        cursor: pointer;
        transition: background-color 0.3s ease;
        margin-left: auto;
        margin-right: auto;
        width: fit-content;
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

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    </style>
    """, unsafe_allow_html=True)

# CSS 적용 함수 호출
apply_custom_css()

# --- Google Cloud Vision API 클라이언트 초기화 ---
# 이 부분은 app.py에서 초기화하여 session_state에 저장, 모든 페이지에서 사용 가능
temp_credentials_path = None
vision_client = None

try:
    # secrets.toml에서 Google Cloud 서비스 계정 정보 로드
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

# --- 메인 페이지 (환영 페이지) 내용 ---

# 로고 이미지와 텍스트를 감싸는 래퍼
st.markdown('<div class="logo-elements-wrapper">', unsafe_allow_html=True)

image_path = "carebite-.png"

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

st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- 이미지 분석 페이지로 이동하는 버튼 ---
# 이제 'pages/page_1.py' (이미지 분석 페이지)로 직접 이동
st.page_link("pages/page_1.py", label="이미지 분석 시작하기", icon="🚀")

st.markdown("---")
st.write("이 애플리케이션은 Google Cloud Vision API 및 제공된 데이터 처리 로직을 사용합니다.")

# 임시 인증 파일 삭제 (앱 종료 시 처리)
if st.session_state.get('temp_credentials_path') and os.path.exists(st.session_state.get('temp_credentials_path')):
    try:
        os.remove(st.session_state['temp_credentials_path'])
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")
