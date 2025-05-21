import streamlit as st

# --- 1. st.set_page_config()를 맨 위로 이동 ---
st.set_page_config(layout="wide") # 넓은 레이아웃으로 설정하여 여백 확보

def apply_custom_css():
    st.markdown("""
    <style>
    /* 1. 전체 앱 배경색 및 폰트 설정 (welcome 클래스 역할) */
    .stApp {
        background-color: #38ADA9; /* welcome의 background */
        font-family: "Poppins", sans-serif; /* carebite의 폰트 */
    }

    /* 2. 로고 영역 스타일 (logo 클래스 역할) */
    /* Streamlit에서 absolute position은 사용하기 어려우므로,
       가운데 정렬 등의 다른 방식으로 로고를 배치하는 것을 고려합니다.
       만약 절대 위치를 강제하려면 st.empty()나 st.container()를 사용해야 할 수 있습니다.
       여기서는 flexbox를 이용한 가운데 정렬을 시도합니다. */
    .logo-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        width: 100%; /* Streamlit 컨테이너에 맞춰 너비 설정 */
        padding-top: 368px; /* welcome의 top 값과 유사하게 간격 조정 */
        /* height: 75px; /* height는 내용물에 따라 조절될 수 있습니다. */
        row-gap: 5px;
        column-gap: 5px;
        /* top: calc(100% - 812px + 368px); left: calc(100% - 375px + 116.5px); */
        /* 위 absolute position은 Streamlit에서 직접 사용하기 어렵습니다. */
    }

    /* 3. CareBite 텍스트 스타일 (carebite 클래스 역할) */
    .carebite-text {
        color: #FFFFFF;
        font-family: "Poppins", sans-serif;
        font-size: 32px;
        line-height: 37.44px;
        font-weight: 600;
        white-space: nowrap; /* 개행 방지 */
        flex-shrink: 0; /* flex 컨테이너 내에서 크기 축소 방지 */
    }

    /* 4. group-1 스타일 (이 부분은 이미지나 다른 요소일 가능성이 높음) */
    /* 이 클래스는 특정 HTML 요소에 직접 적용되어야 합니다.
       Streamlit에서 이와 같은 고정 위치의 작은 그룹은 이미지로 처리하거나,
       특정 컨테이너를 만들고 그 안에 내용을 넣어야 합니다.
       여기서는 단순히 예시로 빈 컨테이너를 만듭니다. */
    .group-1-style {
        /* position: absolute; top: 299px; left: 158px; */
        /* 위 absolute position은 Streamlit에서 직접 사용하기 어렵습니다. */
        width: 48px;
        height: 76px;
        background-color: rgba(255, 255, 255, 0.2); /* 시각적 확인을 위한 임시 배경 */
        /* display: flex; /* 내부 요소가 있다면 flexbox를 사용할 수 있음 */
        /* justify-content: center;
        align-items: center; */
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CSS 적용 함수 호출 (set_page_config 아래) ---
apply_custom_css()

# 로고 영역 (carebite-text를 포함)
# 로고 컨테이너에 CSS 클래스를 부여하고, 그 안에 텍스트를 넣습니다.
st.markdown('<div class="logo-container">', unsafe_allow_html=True)
st.markdown('<p class="carebite-text">CareBite</p>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# group-1 영역
# 이 부분은 실제 어떤 내용이 들어갈지 모르므로, 임시 컨테이너로 표시합니다.
# 만약 이미지가 있다면 st.image()를 사용하고, CSS로 위치 조정이 필요할 수 있습니다.
# Streamlit의 기본 레이아웃에서 absolute position은 사용하기 매우 어렵기 때문에,
# 만약 정확한 위치가 필요하다면, 이미지로 만들어서 삽입하고 margin 등으로 조정하는 것이 현실적입니다.
st.markdown('<div class="group-1-style"></div>', unsafe_allow_html=True)


st.write("") # 간격 추가
st.write("---") # 구분선 추가
st.header("앱 내용 시작")
st.write("이곳에 당신의 Streamlit 앱의 다른 요소들을 추가하세요.")

# 예시: 다른 위젯 추가
st.text_input("이름을 입력하세요:")
st.button("제출")
