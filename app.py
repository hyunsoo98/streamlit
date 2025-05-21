import streamlit as st
import sqlite3 # SQLite 모듈 임포트
import hashlib # 비밀번호 해싱을 위한 hashlib 임포트 (더 안전한 bcrypt 권장)
import base64
import os
import json # Google Cloud Vision API 관련

# --- st.set_page_config는 항상 첫 번째 Streamlit 명령이어야 합니다. ---
st.set_page_config(
    page_title="CareBite 로그인",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS 적용 함수 (이전과 동일) ---
def apply_custom_css():
    st.markdown("""
    <style>
    /* ... (이전 apply_custom_css 내용 그대로 유지) ... */
    </style>
    """, unsafe_allow_html=True)
apply_custom_css()

# --- Google Cloud Vision API 클라이언트 초기화 (기존 코드 유지) ---
# 이 부분은 로그인 페이지에서는 직접적으로 필요 없을 수 있지만,
# 세션 상태에 저장하여 다른 페이지에서 사용할 수 있도록 유지합니다.
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

# --- DB 설정 및 함수 ---
DB_FILE = "users.db" # 사용자 정보를 저장할 SQLite DB 파일

def init_db():
    """데이터베이스를 초기화하고 users 테이블을 생성합니다."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    """비밀번호를 해싱합니다."""
    # 실제 서비스에서는 bcrypt 또는 Argon2와 같은 강력한 해싱 라이브러리를 사용해야 합니다.
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, stored_hash):
    """입력된 비밀번호와 저장된 해시를 비교합니다."""
    return hash_password(password) == stored_hash

def register_user(username, password):
    """새 사용자를 등록합니다."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # username UNIQUE 제약 조건 위반 (이미 존재하는 사용자)
        return False
    finally:
        conn.close()

def login_user(username, password):
    """사용자 로그인을 처리합니다."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        stored_hash = result[0]
        return verify_password(password, stored_hash)
    return False

# 앱 시작 시 DB 초기화 (한 번만 실행되도록)
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True
# ---------------------

# --- 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False # 회원가입 폼 표시 여부

# --- 로그인 페이지 내용 ---

if not st.session_state.logged_in: # 로그인되지 않은 경우에만 로그인 폼 표시
    # 상단 로고
    st.markdown('<div class="top-logo-container">', unsafe_allow_html=True)
    image_path = "carebite-.png"
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")
            st.markdown(
                f"""
                <img src="data:image/png;base64,{image_base64}" class="social-icon" style="width:116px; height:123px; margin-top: -130px; object-fit: cover;">
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"로고 이미지 '{image_path}' 로딩 오류: {e}")
    else:
        st.warning(f"로고 이미지 파일 '{image_path}'을(를) 찾을 수 없습니다.")
    st.markdown('<p class="smartly-text">CareBite</p>', unsafe_allow_html=True) # 텍스트 'Smartly'를 'CareBite'로 변경
    st.markdown('</div>', unsafe_allow_html=True)

    # 하단 카드
    st.markdown('<div class="card-container">', unsafe_allow_html=True)

    if not st.session_state.show_signup: # 로그인 폼
        st.markdown('<p class="card-title-text">Log in your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        username = st.text_input("", placeholder="Enter your email", key="login_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        password = st.text_input("", type="password", placeholder="Enter your password", key="login_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) # form-container 닫기

        if st.button("Sign In", use_container_width=True, help="Click to sign in"): # Streamlit 기본 버튼 사용
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"환영합니다, {username}님!")
                st.rerun() # 로그인 성공 후 페이지를 다시 로드하여 다음 화면 표시
            else:
                st.error("잘못된 사용자 이름 또는 비밀번호입니다.")

        # "Don't have an account?" 링크
        st.markdown(
            """
            <div class="signup-text-container">
                <p class="signup-text">Don’t have an account? <a href="#" onclick="Streamlit.setSessionState({'show_signup': true})" class="signup-link">Sign Up</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="or-separator-container">
                <div class="line"></div>
                <p class="sign-in-with-text">Sign in with</p>
                <div class="line"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 소셜 로그인 버튼 그룹 (실제 기능 없음)
        st.markdown('<div class="social-login-buttons">', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button"><img src="data:image/png;base64,{}" class="social-icon"></div>'.format(base64.b64encode(open("facebook.png", "rb").read()).decode("utf-8") if os.path.exists("facebook.png") else ''), unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button"><img src="data:image/png;base64,{}" class="social-icon"></div>'.format(base64.b64encode(open("google.png", "rb").read()).decode("utf-8") if os.path.exists("google.png") else ''), unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button"><img src="data:image/png;base64,{}" class="social-icon"></div>'.format(base64.b64encode(open("apple.png", "rb").read()).decode("utf-8") if os.path.exists("apple.png") else ''), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else: # 회원가입 폼
        st.markdown('<p class="card-title-text">Create your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        signup_username = st.text_input("", placeholder="Enter your email", key="signup_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        signup_password = st.text_input("", type="password", placeholder="Create a password", key="signup_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Sign Up", use_container_width=True, help="Click to register"):
            if register_user(signup_username, signup_password):
                st.success("회원가입이 성공했습니다! 이제 로그인해주세요.")
                st.session_state.show_signup = False # 회원가입 후 로그인 폼으로 전환
                st.rerun() # 페이지 다시 로드
            else:
                st.error("회원가입에 실패했습니다. 사용자 이름이 이미 존재할 수 있습니다.")

        # "Already have an account?" 링크
        st.markdown(
            """
            <div class="signup-text-container">
                <p class="signup-text">Already have an account? <a href="#" onclick="Streamlit.setSessionState({'show_signup': false})" class="signup-link">Sign In</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True) # card-container 닫기

else: # 로그인 성공 시
    st.success(f"안녕하세요, {st.session_state.username}님!")
    st.write("메인 앱 기능으로 이동하거나 아래 버튼을 클릭하세요.")

    # 로그인 성공 후 페이지 이동 버튼
    st.page_link("pages/page_1.py", label="이미지 분석 시작하기", icon="🚀")

    if st.button("로그아웃"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun() # 로그아웃 후 페이지 다시 로드하여 로그인 폼 표시

# 임시 인증 파일 삭제 (앱 종료 시 처리)
if st.session_state.get('temp_credentials_path') and os.path.exists(st.session_state.get('temp_credentials_path')):
    try:
        os.remove(st.session_state['temp_credentials_path'])
    except OSError as e:
        st.warning(f"임시 인증 파일 삭제 중 오류 발생: {e}")
