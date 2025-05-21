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
# prediction_value는 0.0 ~ 1.0 사이의 값으로 가정합니다.
def create_circle_chart_svg(prediction_value=0.5, current_level_text="주의"):
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
        
        # "정상" 텍스트의 y 위치 미세 조정 (이전 요청에서 유지)
        if section["label"] == "정상":
            text_y -= 5 # 약간 위로 이동
        
        texts.append(f'<text x="{text_x}" y="{text_y}" text-anchor="middle" fill="#333333" font-family="Poppins, sans-serif" font-size="14px" font-weight="500">{section["label"]}</text>')

    # 중앙에 흰색 원을 뚫어서 도넛 형태로 만듭니다.
    paths.append(f'<circle cx="{cx}" cy="{cy}" r="70" fill="#FFFFFF" />') # 중앙 흰색 원

    # 중앙 "고혈압 지수" 텍스트
    texts.append(f'<text x="{cx}" y="{cy + 10}" text-anchor="middle" fill="#333333" font-family="Poppins, sans-serif" font-size="32px" font-weight="600">고혈압 지수</text>')

    # 화살표 그리기 (예측값에 따라 회전)
    # prediction_value를 각도로 매핑
    # 이 각도 매핑은 실제 모델의 예측 확률과 차트의 섹션에 따라 정밀하게 조정되어야 합니다.
    # 여기서는 예시 값을 사용하여 임시로 '주의' 위치 (45도)를 가리키도록 설정합니다.
    
    # 예측값을 0.0 ~ 1.0 범위로 가정하고, 이를 0도 ~ 360도 범위로 매핑합니다.
    # 예를 들어, 0.0을 135도 (정상 영역의 왼쪽), 1.0을 225도 (고위험 영역의 오른쪽)로 매핑하여
    # 화살표가 반시계 방향으로 움직이도록 할 수 있습니다.
    # 또는 0.0을 90도 (정상과 주의 경계), 1.0을 270도 (고위험과 위험 경계)로 매핑.
    
    # 현재 이미지에 맞추기 위해 '주의' 위치(45도)에 화살표가 고정되어 나타나도록 설정합니다.
    pointer_angle_deg = 45 # 예시: '주의' 영역의 중심 각도

    # 화살표 몸통 시작점 (중앙 원의 반지름보다 약간 더 나가도록)
    start_point_arrow_x, start_point_arrow_y = get_arc_point(pointer_angle_deg, 75) 

    # 화살표 끝점 (원의 테두리보다 약간 바깥쪽)
    end_point_arrow_x, end_point_arrow_y = get_arc_point(pointer_angle_deg, r + 5) 

    # 화살표 머리 (삼각형) 크기
    arrowhead_size = 15 

    # 화살표 몸통 (선)
    paths.append(f"""
        <line x1="{start_point_arrow_x}" y1="{start_point_arrow_y}" 
              x2="{end_point_arrow_x}" y2="{end_point_arrow_y}" 
              stroke="#333333" stroke-width="2" stroke-linecap="round" />
    """)

    # 화살표 머리 (삼각형)
    # 기본 삼각형을 (0,0)에 꼭지점을 두고 왼쪽으로 향하게 정의합니다.
    # M 0,0 L -size,-size/2 L -size,size/2 Z
    arrowhead_path_d = f"M 0,0 L {-arrowhead_size},{-(arrowhead_size/2)} L {-arrowhead_size},{arrowhead_size/2} Z"
    
    # 화살표 머리의 회전은 `pointer_angle_deg`에 맞춰져야 합니다.
    # `transform` 속성을 사용하여 끝점으로 이동(translate)한 다음 회전(rotate)합니다.
    paths.append(f"""
        <path d="{arrowhead_path_d}" fill="#333333" 
              transform="translate({end_point_arrow_x}, {end_point_arrow_y}) rotate({pointer_angle_deg})" />
    """)

    # 현재 등급 텍스트 표시 (차트 밖 왼쪽에 위치)
    # x 좌표를 좀 더 중앙에 가깝게 조정 (기존 0에서 20으로 변경)
    texts.append(f'<text x="20" y="{cy + 20}" text-anchor="start" fill="#333333" font-family="Poppins, sans-serif" font-size="16px" font-weight="400">고혈압 지수 {current_level_text} 등급입니다.</text>')


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
        # "뒤로가기" 아이콘 제거: pass 대신 빈 문자열로 대체
        st.markdown("")
    with col2:
        st.markdown('<p class="menu-title-text">고혈압 등급</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">⋮</div>', unsafe_allow_html=True) # 더보기 아이콘

# --- 고혈압 등급 차트 및 텍스트 ---
with st.container():
    # .circle-chart-container가 이제 카드 역할과 차트 컨테이너 역할을 겸함
    st.markdown('<div class="circle-chart-container">', unsafe_allow_html=True)

    # 포인터 이미지를 로드하던 로직은 제거합니다.
    # 대신 `create_circle_chart_svg` 함수에 직접 예측값과 현재 등급 텍스트를 전달합니다.
    
    # 예측값은 모델로부터 받아와야 하지만, 여기서는 예시 값을 사용합니다.
    # 실제 앱에서는 이 값을 `page_1.py`에서 전달받아 사용해야 합니다.
    example_prediction_proba = 0.65 # '주의' 범위 내의 예시 값
    example_risk_level = "주의" # `classify_risk_level` 함수로 얻은 결과

    # 원형 차트 (SVG) - 예측값과 현재 등급 텍스트를 전달
    st.markdown(create_circle_chart_svg(prediction_value=example_prediction_proba, current_level_text=example_risk_level), unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # circle-chart-container 닫기

# 기존 하단 설명 텍스트 제거 (SVG 내로 이동했음)

st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")
