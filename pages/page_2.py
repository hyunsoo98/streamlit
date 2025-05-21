import streamlit as st
import base64 # 이미지 Base64 인코딩용
import os # 파일 경로 확인용
import numpy as np # numpy 임포트

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

/* 원형 차트 SVG 컨테이너 */
.circle-chart-container {
    width: 325px; /* 원본 카드 너비에 맞춤 */
    height: 325px; /* 원본 카드 높이에 맞춤 */
    border-radius: 45px; /* 원본 카드 모서리 둥글게 */
    box-shadow: 3px 6px 10px 0px rgba(0, 0, 0, 0.1); /* 원본 카드 그림자 */
    background: #FFFFFF; /* 원본 카드 배경색 */
    
    display: flex; /* 내부 요소 중앙 정렬 */
    justify-content: center;
    align-items: center;
    position: relative; /* 내부 absolute 요소의 기준 */
    overflow: hidden; /* 넘치는 요소 숨기기 */
    margin-top: 20px; /* 상단 메뉴와의 간격 */
    margin-left: auto; /* 중앙 정렬 */
    margin-right: auto;
}

/* SVG 자체 스타일 */
.chart-svg {
    position: absolute; /* 컨테이너 내에서 절대 위치 */
    top: 50%; /* 중앙 정렬 */
    left: 50%; /* 중앙 정렬 */
    transform: translate(-50%, -50%); /* 정확한 중앙 정렬 */
    z-index: 1;
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

/* 각 등급 텍스트 (정상, 주의, 위험, 고위험) - SVG 내부에 직접 삽입 */
/* .level-text { ... } */

/* 포인터 아이콘 - SVG 내부에 직접 삽입 */
/* .pointer-icon { ... } */

/* 하단 설명 텍스트 */
.bottom-description-text {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 16px;
    font-weight: 400;
    text-align: center;
    margin-top: 20px; /* 차트와의 간격 */
    margin-bottom: 20px; /* 하단 여백 */
    width: 325px; /* 원본 카드 너비에 맞춰 */
    margin-left: auto; /* 중앙 정렬 */
    margin-right: auto;
}

</style>
""", unsafe_allow_html=True)


# --- SVG 차트 그리는 함수 ---
def create_circle_chart_svg(value_level="caution", pointer_base64=None):
    # 차트의 중심 좌표 및 반지름
    cx, cy, r = 125, 125, 100 # SVG viewBox가 250x250이므로 중심은 125,125

    # Helper to get point on circle
    def get_point(angle_deg, radius):
        # 0도 = 12시 방향에서 시작하도록 조정 (SVG의 0도는 3시 방향)
        angle_rad = (angle_deg - 90) * (np.pi / 180)
        x = cx + radius * np.cos(angle_rad)
        y = cy + radius * np.sin(angle_rad)
        return x, y

    sections = [
        {"color": "#38ADA9", "start_angle": 135, "end_angle": 225, "label": "정상", "text_pos_x": 50, "text_pos_y": 70},  # 정상 (상단 좌)
        {"color": "#F7D400", "start_angle": 45, "end_angle": 135, "label": "주의", "text_pos_x": 200, "text_pos_y": 70},   # 주의 (상단 우)
        {"color": "#F79C00", "start_angle": 315, "end_angle": 45, "label": "위험", "text_pos_x": 200, "text_pos_y": 180},   # 위험 (하단 우)
        {"color": "#FF4D4D", "start_angle": 225, "end_angle": 315, "label": "고위험", "text_pos_x": 50, "text_pos_y": 180}, # 고위험 (하단 좌)
    ]

    paths = []
    for section in sections:
        start_x, start_y = get_point(section["start_angle"], r)
        end_x, end_y = get_point(section["end_angle"], r)
        large_arc_flag = 1 if abs(section["end_angle"] - section["start_angle"]) % 360 > 180 else 0
        sweep_flag = 1 # 시계방향

        path_d = f"M {cx},{cy} L {start_x},{start_y} A {r},{r} 0 {large_arc_flag} {sweep_flag} {end_x},{end_y} Z"
        paths.append(f'<path d="{path_d}" fill="{section["color"]}" />')
    
    # 중앙에 흰색 원을 뚫어서 도넛 형태로 만듭니다.
    paths.append(f'<circle cx="{cx}" cy="{cy}" r="70" fill="#FFFFFF" />') # 중앙 흰색 원

    # 각 등급 텍스트를 SVG 내부에 직접 삽입
    for section in sections:
        paths.append(f'<text x="{section["text_pos_x"]}" y="{section["text_pos_y"]}" text-anchor="middle" fill="#333333" font-family="Poppins, sans-serif" font-size="14px" font-weight="500">{section["label"]}</text>')

    # 포인터 이미지 (SVG 내부에 <image> 태그로 삽입)
    # 포인터 위치는 '주의' (caution) 섹션에 고정
    if pointer_base64:
        # SVG 좌표계에 맞게 위치 조정
        # 원형 차트의 0,0이 SVG의 0,0이므로, 포인터도 그에 맞춰서 위치를 조정
        # '주의' 섹션은 대략 45도 ~ 135도. 포인터는 90도 방향 (12시 기준 3시)에 위치
        # 포인터 이미지의 중심이 해당 위치에 오도록 조정
        pointer_width = 30
        pointer_height = 30 # 이미지 비율에 따라 조절
        pointer_x = cx + r * np.cos((45 - 90) * (np.pi / 180)) - pointer_width / 2 # 45도 시작점에서 약간 안쪽
        pointer_y = cy + r * np.sin((45 - 90) * (np.pi / 180)) - pointer_height / 2 # 45도 시작점에서 약간 안쪽
        
        # 디자인 이미지와 유사하게 '주의' 섹션의 중간 지점 (90도)에 배치
        # 90도 (12시 기준 3시) 방향으로 포인터를 위치시키고 회전
        pointer_center_x, pointer_center_y = get_point(90, r + 10) # 반지름보다 조금 더 바깥에 배치
        
        paths.append(f'<image href="data:image/png;base64,{pointer_base64}" x="{pointer_center_x - pointer_width/2}" y="{pointer_center_y - pointer_height/2}" width="{pointer_width}" height="{pointer_height}" transform="rotate(45 {pointer_center_x} {pointer_center_y})" />') # 45도 회전
    
    svg_content = f"""
    <svg width="250" height="250" viewBox="0 0 250 250" class="chart-svg">
        {chr(10).join(paths)}
    </svg>
    """
    return svg_content

# --- Streamlit 앱 메인 로직 (이 페이지의 내용) ---
# 이 페이지는 로그인 정보가 필요 없으므로, 관련 변수 가져오기 및 로그인 확인 로직은 제거합니다.

# --- 상단 메뉴 ---
with st.container():
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.markdown('<div class="menu-icon">⬅️</div>', unsafe_allow_html=True) # 뒤로가기 아이콘
    with col2:
        st.markdown('<p class="menu-title-text">고혈압 등급</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">⋮</div>', unsafe_allow_html=True) # 더보기 아이콘

# --- 메인 카드 (이제는 원형 차트 컨테이너) 및 고혈압 등급 차트 ---
with st.container():
    # .main-card 스타일을 .circle-chart-container에 적용하여 사각형 역할을 겸하게 함
    # 이 컨테이너 자체가 카드 역할을 하며, 그 안에 SVG 차트가 들어감
    # CSS에서 .circle-chart-container에 box-shadow, border-radius, background 등을 추가
    st.markdown('<div class="circle-chart-container">', unsafe_allow_html=True)

    # 포인터 이미지 로드 (Base64)
    pointer_base64_data = None
    pointer_image_path = "pointer.png" # 포인터 이미지 파일 경로
    if os.path.exists(pointer_image_path):
        try:
            with open(pointer_image_path, "rb") as f:
                pointer_bytes = f.read()
            pointer_base64_data = base64.b64encode(pointer_bytes).decode("utf-8")
        except Exception as e:
            st.warning(f"포인터 이미지 '{pointer_image_path}' 로딩 오류: {e}")
    else:
        st.warning(f"포인터 이미지 파일 '{pointer_image_path}'을(를) 찾을 수 없습니다. 주의 등급 포인터가 표시되지 않습니다.")

    # 원형 차트 (SVG) - 포인터 Base64 데이터를 전달
    st.markdown(create_circle_chart_svg("caution", pointer_base64_data), unsafe_allow_html=True)

    # 중앙 텍스트 (SVG 위에 겹쳐지도록)
    st.markdown('<p class="chart-center-text">고혈압 지수</p>', unsafe_allow_html=True)

    # 등급 텍스트는 이제 SVG 내부에 있으므로 여기서는 제거
    # st.markdown('<p class="level-text normal">정상</p>', unsafe_allow_html=True)
    # st.markdown('<p class="level-text caution">주의</p>', unsafe_allow_html=True)
    # st.markdown('<p class="level-text warning">위험</p>', unsafe_allow_html=True)
    # st.markdown('<p class="level-text high-risk">고위험</p>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # circle-chart-container 닫기

# --- 하단 설명 텍스트 ---
st.markdown('<p class="bottom-description-text">고혈압 지수 주의 등급입니다.</p>', unsafe_allow_html=True)

st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")
