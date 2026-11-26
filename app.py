import streamlit as st
import pandas as pd
import random
import time

# ==========================================
# 1. 데이터 구조 (리스트 & 딕셔너리)
# ==========================================
sectors = ["직선 고속구간", "급커브 헤어핀", "빗길 슬릭", "최종 결승 직선"]
parts = ["구동 모터", "고전압 배터리", "인버터/제어기"]

motors_spec = {
    "IPMSM (영구자석 동기모터)": {"accel": 1.00, "max_spd": 310, "heat": 1.00, "desc": "균형 잡힌 표준 레이싱 모터"},
    "IM (유도전동기)": {"accel": 0.92, "max_spd": 335, "heat": 0.78, "desc": "열에 강하고 직선 최고속도가 높음"},
    "AFPM (축방향 자속 모터)": {"accel": 1.22, "max_spd": 295, "heat": 1.25, "desc": "초반 가속 폭발적, 온도가 빨리 오름"}
}

batteries_spec = {
    "NCM 811 (고출력 리튬이온)": {"cap": 100.0, "drain": 1.00, "regen": 1.00, "heat_stab": 1.00, "desc": "고출력 방전에 유리한 표준 배터리"},
    "LFP (리튬인산철)": {"cap": 95.0, "drain": 0.95, "regen": 0.95, "heat_stab": 0.72, "desc": "열 안정성이 매우 뛰어나 과열 방지"},
    "Solid-State (전고체 배터리)": {"cap": 115.0, "drain": 0.85, "regen": 1.45, "heat_stab": 0.85, "desc": "대용량(115%) 및 회생제동 충전 효율 극대화"}
}

inverters_spec = {
    "Si-IGBT (표준 인버터)": {"power": 1.00, "heat_red": 1.00, "regen_boost": 1.00, "desc": "기본 스위칭 전력 제어기"},
    "SiC-MOSFET (실리콘카바이드)": {"power": 1.08, "heat_red": 0.70, "regen_boost": 1.25, "desc": "발열 약 30% 감소 및 회생 효율 상승"},
    "Dual-Inverter 800V": {"power": 1.22, "heat_red": 1.12, "regen_boost": 1.10, "desc": "800V 승압으로 최고 출력 +22%"}
}

# random 라이브러리용 실시간 트랙 환경 변수
random_events = [
    ("순풍이 불어 공기저항이 줄었습니다!", 4.0, -0.4, 0.2),
    ("노면 온도가 최상이라 접지력이 좋습니다!", 2.0, 0.0, 0.0),
    ("맞바람이 불어 전력 소모가 증가합니다.", -4.0, 0.3, -0.3),
    ("앞차 난기류로 냉각 효율이 약간 떨어졌습니다.", -1.5, 0.6, -0.1),
    ("완벽한 주행 라인을 유지하고 있습니다!", 1.5, -0.2, 0.2)
]

# ==========================================
# 2. 상태 초기화 및 버튼 즉시 반응 콜백 함수 (def)
# ==========================================
def init_game():
    st.session_state.is_racing = False
    st.session_state.finished = False
    st.session_state.distance = 0.0        # 총 1200m 트랙
    st.session_state.elapsed_time = 0.0    # 주행 시간(초)
    st.session_state.speed = 0.0           # 현재 속도(km/h)
    st.session_state.motor_temp = 45.0     # 모터 온도(℃)
    st.session_state.battery = 100.0       # 배터리 잔량(%)
    st.session_state.score = 100           # 레이싱 점수
    
    # 실시간 운전 조작 상태 (ACCEL: 가속, REGEN: 회생제동, BOOST: 오버부스트, COAST: 탄력주행)
    st.session_state.pedal = "ACCEL"
    st.session_state.cooling = 2           # 1: ECO, 2: NORMAL, 3: MAX
    st.session_state.is_slipping = False   # 빗길 휠스핀 여부
    
    st.session_state.status_msg = "개러지에서 부품을 고른 뒤 '🏁 레이스 스타트!'를 누르면 차가 출발합니다!"
    st.session_state.event_msg = "실시간 텔레메트리 대기 중..."
    st.session_state.alert_level = "info"

def start_race():
    st.session_state.is_racing = True
    st.session_state.finished = False
    st.session_state.battery = batteries_spec[st.session_state.selected_battery]["cap"]
    st.session_state.pedal = "ACCEL"
    st.session_state.status_msg = "🚦 출발! 트랙 위치와 차량 상태를 보면서 페달과 냉각 시스템을 조작하세요!"

