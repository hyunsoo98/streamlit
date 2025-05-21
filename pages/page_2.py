import streamlit as st
import base64 # 이미지 Base64 인코딩용
import os # 파일 경로 확인용

# --- CSS 추가 (이 페이지 전용) ---
st.markdown("""
<style>
/* 이 페이지의 CSS는 app.py의 전역 CSS와 병합됩니다. */

/* 상단 메뉴 (back, title, more) */
.top-menu-container {
    width: 325px;
    height: 45px;
    display: flex;
    flex-direction: row;
    justify-content: space-between; /* 양 끝 정렬 */
    align-items: center;
    column-gap: 15px;
    margin-top: 20px; /* 상단 여백 조절 */
    margin-left: auto;
    margin-right: auto;
    /* max-width를 설정하여 중앙에 고정된 너비로 보이게 할 수도 있습니다. */
}
.menu-icon {
    width: 45px;
    height: 45px;
    display: flex; /* 아이콘을 flexbox로 감싸서 중앙 정렬 */
    justify-content: center;
    align-items: center;
    font-size: 24px; /* 이모지 크기 조절 */
    color: #333333; /* 아이콘 색상 */
    cursor: pointer;
}
.menu-title-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 20px;
    line-height: 23.4px;
    font-weight: 600;
    text-align: center;
    flex-grow: 1; /* 남은 공간을 채워 제목을 중앙으로 밀어냄 */
}

/* 메인 카드 (사각형) */
.main-card {
    width: 325px; /* 원본 디자인과 유사한 너비 */
    height: 325px; /* 원형 차트가 들어갈 충분한 공간 */
    box-shadow: 3px 6px 10px 0px rgba(0, 0, 0, 0.1); /* 약한 그림자 */
    border-radius: 45px;
    background: #FFFFFF;
    margin-top: 20px; /* 상단 메뉴와의 간격 */
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    position: relative; /* 내부 absolute 요소의 기준 */
    overflow: hidden; /* 넘치는 요소 숨기기 */
}

/* 원형 차트 SVG 컨테이너 */
.circle-chart-container {
    width: 250px; /* 원형 차트의 전체 너비 */
    height: 250px; /* 원형 차트의 전체 높이 */
    position: relative; /* 내부 텍스트 및 포인터의 기준 */
    display: flex;
    justify-content: center;
    align-items: center;
}

/* 원형 차트의 중앙 텍스트 */
.chart-center-text {
    position: absolute;
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 32px; /* 고혈압 지수 텍스트 크기 */
    font-weight: 600;
    text-align: center;
    z-index: 2; /* SVG 위에 표시되도록 */
}

/* 각 등급 텍스트 (정상, 주의, 위험, 고위험) */
.level-text {
    position: absolute;
    font-family: "Poppins", sans-serif;
    font-size: 14px;
    font-weight: 500;
    color: #333333;
    white-space: nowrap;
    z-index: 2;
}
.level-text.normal { top: 35px; left: 35px; color: #38ADA9; } /* 정상 (Green) */
.level-text.caution { top: 35px; right: 35px; color: #F7D400; } /* 주의 (Yellow) */
.level-text.warning { bottom: 35px; right: 35px; color: #F79C00; } /* 위험 (Orange) */
.level-text.high-risk { bottom: 35px; left: 35px; color: #FF4D4D; } /* 고위험 (Red) */


/* 포인터 아이콘 */
.pointer-icon {
    position: absolute;
    width: 30px; /* 포인터 이미지 크기 조절 */
    height: auto;
    transform: rotate(45deg); /* '주의' 위치에 맞게 회전 */
    transform-origin: center;
    /* 정확한 위치는 이미지 크기와 SVG 차트 크기에 따라 조절 */
    top: 70px; /* 대략적인 위치 */
    right: 65px; /* 대략적인 위치 */
    z-index: 3; /* 가장 위에 표시되도록 */
}

/* 하단 설명 텍스트 */
.bottom-description-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 16px;
    font-weight: 400;
    text-align: center;
    margin-top: 20px; /* 카드와의 간격 */
    margin-bottom: 20px; /* 하단 여백 */
}

</style>
""", unsafe_allow_html=True)


