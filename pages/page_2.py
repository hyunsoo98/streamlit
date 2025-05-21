import streamlit as st
import base64 # 이미지 Base64 인코딩용
import os # 파일 경로 확인용

# --- CSS 추가 (이 페이지 전용, app.py의 CSS와 병합됨) ---
# app.py의 CSS는 전역으로 적용되므로, 여기서는 이 페이지의 특정 요소에 대한 CSS만 추가합니다.
st.markdown("""
<style>
/* 기본 앱 배경은 app.py에서 설정됨 (여기서는 흰색) */

/* 메인 사각형 (rectangle-116) */
.main-rectangle {
    width: 281px;
    height: 279px;
    box-shadow: 3px 6px 10px 0px rgba(0, 0, 0, 0.3);
    border-radius: 45px;
    background: #FFFFFF;
    margin-top: 50px; /* 위치 조절 (top: 118px 대신) */
    /* margin-left: 50px; (중앙 정렬을 위해 auto로 변경) */
    margin-left: auto;
    margin-right: auto;
    position: relative; /* 내부 absolute 요소의 기준 */
    box-sizing: border-box; /* 패딩이 너비/높이에 포함되도록 */
    display: flex; /* 내부 요소 중앙 정렬용 */
    flex-direction: column;
    justify-content: center;
    align-items: center;
}

/* 하단 버튼 */
.bottom-button-style {
    width: 325px;
    height: 50px;
    border-radius: 12px;
    background: #38ADA9;
    display: flex;
    justify-content: center;
    align-items: center;
    color: #FFFFFF;
    font-family: "Poppins", sans-serif;
    font-size: 14px;
    line-height: 16.38px;
    font-weight: 500;
    text-align: center;
    cursor: pointer;
    border: none;
    margin-top: auto; /* 하단으로 밀어냄 */
    margin-bottom: 20px; /* 하단 여백 */
}

/* 자동 조절 버튼 (auto-adjustment) */
.auto-adjustment-style {
    width: 319px;
    height: 43px;
    border-radius: 12px;
    display: flex;
    justify-content: space-between; /* 양 끝 정렬 */
    align-items: center;
    padding: 12px 15px;
    background: #FFFFFF;
    border: 1px solid #EEEEEE;
    margin-top: 40px; /* 위치 조절 */
    margin-left: auto; /* 중앙 정렬 */
    margin-right: auto;
    box-sizing: border-box;
}
.auto-adjustment-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 16px;
    line-height: 18.72px;
    font-weight: 500;
    white-space: nowrap;
}

/* 인스턴트 기능 버튼들 컨테이너 */
.instant-features-container {
    width: 325px;
    height: 85px;
    display: flex;
    flex-direction: row;
    justify-content: center; /* 가운데 정렬 */
    align-items: center;
    column-gap: 15px;
    margin-top: 40px; /* 위치 조절 */
    margin-left: auto; /* 중앙 정렬 */
    margin-right: auto;
}

/* 개별 인스턴트 기능 버튼 (cool, air, hot, eco) */
.feature-button {
    flex-shrink: 0;
    width: 70px;
    height: 85px;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    row-gap: 5px;
    padding: 10px;
    background: #FFFFFF;
    border: 1px solid #EEEEEE; /* 기본 테두리 */
    box-shadow: 2px 2px 30px 0px rgba(0, 0, 0, 0.1); /* cool 버튼만 그림자 있음 */
    cursor: pointer;
    box-sizing: border-box;
}
.feature-button.cool-shadow {
    box-shadow: 2px 2px 30px 0px rgba(0, 0, 0, 0.1);
}
.feature-button-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 12px;
    line-height: 14.04px;
    font-weight: 500;
    text-align: center;
    white-space: nowrap;
}
.feature-button:not(.cool-shadow) .feature-button-text {
    color: #666666;
}
.feature-icon {
    width: 20px;
    height: 20px;
    object-fit: contain;
}

/* 원형 AC 컨트롤러 (ac-volume) - 복잡하므로 단순화하거나 이미지 사용 권장 */
.ac-volume-container {
    width: 219px;
    height: 214px;
    position: relative;
    /* margin-top: 152px; (상위 main-rectangle 안에 있으므로 상대적으로 조절) */
    /* margin-left: auto; margin-right: auto; (main-rectangle이 flex이므로 내부 정렬 가능) */
    box-sizing: border-box;
    display: flex; /* 내부 요소 중앙 정렬용 */
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.outer-circle {
    width: 210px;
    height: 210px;
    border-radius: 50%;
    border: 1px solid #ccc;
    display: flex;
    justify-content: center;
    align-items: center;
    position: absolute;
    top: 0; left: 8.5px;
    box-sizing: border-box;
}
.ac-center-text {
    color: #333333;
    font-family: "Poppins";
    font-size: 32px;
    line-height: 37.44px;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
    position: absolute;
    top: 81px;
    left: 35.5px;
    width: 155px;
    height: 38px;
    box-sizing: border-box;
}
.ac-small-text {
    color: #666666;
    font-family: "Poppins";
    font-size: 15px;
    line-height: 17.55px;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
    position: absolute;
}
.ac-small-text.top-left { top: 0px; left: 7.5px; }
.ac-small-text.top-right { top: 0px; left: 191px; }
.ac-small-text.bottom-left { top: 196px; left: 0px; width: 42px;}
.ac-small-text.bottom-right { top: 192px; left: 191px; }


/* 상단 메뉴 (menu) */
.top-menu-container {
    width: 325px;
    height: 45px;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
    column-gap: 15px;
    margin-top: 44px;
    margin-left: auto;
    margin-right: auto;
}
.menu-icon {
    width: 45px;
    height: 45px;
    object-fit: contain;
    cursor: pointer;
}
.menu-title-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 20px;
    line-height: 23.4px;
    font-weight: 600;
    text-align: center;
    flex-grow: 1;
}

</style>
""", unsafe_allow_html=True)


# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---
st.title("AC Control Panel (Design Test)")
st.write("에어컨 제어판 디자인을 테스트합니다.") # 로그인 정보 제거

# --- 상단 메뉴 ---
with st.container():
    col1, col2, col3 = st.columns([1, 4, 1]) # 아이콘-제목-아이콘 비율
    with col1:
        st.markdown('<div class="menu-icon">⬅️</div>', unsafe_allow_html=True) # 뒤로가기 아이콘 (임시)
    with col2:
        st.markdown('<p class="menu-title-text">Air Conditioner</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">...</div>', unsafe_allow_html=True) # 더보기 아이콘 (임시)


# --- 메인 사각형 (rectangle-116) 및 AC 볼륨 컨트롤러 ---
with st.container():
    st.markdown('<div class="main-rectangle">', unsafe_allow_html=True)

    # AC 볼륨 컨트롤러 (ac-volume) - 복잡하므로 이미지나 SVG로 대체 권장
    # 여기서는 HTML/CSS로 대략적인 모양만 시도
    st.markdown('<div class="ac-volume-container">', unsafe_allow_html=True)
    st.markdown('<div class="outer-circle"></div>', unsafe_allow_html=True)
    st.markdown('<p class="ac-center-text">24°C</p>', unsafe_allow_html=True) # 중앙 온도 텍스트 (예시)
    st.markdown('<p class="ac-small-text top-left">Off</p>', unsafe_allow_html=True) # 예시 텍스트
    st.markdown('<p class="ac-small-text top-right">Auto</p>', unsafe_allow_html=True)
    st.markdown('<p class="ac-small-text bottom-left">Low</p>', unsafe_allow_html=True)
    st.markdown('<p class="ac-small-text bottom-right">High</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # ac-volume-container 닫기

    st.markdown('</div>', unsafe_allow_html=True) # main-rectangle 닫기


# --- 자동 조절 버튼 ---
with st.container():
    st.markdown(
        """
        <div class="auto-adjustment-style">
            <p class="auto-adjustment-text">Auto Adjustment</p>
            <div>🎛️</div> </div>
        """,
        unsafe_allow_html=True,
    )

# --- 인스턴트 기능 버튼들 ---
with st.container():
    st.markdown('<div class="instant-features-container">', unsafe_allow_html=True)
    
    # Cool 버튼
    st.markdown(
        """
        <div class="feature-button cool-shadow">
            <div>❄️</div> <p class="feature-button-text">Cool</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Air 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>💨</div> <p class="feature-button-text">Air</p>
        </div>
        """, unsafe_allow_html=True)

    # Hot 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>🔥</div> <p class="feature-button-text">Hot</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Eco 버튼
    st.markdown(
        """
        <div class="feature-button">
            <div>🌱</div> <p class="feature-button-text">Eco</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # instant-features-container 닫기


# --- 하단 버튼 (Save Changes) ---
# st.button을 사용하면 Streamlit 위젯 기능을 쉽게 연결 가능
if st.button("Save Changes", key="save_changes_button", use_container_width=True):
    st.success("변경 사항이 저장되었습니다!")

# --- 기타 앱 정보 (필요시) ---
st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")