def set_pedal(mode):
    st.session_state.pedal = mode

def set_cooling(level):
    st.session_state.cooling = level

# ==========================================
# 3. 실시간 물리 엔진 업데이트 함수 (def + if-elif-else + random)
# ==========================================
def update_race_tick():
    m_spec = motors_spec[st.session_state.selected_motor]
    b_spec = batteries_spec[st.session_state.selected_battery]
    i_spec = inverters_spec[st.session_state.selected_inverter]
    
    dist = st.session_state.distance
    sec_idx = min(3, int(dist // 300))
    current_sector = sectors[sec_idx]
    
    pedal = st.session_state.pedal
    cool_lv = st.session_state.cooling
    st.session_state.is_slipping = False
    
    # 냉각 시스템 단계별 냉각량 및 배터리 소모량
    if cool_lv == 1:
        cool_effect, cool_drain = 0.35, 0.08
    elif cool_lv == 2:
        cool_effect, cool_drain = 0.95, 0.25
    else:
        cool_effect, cool_drain = 2.15, 0.65

    # random 라이브러리를 이용한 실시간 트랙 변수 적용
    if random.random() < 0.35:
        ev_text, ev_spd, ev_temp, ev_bat = random.choice(random_events)
        st.session_state.event_msg = ev_text
    else:
        ev_spd, ev_temp, ev_bat = 0.0, 0.0, 0.0

    spd = st.session_state.speed
    temp = st.session_state.motor_temp
    bat = st.session_state.battery
    score = st.session_state.score
    
    # 페달 조작에 따른 가속/감속/발열/충전 계산
    if pedal == "ACCEL":
        accel_force = 23.0 * m_spec["accel"] * i_spec["power"]
        spd = min(m_spec["max_spd"], spd + accel_force - (spd * 0.045) + ev_spd)
        temp += (2.1 * m_spec["heat"] * i_spec["heat_red"] * b_spec["heat_stab"]) - cool_effect + ev_temp
        bat -= (1.3 * b_spec["drain"] + cool_drain) - ev_bat
        msg = "⚡ 가속 페달(ACCEL) 작동 중 — 구동 모터에 전력을 공급해 가속합니다."
        level = "info"
        
    elif pedal == "BOOST":
        accel_force = 35.0 * m_spec["accel"] * i_spec["power"]
        spd = min(m_spec["max_spd"] + 25, spd + accel_force - (spd * 0.04) + ev_spd)
        temp += (3.8 * m_spec["heat"] * i_spec["heat_red"]) - cool_effect + ev_temp
        bat -= (2.4 * b_spec["drain"] + cool_drain) - ev_bat
        msg = "🔥 오버부스트(BOOST) 가동! 인버터 최대 출력으로 불꽃 가속 중!"
        level = "warning"
        
    elif pedal == "REGEN":
        spd = max(75.0, spd - 26.0 + ev_spd)
        charge = 1.75 * b_spec["regen"] * i_spec["regen_boost"]
        temp += 0.35 - cool_effect + ev_temp
        bat += charge - cool_drain + ev_bat
        msg = f"🔋 회생제동(REGEN) 작동! 감속 에너지를 전기로 바꿔 배터리를 충전 중 (+{charge:.1f}%)"
        level = "success"
        
    else:  # COAST (탄력주행)
        spd = max(65.0, spd - 9.0 + ev_spd)
        temp -= cool_effect
        bat -= cool_drain
        msg = "💨 탄력 주행(COAST) — 전력 차단으로 배터리 절약 및 모터 온도 냉각 중!"
        level = "info"

    # 조건문 (if-elif-else): 트랙 구간별 공학 규칙 및 페널티 판정
    if current_sector == "급커브 헤어핀":
        if pedal == "REGEN":
            bat += 0.9
            msg = "🏁 헤어핀 코너 회생제동 성공! 안정적인 코너링 + 배터리 추가 회수!"
            level = "success"
        elif spd > 205:
            spd *= 0.80
            score = max(0, score - 3)
            msg = "⚠️ 헤어핀 과속 진입! '🔋 회생제동' 버튼을 눌러 속도를 줄이세요!"
            level = "error"
            
    elif current_sector == "빗길 슬릭":
        # 빗길에서는 오버부스트나 과속 가속 시 휠스핀 발생 -> 탄력주행이나 회생제동으로 제어
        if pedal == "BOOST" or (pedal == "ACCEL" and spd > 220):
            if random.random() < 0.75:
                st.session_state.is_slipping = True
                spd *= 0.76
                score = max(0, score - 3)
                msg = "⚠️ 빗길 휠스핀(슬립) 발생! 타이어가 헛돕니다! '💨 탄력주행'이나 '🔋 회생제동'으로 감속하세요!"
                level = "error"
        else:
            msg = "✅ 빗길 트랙션 안정! 미끄러짐 없이 노면을 통과 중입니다."
            level = "success"

    # 모터 과열(95℃ 이상) 출력 제한 판정
    temp = max(35.0, temp + random.uniform(-0.3, 0.4))
    if temp >= 95.0:
        spd *= 0.78
        score = max(0, score - 2)
        msg = "🔥 모터 과열 경고(95℃ 초과)! 출력 제한 발동! 냉각 시스템을 '❄️ 3: MAX'로 올리세요!"
        level = "error"

    # 거리 및 시간 업데이트
    dt = 0.35
    moved = (spd * 0.145) + random.uniform(-0.5, 0.5)
    st.session_state.distance = min(1200.0, dist + max(5.0, moved))
    st.session_state.elapsed_time = round(st.session_state.elapsed_time + dt, 2)
    st.session_state.speed = round(spd, 1)
    st.session_state.motor_temp = round(temp, 1)
    st.session_state.battery = round(max(0.0, min(b_spec["cap"], bat)), 1)
    st.session_state.score = score
    st.session_state.status_msg = msg
    st.session_state.alert_level = level

    # 완주 또는 방전 종료 판정
    if st.session_state.battery <= 0:
        st.session_state.is_racing = False
        st.session_state.finished = True
        st.session_state.status_msg = "🪫 배터리 완전 방전(DNF)! 에너지 관리 실패로 레이스가 종료되었습니다."
        st.session_state.alert_level = "error"
    elif st.session_state.distance >= 1200.0:
        st.session_state.is_racing = False
        st.session_state.finished = True
        st.session_state.status_msg = f"🏆 1,200m 완주 성공! 최종 기록: {st.session_state.elapsed_time}초 / 점수: {st.session_state.score}점"
        st.session_state.alert_level = "success"

# ==========================================
# 4. 실시간 트랙 위치 + 버튼 조작에 따른 차량 상태 시각화 (SVG)
# ==========================================
def render_live_track_and_car(distance, speed, pedal, temp, cooling, is_slipping):
    # 전체 1,200m 트랙 위 차량 X좌표 (30px ~ 730px)
    car_x = 30 + (min(1200.0, distance) / 1200.0) * 700
    
    # 구간에 따라 차량의 상하(Y) 경로가 실제 트랙 모양(직선 -> 헤어핀 커브 -> 빗길 -> 결승선)을 따라 이동
    if distance < 300:
        car_y = 75
        sec_label = "① 직선 고속구간 (0~300m)"
    elif distance < 600:
        # 급커브 헤어핀 구간에서는 S자 곡선을 그리며 주행
        curve_ratio = (distance - 300) / 300.0
        car_y = 75 - 32 if curve_ratio < 0.5 else 75 + 32
        sec_label = "② 급커브 헤어핀 (300~600m)"
    elif distance < 900:
        car_y = 75 + (random.choice([-6, 6]) if is_slipping else 0)
        sec_label = "③ 빗길 슬릭 구간 (600~900m)"
    else:
        car_y = 75
        sec_label = "④ 최종 결승 직선 (900~1200m)"

    # 버튼을 누를 때마다 차량에 나타나는 시각 효과 생성
    effect_svg = ""
    car_body_color = "#0ea5e9"
    action_badge = "⚡ 가속 주행 중"

    if pedal == "ACCEL":
        car_body_color = "#0284c7"
        action_badge = "⚡ 가속 (전기 추진)"
        # 뒤쪽 전기 추진 파란 불꽃
        effect_svg += '<polygon points="-24,18 -4,10 -4,26" fill="#38bdf8" opacity="0.9"/>'
    elif pedal == "BOOST":
        car_body_color = "#ea580c"
        action_badge = "🔥 오버부스트 (최대출력)"
        # 뒤쪽 거대한 주황/노랑 부스터 불꽃
        effect_svg += '<polygon points="-42,18 -4,6 -4,30" fill="#f97316"/>'
        effect_svg += '<polygon points="-26,18 -4,12 -4,24" fill="#fde047"/>'
    elif pedal == "REGEN":
        car_body_color = "#16a34a"
        action_badge = "🔋 회생제동 (배터리 충전)"
        # 차량 주위 초록색 회생 충전 에너지 파동 + 앞쪽 브레이크 등
        effect_svg += '<rect x="-6" y="-4" width="60" height="44" rx="12" fill="none" stroke="#4ade80" stroke-width="3" stroke-dasharray="6,4"/>'
        effect_svg += '<rect x="46" y="4" width="4" height="28" fill="#ef4444"/>'
    elif pedal == "COAST":
        car_body_color = "#64748b"
        action_badge = "💨 탄력 주행 (전력 차단)"
        effect_svg += '<line x1="-22" y1="10" x2="-6" y2="10" stroke="#cbd5e1" stroke-width="2"/>'
        effect_svg += '<line x1="-28" y1="26" x2="-6" y2="26" stroke="#cbd5e1" stroke-width="2"/>'

    # 냉각 시스템 상태에 따른 차량 주변 냉각 기류 효과
    cool_badge = "❄️ 냉각: NORMAL"
    if cooling == 3:
        cool_badge = "❄️ 냉각: MAX (강력 냉각 중)"
        effect_svg += '<circle cx="24" cy="18" r="34" fill="none" stroke="#7dd3fc" stroke-width="2.5" stroke-dasharray="4,4"/>'
    elif cooling == 1:
        cool_badge = "❄️ 냉각: ECO (절전)"

    # 빗길 슬립 경고 표시
    if is_slipping:
        action_badge = "⚠️ 휠스핀(슬립) 미끄러짐!"
        effect_svg += '<text x="24" y="-12" fill="#f87171" font-size="12" font-weight="bold" text-anchor="middle">⚠️ SLIP!</text>'

    svg_html = f"""
<div style="background:#0f172a; border-radius:12px; padding:14px; border:2px solid #334155; margin-bottom:12px;">
  <div style="display:flex; justify-content:space-between; color:#e2e8f0; font-size:14px; font-weight:bold; margin-bottom:8px;">
    <span>📍 현재 위치: <span style="color:#38bdf8;">{int(distance)}m / 1,200m ({sec_label})</span></span>
    <span>🚗 차량 상태: <span style="color:#fbbf24;">{action_badge}</span> | <span style="color:#7dd3fc;">{cool_badge}</span></span>
  </div>
  <svg width="100%" height="165" viewBox="0 0 800 165">
    <!-- 4개 트랙 구간 배경 -->
    <rect x="0" y="25" width="200" height="120" fill="#1e293b" />
    <rect x="200" y="25" width="200" height="120" fill="#332618" />
    <rect x="400" y="25" width="200" height="120" fill="#132a46" />
    <rect x="600" y="25" width="200" height="120" fill="#1e293b" />

    <!-- 구간 상단 라벨 -->
    <text x="100" y="17" fill="#94a3b8" font-size="12" text-anchor="middle" font-weight="bold">① 직선 고속 (0~300m)</text>
    <text x="300" y="17" fill="#fbbf24" font-size="12" text-anchor="middle" font-weight="bold">② 급커브 헤어핀 (300~600m)</text>
    <text x="500" y="17" fill="#38bdf8" font-size="12" text-anchor="middle" font-weight="bold">③ 빗길 슬릭 (600~900m)</text>
    <text x="700" y="17" fill="#4ade80" font-size="12" text-anchor="middle" font-weight="bold">④ 결승 직선 (900~1200m)</text>

    <!-- 트랙 주행 도로선 (직선 -> S자 급커브 헤어핀 -> 빗길 -> 결승선) -->
    <path d="M 0 92 L 200 92 L 260 60 L 340 124 L 400 92 L 775 92" fill="none" stroke="#475569" stroke-width="44" stroke-linejoin="round"/>
    <path d="M 0 92 L 200 92 L 260 60 L 340 124 L 400 92 L 775 92" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="10,10"/>

    <!-- 빗길 구간 빗방울 표시 -->
    <text x="440" y="55" fill="#38bdf8" font-size="14">💧 💧 💧</text>
    <text x="520" y="135" fill="#38bdf8" font-size="14">💧 💧 💧</text>

    <!-- 결승선 체크무늬 -->
    <line x1="775" y1="30" x2="775" y2="140" stroke="#ffffff" stroke-width="6" stroke-dasharray="6,6"/>
    <text x="775" y="157" fill="#4ade80" font-size="11" text-anchor="middle" font-weight="bold">GOAL</text>

    <!-- 내 전기차(EV) 및 버튼 조작 이펙트 -->
    <g transform="translate({car_x}, {car_y})">
      {effect_svg}
      <!-- 타이어 4개 -->
      <rect x="6" y="-2" width="10" height="5" rx="2" fill="#0f172a"/>
      <rect x="32" y="-2" width="10" height="5" rx="2" fill="#0f172a"/>
      <rect x="6" y="33" width="10" height="5" rx="2" fill="#0f172a"/>
      <rect x="32" y="33" width="10" height="5" rx="2" fill="#0f172a"/>
      <!-- 차체 -->
      <rect x="0" y="2" width="48" height="32" rx="8" fill="{car_body_color}" stroke="#ffffff" stroke-width="2"/>
      <!-- 운전석 캐노피 -->
      <rect x="14" y="6" width="18" height="24" rx="4" fill="#0f172a"/>
      <!-- 실시간 속도 표시 -->
      <text x="24" y="52" fill="#ffffff" font-size="11" text-anchor="middle" font-weight="bold">{int(speed)} km/h</text>
    </g>
  </svg>
</div>
"""
    st.markdown(svg_html, unsafe_allow_html=True)

# ==========================================
# 5. 메인 화면 UI 구성
# ==========================================
st.set_page_config(page_title="하이퍼 EV 레이싱: 실시간 주행", page_icon="🏎️", layout="wide")

if "is_racing" not in st.session_state:
    init_game()

if st.session_state.is_racing and not st.session_state.finished:
    update_race_tick()

st.title("🏎️⚡ 하이퍼 EV 레이싱: 파워트레인 마스터")

# [1] 개러지 부품 선택 (주행 시작 시 자동 잠금)
disabled_flag = st.session_state.is_racing or st.session_state.finished
lock_status = "🔒 LOCKED (주행 중 교체 불가)" if disabled_flag else "🔓 OPEN (출발 전 부품 세팅)"
st.caption(f"🛠️ **개러지 파워트레인 세팅:** `{lock_status}`")

g1, g2, g3 = st.columns(3)
with g1:
    st.selectbox("구동 모터", list(motors_spec.keys()), key="selected_motor", disabled=disabled_flag)
with g2:
    st.selectbox("고전압 배터리", list(batteries_spec.keys()), key="selected_battery", disabled=disabled_flag)
with g3:
    st.selectbox("인버터 제어기", list(inverters_spec.keys()), key="selected_inverter", disabled=disabled_flag)

# [2] 트랙 구간별 엔지니어 전략 무전 가이드
dist = st.session_state.distance
if st.session_state.motor_temp >= 85:
    st.error("🚨 [엔지니어 긴급 무전] 모터 온도 85℃ 돌파! 지금 즉시 '❄️ 3: MAX 냉각' 버튼을 누르세요!")
elif dist < 300:
    st.info("📡 [① 직선 고속구간] '⚡ 가속' 또는 '🔥 오버부스트'를 눌러 최고 속도로 치고 나가세요!")
elif dist < 600:
    st.warning("📡 [② 급커브 헤어핀] 코너 진입! 지금 '🔋 회생제동'을 눌러 감속하면서 배터리를 충전하세요!")
elif dist < 900:
    st.warning("📡 [③ 빗길 슬릭 구간] 노면이 미끄럽습니다! 오버부스트를 끄고 '💨 탄력주행'이나 '🔋 회생제동'으로 미끄러짐을 막으세요!")
else:
    st.success("📡 [④ 최종 결승 직선] 결승선까지 전력 질주! '🔥 오버부스트'로 마지막 스퍼트를 내세요!")

# [3] 실시간 주행 트랙 위치 & 차량 변화 시각화 화면
render_live_track_and_car(
    st.session_state.distance,
    st.session_state.speed,
    st.session_state.pedal,
    st.session_state.motor_temp,
    st.session_state.cooling,
    st.session_state.is_slipping
)

# [4] 운전석 조작 패널 (페달 4종 + 냉각 3단계만 깔끔하게 배치)
ctrl_col, status_col = st.columns([1.15, 1.0])

with ctrl_col:
    st.subheader("🎮 실시간 운전석 컨트롤")
    
    top_b1, top_b2 = st.columns(2)
    with top_b1:
        st.button(
            "🏁 레이스 스타트! (주행 시작)",
            on_click=start_race,
            type="primary",
            disabled=disabled_flag,
            use_container_width=True
        )
    with top_b2:
        st.button("🔄 개러지로 복귀 (리셋)", on_click=init_game, use_container_width=True)

    st.markdown("**1️⃣ 주행 페달 조작 (누르면 차의 움직임과 이펙트가 즉시 바뀝니다)**")
    p1, p2, p3, p4 = st.columns(4)
    p1.button("⚡ 가속", on_click=set_pedal, args=("ACCEL",), use_container_width=True)
    p2.button("🔋 회생제동", on_click=set_pedal, args=("REGEN",), use_container_width=True)
    p3.button("🔥 오버부스트", on_click=set_pedal, args=("BOOST",), use_container_width=True)
    p4.button("💨 탄력주행", on_click=set_pedal, args=("COAST",), use_container_width=True)

    st.markdown("**2️⃣ 냉각 시스템 출력 (모터 과열 방지)**")
    c1, c2, c3 = st.columns(3)
    c1.button("❄️ 1: ECO (절전)", on_click=set_cooling, args=(1,), use_container_width=True)
    c2.button("❄️ 2: NORMAL", on_click=set_cooling, args=(2,), use_container_width=True)
    c3.button("❄️ 3: MAX (최대냉각)", on_click=set_cooling, args=(3,), use_container_width=True)
    
    with st.expander("💡 냉각 시스템이 뭔가요?"):
        st.write("전기모터에 큰 전류가 흐르면 열이 발생해 온도가 오릅니다. **95℃**를 넘으면 부품 보호를 위해 출력이 줄어드므로, 온도가 오르면 **❄️ 3: MAX**를 눌러 냉각 팬과 워터펌프를 최대로 가동해 식혀주세요!")

with status_col:
    st.subheader("📊 실시간 계기판 & 전장 부품 진단")
    
    if st.session_state.alert_level == "error":
        st.error(st.session_state.status_msg)
    elif st.session_state.alert_level == "warning":
        st.warning(st.session_state.status_msg)
    elif st.session_state.alert_level == "success":
        st.success(st.session_state.status_msg)
    else:
        st.info(st.session_state.status_msg)
        
    st.caption(f"🎲 **실시간 트랙 변수 (random):** {st.session_state.event_msg}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("⏱️ 랩타임", f"{st.session_state.elapsed_time}초")
    m2.metric("📏 주행거리", f"{int(st.session_state.distance)}m")
    m3.metric("🌡️ 모터온도", f"{st.session_state.motor_temp}℃")
    m4.metric("🏆 점수", f"{st.session_state.score}점")

    # 반복문 (for): 전장 부품 리스트를 순회하며 상태 테이블 생성
    diag_rows = []
    pedal_names = {"ACCEL": "가속 주행", "REGEN": "회생제동", "BOOST": "오버부스트", "COAST": "탄력 주행"}
    for part in parts:
        if part == "구동 모터":
            load_s = pedal_names[st.session_state.pedal]
            vt_s = f"{st.session_state.motor_temp}℃"
            st_s = "🔥 과열주의" if st.session_state.motor_temp >= 85 else ("⚡ 고출력" if st.session_state.pedal in ["ACCEL", "BOOST"] else "✅ 정상")
        elif part == "고전압 배터리":
            load_s = f"{st.session_state.battery}%"
            volt = random.randint(355, 370) if st.session_state.battery < 20 else random.randint(396, 405)
            if "800V" in st.session_state.selected_inverter:
                volt *= 2
            vt_s = f"{volt}V"
            st_s = "🔋 회생충전" if st.session_state.pedal == "REGEN" else ("🪫 저전압" if st.session_state.battery < 20 else "✅ 정상")
        elif part == "인버터/제어기":
            cool_names = {1: "ECO", 2: "NORMAL", 3: "MAX"}
            load_s = f"냉각 {cool_names[st.session_state.cooling]}"
            vt_s = "정상"
            st_s = "❄️ 최대냉각" if st.session_state.cooling == 3 else "✅ 안정"
            
        diag_rows.append({"전장 부품": part, "작동 상태": load_s, "온도/전압": vt_s, "진단 결과": st_s})
        
    st.table(pd.DataFrame(diag_rows))

# ==========================================
# 6. 실시간 자동 주행 루프 (0.35초마다 화면 자동 갱신)
# ==========================================
if st.session_state.is_racing and not st.session_state.finished:
    time.sleep(0.35)
    st.rerun()