# --- SVG 차트 그리는 함수 ---
def create_circle_chart_svg(value_level="caution"):
    # SVG 차트 데이터 (각 섹션의 색상 및 각도)
    # 총 360도에서 4개 구간
    # 정상: 90도 (초록)
    # 주의: 90도 (노랑)
    # 위험: 90도 (주황)
    # 고위험: 90도 (빨강)

    # 차트의 중심 좌표 및 반지름
    cx, cy, r = 125, 125, 100

    # 각 섹션의 시작 각도 (시계방향으로)
    # 0도 = 3시 방향, 90도 = 6시 방향
    # 정상 (시작: 135도, 끝: 225도)
    # 주의 (시작: 45도, 끝: 135도)
    # 위험 (시작: -45도, 끝: 45도) 또는 (315도, 45도)
    # 고위험 (시작: 225도, 끝: 315도)

    # SVG Path for arcs (D = "M startX startY A r r 0 large-arc-flag sweep-flag endX endY")
    # large-arc-flag: 0 for less than 180, 1 for more than 180
    # sweep-flag: 0 for counter-clockwise, 1 for clockwise

    # Helper to get point on circle
    def get_point(angle_deg, radius):
        angle_rad = (angle_deg - 90) * (3.1415926535 / 180) # 0도 = 12시 방향에서 시작하도록 조정
        x = cx + radius * np.cos(angle_rad)
        y = cy + radius * np.sin(angle_rad)
        return x, y

    sections = [
        {"color": "#38ADA9", "start_angle": 135, "end_angle": 225, "label": "정상"},  # 정상 (상단 좌)
        {"color": "#F7D400", "start_angle": 45, "end_angle": 135, "label": "주의"},   # 주의 (상단 우)
        {"color": "#F79C00", "start_angle": 315, "end_angle": 45, "label": "위험"},   # 위험 (하단 우)
        {"color": "#FF4D4D", "start_angle": 225, "end_angle": 315, "label": "고위험"}, # 고위험 (하단 좌)
    ]

    paths = []
    for section in sections:
        start_x, start_y = get_point(section["start_angle"], r)
        end_x, end_y = get_point(section["end_angle"], r)
        large_arc_flag = 1 if (section["end_angle"] - section["start_angle"]) % 360 > 180 else 0
        
        path_d = f"M {cx},{cy} L {start_x},{start_y} A {r},{r} 0 {large_arc_flag} 1 {end_x},{end_y} Z"
        paths.append(f'<path d="{path_d}" fill="{section["color"]}" />')
    
    # 중앙에 흰색 원을 뚫어서 도넛 형태로 만듭니다.
    paths.append(f'<circle cx="{cx}" cy="{cy}" r="70" fill="#FFFFFF" />') # 중앙 흰색 원

    svg_content = f"""
    <svg width="250" height="250" viewBox="0 0 250 250" style="position: absolute;">
        {chr(10).join(paths)}
    </svg>
    """
    return svg_content

# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---

# --- 상단 메뉴 ---
with st.container():
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.markdown('<div class="menu-icon">⬅️</div>', unsafe_allow_html=True) # 뒤로가기 아이콘
    with col2:
        st.markdown('<p class="menu-title-text">고혈압 등급</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">⋮</div>', unsafe_allow_html=True) # 더보기 아이콘

# --- 메인 카드 및 고혈압 등급 차트 ---
with st.container():
    st.markdown('<div class="main-card">', unsafe_allow_html=True)

    # 원형 차트 (SVG)
    st.markdown(create_circle_chart_svg("caution"), unsafe_allow_html=True) # '주의' 레벨을 기본으로

    # 중앙 텍스트
    st.markdown('<p class="chart-center-text">고혈압 지수</p>', unsafe_allow_html=True)

    # 각 등급 텍스트
    st.markdown('<p class="level-text normal">정상</p>', unsafe_allow_html=True)
    st.markdown('<p class="level-text caution">주의</p>', unsafe_allow_html=True)
    st.markdown('<p class="level-text warning">위험</p>', unsafe_allow_html=True)
    st.markdown('<p class="level-text high-risk">고위험</p>', unsafe_allow_html=True)

    # 포인터 (이미지 파일이 필요)
    pointer_image_path = "pointer.png" # 포인터 이미지 파일 경로
    if os.path.exists(pointer_image_path):
        try:
            with open(pointer_image_path, "rb") as f:
                pointer_bytes = f.read()
            pointer_base64 = base64.b64encode(pointer_bytes).decode("utf-8")
            st.markdown(
                f"""
                <img src="data:image/png;base64,{pointer_base64}" class="pointer-icon">
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.warning(f"포인터 이미지 '{pointer_image_path}' 로딩 오류: {e}")
    else:
        st.warning(f"포인터 이미지 파일 '{pointer_image_path}'을(를) 찾을 수 없습니다. 주의 등급 포인터가 표시되지 않습니다.")

    st.markdown('</div>', unsafe_allow_html=True) # main-card 닫기

# --- 하단 설명 텍스트 ---
st.markdown('<p class="bottom-description-text">고혈압 지수 주의 등급입니다.</p>', unsafe_allow_html=True)

st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")
