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

/* 하단 설명 텍스트 (새로운 위치 및 스타일) */
.bottom-description-text-new {
    color: #333333;
    font-family: "Poppins", sans-serif;
    font-size: 16px;
    font-weight: 400;
    text-align: left; /* 왼쪽 정렬로 변경 */
    position: absolute; /* 절대 위치 */
    top: 60%; /* 차트의 중앙보다 아래 */
    left: 10%; /* 왼쪽 여백 */
    width: 150px; /* 텍스트 너비 */
    transform: translateY(-50%); /* 세로 중앙 정렬 */
    z-index: 2; /* 차트 위에 오도록 */
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
        {"color": "#F7D400", "start_angle": 0, "end_angle": 90, "label": "주의", "text_angle": 45, "min_val": 0.59, "max_val": 0.74},     # 주의 (우상단)
        {"color": "#38ADA9", "start_angle": 90, "end_angle": 180, "label": "정상", "text_angle": 135, "min_val": 0.0, "max_val": 0.59},   # 정상 (좌상단)
        {"color": "#FF4D4D", "start_angle": 180, "end_angle": 270, "label": "고위험", "text_angle": 225, "min_val": 0.89, "max_val": 1.0}, # 고위험 (좌하단)
        {"color": "#F79C00", "start_angle": 270, "end_angle": 360, "label": "위험", "text_angle": 315, "min_val": 0.74, "max_val": 0.89},   # 위험 (우하단)
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
    # prediction_value를 각도로 매핑 (0.0 -> 180도, 1.0 -> 0도, 즉 0.0~1.0을 0도~360도로 변환)
    # 차트의 시작 각도를 0도(3시 방향)로 설정했으므로, 0.0 (정상) -> 135도, 1.0 (고위험) -> 225도로 매핑.
    # 단순화: 0.0~1.0의 확률 값을 90도(정상) ~ 270도(고위험) 범위에 매핑.
    # 즉, 0.0이 90도, 1.0이 270도. 중간값 0.5가 180도.
    # `np.interp`를 사용하여 확률 값을 각도 범위로 선형 매핑
    
    # 0.0 (정상) -> 135도 (정상 영역 중앙)
    # 0.59 (주의-정상 경계) -> 90도
    # 0.74 (주의-위험 경계) -> 0도 (또는 360도)
    # 0.89 (위험-고위험 경계) -> 270도 (고위험 영역 중앙)

    # 새로운 이미지의 포인터 위치를 기준으로 매핑합니다.
    # 정상(0.0)이 135도, 주의(0.74)가 45도, 위험(0.89)이 315도, 고위험(1.0)이 225도
    # 예시 임계값:
    # 0.0 ~ 0.59 (정상): 135도에서 90도 사이
    # 0.59 ~ 0.74 (주의): 90도에서 0도 사이
    # 0.74 ~ 0.89 (위험): 360도에서 270도 사이 (270도에서 360도)
    # 0.89 ~ 1.0 (고위험): 270도에서 180도 사이

    # 확률 값에 따른 각도 계산
    # 예측값(prediction_value)이 0.0~1.0 사이라고 가정
    # 예시 매핑:
    # 0.0 -> 150도 (정상 중앙보다 약간 위)
    # 0.25 -> 100도 (정상과 주의 사이)
    # 0.5 -> 50도 (주의 중앙)
    # 0.75 -> 0도 (위험과 주의 경계)
    # 1.0 -> 330도 (위험 중앙)
    
    # 더 정확한 매핑을 위해 각 레벨의 임계값을 사용합니다.
    # 각 섹션의 중간 각도를 기준으로 확률에 따라 보간합니다.
    # (주의) prediction_value를 이 각도에 매핑하는 것은 모델의 출력 분포와 각 섹션의 의미를 정확히 알아야 가능합니다.
    # 여기서는 간단히 0.0에서 1.0까지를 전체 원형 차트의 360도 범위에 매핑하거나, 특정 구간에 매핑합니다.
    
    # 예시: 0.0 (정상) -> 135도, 1.0 (고위험) -> 225도 (전체 180도 범위)
    # 이 경우 '주의'나 '위험'이 정확히 중간에 오지 않을 수 있습니다.
    # 가장 자연스러운 것은 0.0이 정상의 시작, 1.0이 고위험의 끝으로 매핑되는 것입니다.
    # 차트의 시작이 0도 (주의 시작), 끝이 360도 (위험 끝)
    # 0.0이 정상의 시작(90도), 1.0이 고위험의 끝(270도)으로 가정합니다.
    # 즉, 0.0 ~ 1.0의 값을 90도 ~ 270도 (반시계 방향) 또는 270도 ~ 90도 (시계 방향)으로 매핑.
    # 여기서 각도는 시계방향으로 0도가 3시.
    # 정상 (90~180) -> 0.0 ~ 0.59
    # 주의 (0~90) -> 0.59 ~ 0.74
    # 위험 (270~360) -> 0.74 ~ 0.89
    # 고위험 (180~270) -> 0.89 ~ 1.0

    # 포인터가 전체 원을 도는 것으로 가정하고, 0.0을 135도, 1.0을 225도로 설정합니다.
    # (예측 확률이 0.0일 때 '정상' 중앙, 1.0일 때 '고위험' 중앙)
    # 각도를 조절하여 포인터가 '주의' 부분에 오도록 합니다.
    # 현재 이미지에 '주의' 위치에 포인터가 있으므로, 대략 45도 방향에 고정하거나,
    # prediction_value를 받아 해당 각도를 계산하여 동적으로 움직이게 할 수 있습니다.

    # 임시로 '주의' 위치에 고정된 화살표를 그립니다. (이전 pointer.png 위치와 유사)
    # 실제 prediction_value에 따라 움직이게 하려면, prediction_value를 적절한 각도 범위로 매핑해야 합니다.
    # 예를 들어, prediction_value가 0.5~0.74 일 때 '주의' 영역에 위치하도록 각도를 계산합니다.
    
    # 간단한 예시: 모든 확률 값을 0도(오른쪽)에서 270도(아래)까지 매핑 (반시계 방향)
    # 실제로는 각 등급별 확률 범위와 차트의 각도를 고려하여 복잡한 매핑이 필요합니다.
    # 지금은 '주의' 등급이므로, 대략 45도에 포인터가 오도록 설정합니다.
    
    # 화살표의 중앙점 (차트의 중앙)
    arrow_cx, arrow_cy = cx, cy
    arrow_length = r - 20 # 화살표가 중앙 원까지 닿지 않도록 길이 조절

    # 포인터의 끝이 가리킬 각도 (차트 이미지에서 '주의' 위치와 일치하도록 45도)
    # 이 각도를 prediction_value에 따라 동적으로 계산해야 합니다.
    # 여기서는 예시로 45도를 사용합니다. (prediction_value가 '주의' 범위에 있을 때)
    
    # 실제 앱에서는 prediction_value와 등급 임계값을 사용하여 각도를 계산해야 합니다.
    # 예시:
    # if risk_level == "정상": target_angle = np.interp(prediction_proba, [0.0, 0.59], [150, 90])
    # elif risk_level == "주의": target_angle = np.interp(prediction_proba, [0.59, 0.74], [90, 0]) # 0도는 3시 방향
    # elif risk_level == "위험": target_angle = np.interp(prediction_proba, [0.74, 0.89], [360, 270])
    # else: # 고위험
    #     target_angle = np.interp(prediction_proba, [0.89, 1.0], [270, 180])

    # 현재 이미지에서는 포인터가 '주의' 위치에 있으므로, 대략 45도 방향으로 고정하여 표시합니다.
    pointer_angle = 45 # Default to '주의' angle for demonstration
    
    # 화살표 끝 지점 계산
    end_x, end_y = get_arc_point(pointer_angle, arrow_length)

    # 화살표 SVG (삼각형 머리 포함)
    # 'arrow_path'는 화살표의 몸통과 머리 부분을 SVG path로 정의합니다.
    # 몸통은 가운데 원과 가까운 점에서 시작하여 바깥쪽으로 향하게 합니다.
    # 삼각형 머리는 화살표 끝에 위치하고, 회전 각도에 따라 함께 회전합니다.
    
    # 화살표 몸통 시작점 (중앙 원의 반지름보다 약간 더 나가도록)
    start_point_arrow_x, start_point_arrow_y = get_arc_point(pointer_angle, 75) # 중앙 원의 반지름 70보다 약간 크게

    # 화살표 끝점 (원의 테두리보다 약간 안쪽 또는 바깥쪽)
    end_point_arrow_x, end_point_arrow_y = get_arc_point(pointer_angle, r + 5) # 원의 반지름보다 약간 바깥쪽

    # 화살표 머리 (삼각형)의 크기
    arrowhead_size = 15 # 화살표 머리 크기 조절

    # 화살표 머리 경로 (시작점, 좌우점)
    # 화살표 끝점을 기준으로 회전하여 그립니다.
    # 삼각형 머리는 화살표 방향(pointer_angle)에 맞춰 회전해야 합니다.
    # 0도(3시 방향)를 기준으로 화살표 머리가 오른쪽을 가리키는 삼각형을 그리고,
    # 이 삼각형을 `pointer_angle`에 맞춰 회전시킵니다.
    # 삼각형의 꼭지점은 end_point_arrow_x, end_point_arrow_y
    # 삼각형의 다른 두 점은 꼬리 방향으로 arrowhead_size만큼 떨어져 있고, perpendicular하게 벌어집니다.
    
    # 화살표 머리의 회전 중심은 화살표 끝점
    # 화살표는 가리키는 방향의 반대쪽(뒤쪽)을 향해야 하므로, pointer_angle + 180도
    # (SVG path의 rotate 변환은 시계방향)
    
    # 삼각형 꼭지점 (화살표 끝)
    tip_x, tip_y = end_point_arrow_x, end_point_arrow_y

    # 화살표 머리 베이스의 중앙점 (팁에서 arrowhead_size만큼 뒤로)
    base_center_x, base_center_y = get_arc_point(pointer_angle + 180, arrowhead_size) # 팁에서 반대 방향으로 이동
    
    # 화살표 머리 베이스의 양 끝점 (중앙점에서 수직 방향으로 벌어짐)
    # 회전된 좌표를 계산해야 함
    base_angle_perp1 = pointer_angle + 90
    base_angle_perp2 = pointer_angle - 90

    base_p1_x, base_p1_y = get_arc_point(base_angle_perp1, arrowhead_size / 2)
    base_p2_x, base_p2_y = get_arc_point(base_angle_perp2, arrowhead_size / 2)
    
    # 이 방식은 복잡하니, 간단하게 path를 회전시키는 방식으로 구현합니다.
    # 기본 화살표 머리 (오른쪽을 가리키는 삼각형)를 정의하고, 나중에 회전시킵니다.
    # 팁: (1, 0), 좌상: (0, 0.5), 좌하: (0, -0.5) 크기를 15x15로 가정.
    arrowhead_path_d = f"M {arrowhead_size},0 L 0,{arrowhead_size/2} L 0,{-arrowhead_size/2} Z"
    
    paths.append(f"""
        <line x1="{start_point_arrow_x}" y1="{start_point_arrow_y}" x2="{end_point_arrow_x}" y2="{end_point_arrow_y}" stroke="#333333" stroke-width="2" />
        <path d="{arrowhead_path_d}" fill="#333333" 
              transform="translate({tip_x}, {tip_y}) rotate({pointer_angle} 0 0)" />
    """) # 화살표는 검정색으로 지정

    # 현재 등급 텍스트 표시 (차트 밖 왼쪽에 위치)
    texts.append(f'<text x="0" y="{cy + 20}" text-anchor="start" fill="#333333" font-family="Poppins, sans-serif" font-size="16px" font-weight="400">고혈압 지수 {current_level_text} 등급</text>')


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
        # "뒤로가기" 아이콘 제거
        pass
    with col2:
        st.markdown('<p class="menu-title-text">고혈압 등급</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="menu-icon">⋮</div>', unsafe_allow_html=True) # 더보기 아이콘

# --- 고혈압 등급 차트 및 텍스트 ---
with st.container():
    # .circle-chart-container가 이제 카드 역할과 차트 컨테이너 역할을 겸함
    st.markdown('<div class="circle-chart-container">', unsafe_allow_html=True)

    # 이전에 pointer.png를 로드하던 로직은 제거합니다.
    # 대신 `create_circle_chart_svg` 함수에 직접 예측값과 현재 등급 텍스트를 전달합니다.
    
    # 예측값은 모델로부터 받아와야 하지만, 여기서는 예시 값을 사용합니다.
    # 실제 앱에서는 이 값을 `page_1.py`에서 전달받아 사용해야 합니다.
    example_prediction_proba = 0.65 # '주의' 범위 내의 예시 값
    example_risk_level = "주의" # `classify_risk_level` 함수로 얻은 결과

    # 원형 차트 (SVG) - 예측값과 현재 등급 텍스트를 전달
    st.markdown(create_circle_chart_svg(prediction_value=example_prediction_proba, current_level_text=example_risk_level), unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # circle-chart-container 닫기

# 기존 하단 설명 텍스트 제거
# st.markdown('<p class="bottom-description-text">고혈압 지수 주의 등급입니다.</p>', unsafe_allow_html=True)

st.markdown("---")
st.write("이 애플리케이션은 Streamlit 디자인 테스트용입니다.")
