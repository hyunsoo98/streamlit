import streamlit as st
import sqlite3
import hashlib # For SHA256 (consider bcrypt for production)
import bcrypt # Recommended for secure password hashing
import os
import json # For Google Cloud Vision API related setup

# --- DB 설정 및 함수 ---
DB_FILE = "users.db" # User database file (should be in the root directory)

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
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

def hash_password_bcrypt(password):
    """Hashes the password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def verify_password_bcrypt(password, stored_hash):
    """Verifies the input password against the stored bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

def register_user(username, password):
    """Registers a new user."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        password_hash = hash_password_bcrypt(password)
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # User already exists
    finally:
        conn.close()

def login_user(username, password):
    """Handles user login."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result:
        stored_hash = result[0]
        return verify_password_bcrypt(password, stored_hash)
    return False

# Initialize DB when this page is loaded (or first time app is run)
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False

# --- Login/Signup Page Content ---

if not st.session_state.logged_in: # Display login/signup form if not logged in
    # Top logo (re-using CSS from app.py)
    st.markdown('<div class="top-logo-container" style="margin-top: 100px; margin-bottom: 20px;">', unsafe_allow_html=True)
    # The carebite logo image should ideally be in a central place if used here.
    # For now, just display the 'CareBite' text.
    st.markdown('<p class="smartly-text">CareBite</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Bottom card
    st.markdown('<div class="card-container">', unsafe_allow_html=True)

    if not st.session_state.show_signup: # Login Form
        st.markdown('<p class="card-title-text">Log in your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        username_input = st.text_input("", placeholder="Enter your email", key="login_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        password_input = st.text_input("", type="password", placeholder="Enter your password", key="login_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True) # Close form-container

        if st.button("Sign In", use_container_width=True, key="signin_button"):
            if login_user(username_input, password_input):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.success(f"환영합니다, {username_input}님!")
                # Navigate to page_2.py upon successful login
                st.switch_page("pages/page_2.py") # Direct switch
            else:
                st.error("잘못된 사용자 이름 또는 비밀번호입니다.")

        # "Don't have an account?" link
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

        # Social login buttons (placeholders for now)
        st.markdown('<div class="social-login-buttons">', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button">F</div>', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button">G</div>', unsafe_allow_html=True)
        st.markdown('<div class="social-icon-button">A</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    else: # Signup Form
        st.markdown('<p class="card-title-text">Create your account</p>', unsafe_allow_html=True)

        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Email</label>', unsafe_allow_html=True)
        signup_username_input = st.text_input("", placeholder="Enter your email", key="signup_username")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="input-group">', unsafe_allow_html=True)
        st.markdown('<label class="input-label">Password</label>', unsafe_allow_html=True)
        signup_password_input = st.text_input("", type="password", placeholder="Create a password", key="signup_password")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("Sign Up", use_container_width=True, key="signup_button"):
            if register_user(signup_username_input, signup_password_input):
                st.success("회원가입이 성공했습니다! 이제 로그인해주세요.")
                st.session_state.show_signup = False # Switch to login form
                st.rerun() # Rerun to display login form
            else:
                st.error("회원가입에 실패했습니다. 사용자 이름이 이미 존재할 수 있습니다.")

        # "Already have an account?" link
        st.markdown(
            """
            <div class="signup-text-container">
                <p class="signup-text">Already have an account? <a href="#" onclick="Streamlit.setSessionState({'show_signup': false})" class="signup-link">Sign In</a></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True) # Close card-container

else: # Already logged in on this page
    st.success(f"이미 로그인되어 있습니다, {st.session_state.username}님! 이미지 분석 페이지로 이동합니다.")
    st.info("잠시 후 이미지 분석 페이지로 자동 이동합니다.")
    st.switch_page("pages/page_2.py") # Automatically switch to page_2.py
