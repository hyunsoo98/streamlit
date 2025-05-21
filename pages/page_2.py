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

/* 원형 차트 SVG 컨테이너 (이제 이 자체가 카드 역할) */
.circle-chart-container {
    width: 325px; /* 원본 디자인과 유사한 너비 */
    height: 325px; /* 원본 디자인과 유사한 높이 */
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

    # Helper to get point on circle (for arc start/end)
    def get_arc_point(angle_deg, radius):
        # SVG의 0도는 3시 방향, 각도는 시계방향으로 증가
        angle_rad = np.deg2rad(angle_deg)
        x = cx + radius * np.cos(angle_rad)
        y = cy + radius * np.sin(angle_rad)
        return x, y

    # Helper to get text label point (for text positioning)
    def get_text_point(angle_deg, radius_offset):
        # 0도 = 3시 방향, 각도는 시계방향으로 증가
        angle_rad = np.deg2rad(angle_deg)
        x = cx + (r + radius_offset) * np.cos(angle_rad)
        y = cy + (r + radius_offset) * np.sin(angle_rad)
        return x, y

    # 섹션 정의 (시작 각도, 끝 각도 - 시계방향, 3시 방향이 0도)
    sections = [
        {"color": "#F7D400", "start_angle": 0, "end_angle": 90, "label": "주의", "text_angle": 45},     # 주의 (우상단)
        {"color": "#38ADA9", "start_angle": 90, "end_angle": 180, "label": "정상", "text_angle": 135},   # 정상 (좌상단)
        {"color": "#FF4D4D", "start_angle": 180, "end_angle": 270, "label": "고위험", "text_angle": 225}, # 고위험 (좌하단)
        {"color": "#F79C00", "start_angle": 270, "end_angle": 360, "label": "위험", "text_angle": 315},   # 위험 (우하단)
    ]

    paths = []
    texts = []
    
    # 각 섹션 그리기
    for section in sections:
        start_x, start_y = get_arc_point(section["start_angle"], r)
        end_x, end_y = get_arc_point(section["end_angle"], r)
        
        # 각도가 180도 이상이면 large-arc-flag = 1
        large_arc_flag = 1 if (section["end_angle"] - section["start_angle"]) > 180 else 0
        sweep_flag = 1 # 시계방향

        path_d = f"M {cx},{cy} L {start_x},{start_y} A {r},{r} 0 {large_arc_flag} {sweep_flag} {end_x},{end_y} Z"
        paths.append(f'<path d="{path_d}" fill="{section["color"]}" />')
        
        # 등급 텍스트 위치 계산 및 삽입 (원의 바깥쪽)
        text_offset_r = 20 # 원 반지름 + 텍스트와의 간격
        text_x, text_y = get_text_point(section["text_angle"], text_offset_r)
        texts.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" fill="#333333" font-family="Poppins, sans-serif" font-size="14px" font-weight="500">{section["label"]}</text>')

    # 중앙에 흰색 원을 뚫어서 도넛 형태로 만듭니다.
    paths.append(f'<circle cx="{cx}" cy="{cy}" r="70" fill="#FFFFFF" />') # 중앙 흰색 원

    # 중앙 "고혈압 지수" 텍스트
    texts.append(f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" fill="#333333" font-family="Poppins, sans-serif" font-size="32px" font-weight="600">고혈압 지수</text>')

    # 포인터 이미지 (SVG 내부에 <image> 태그로 삽입)
    # 포인터 위치는 '주의' (caution) 섹션의 중간 (45도)에 고정
    if pointer_base64:
        pointer_width = 30
        pointer_height = 30 
        
        # 포인터의 중심이 45도 방향 (주의 섹션 중간)에 위치하도록
        pointer_pos_x, pointer_pos_y = get_arc_point(45, r + 10) # 원 반지름보다 약간 바깥에
        
        # 포인터 이미지의 회전 (디자인 이미지에 맞춰 조절)
        # 45도 방향을 가리키려면 이미지 자체의 방향에 따라 회전 각도 조절 필요
        # 이미지에 따라 -45, 0, 45, 90 등 다양하게 시도
        rotation_angle = 45 # 시계방향 45도 회전 (이미지 모양에 따라 다름)
        
        paths.append(f'<image href="data:image/png;base64,{pointer_base64}" x="{pointer_pos_x - pointer_width/2}" y="{pointer_pos_y - pointer_height/2}" width="{pointer_width}" height="{pointer_height}" transform="rotate({rotation_angle} {pointer_pos_x} {pointer_pos_y})" />')
    
    svg_content = f"""
    <svg width="250" height="250" viewBox="0 0 250 250" class="chart-svg">
        {chr(10).join(paths)}
        {chr(10).join(texts)}
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

# --- 고혈압 등급 차트 및 텍스트 ---
with st.container():
    # .circle-chart-container가 이제 카드 역할과 차트 컨테이너 역할을 겸함
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

    # 중앙 텍스트 및 등급 텍스트는 이제 SVG 내부에 있으므로 여기서는 제거
    # st.markdown('<p class="chart-center-text">고혈압 지수</p>', unsafe_allow_html=True)
    # st.markdown('<p class="level-text normal">정상</p>', unsafe_allow_html=True)
    # ...

    st.markdown('</div>', unsafe_allow_html=True) # circle-chart-container 닫기

# --- 하단 설명 텍스트 ---
st.markdown('<p class="bottom-description-text">고혈압 지수 주의 등급입니다.</p>', unsafe_allow_html=True)

st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")

