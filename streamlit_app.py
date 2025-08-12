import streamlit as st
import asyncio
import re

from src.agents.clipgen import run_graph


st.set_page_config(page_title="ClipGen-AI", layout="wide")

st.markdown("## 🎬 ClipGen-AI: 숏폼 콘텐츠 생성기")

# ---- 3분할 레이아웃 ----
col1, col2, col3 = st.columns([1.0, 1.5, 1.5])  # 비율 조절 가능

# --- 1번 영역: 입력 영역 ---
with col1:
    st.markdown("### 📥 입력")

    # 주제 (필수)
    topic = st.text_input("주제 *", placeholder="예: 파이썬 기초 프로그래밍")
    if not topic:
        st.error("주제를 입력해주세요.")

    # 결과 타입
    output_type = st.selectbox("결과 타입", ["script", "audio", "video"])

    # 언어 선택
    language = st.selectbox(
        "언어",
        ["Korean", "English"],
        index=0,  # 기본값으로 한국어 선택
    )

    # 스타일
    st.markdown("**스타일**")
    roles = ["강사", "유튜버", "전문가", "진행자", "기타", "랜덤"]
    selected_roles = st.multiselect(
        "역할: 최대 2명의 화자 선택 가능",
        roles,
        default=["강사"],  # 디폴트 값 설정
        max_selections=2,
    )

    if "기타" in selected_roles:
        custom_style = st.text_input("기타 역할 입력")
        if custom_style:
            selected_roles = [s for s in selected_roles if s != "기타"] + [custom_style]

    # 스타일이 선택되지 않은 경우 에러 메시지 표시
    if not selected_roles:
        st.error("최소 1명의 화자를 선택해주세요.")

    # 맞춤 설정
    custom_setting = st.text_area(
        "맞춤 설정",
        placeholder="예시) 내용: 핵심 개념 3가지를 중심으로 초보자도 이해하기 쉽게 설명\n스타일: 친근하고 대화하듯이, 예시를 많이 들어서 설명",
        height=70,
    )

    st.markdown("#### 📚 자료")

    # 텍스트 직접 입력
    user_text = st.text_area("텍스트 입력", height=100)

    # PDF 업로드 (최대 5개)
    pdf_files = st.file_uploader(
        "PDF 업로드 (최대 5개)", type=["pdf"], accept_multiple_files=True
    )

    # PDF 파일 개수 제한
    if pdf_files and len(pdf_files) > 5:
        st.error("PDF 파일은 최대 5개까지 업로드 가능합니다.")
        pdf_files = pdf_files[:5]  # 처음 5개만 유지

    # 웹 검색 체크박스
    use_web_search = st.checkbox("웹 검색 포함")

    # 자료 입력 검증
    has_material = bool(user_text or pdf_files or use_web_search)
    if not has_material:
        st.error("자료를 하나 이상 입력해주세요. (텍스트, PDF, 웹 검색 중 선택)")

    st.divider()

    # 생성 버튼 (필수 조건 만족시에만 활성화)
    can_generate = bool(topic and has_material and selected_roles)
    generate = st.button("🚀 생성하기", disabled=not can_generate)

    if not can_generate and st.session_state.get("button_clicked", False):
        if not topic:
            st.warning("주제를 입력해주세요.")
        if not has_material:
            st.warning("자료를 하나 이상 선택해주세요.")
        if not selected_roles:
            st.warning("최소 1명의 화자를 선택해주세요.")

    # 버튼 클릭 상태 저장 및 데이터 처리
    if generate:
        st.session_state["button_clicked"] = True

        # PDF 파일 처리
        pdf_paths = []
        if pdf_files:
            import os
            import uuid

            # UUID 생성 및 폴더 생성
            session_uuid = str(uuid.uuid4())
            logs_dir = os.path.join("logs", session_uuid)
            os.makedirs(logs_dir, exist_ok=True)

            for pdf_file in pdf_files:
                # 파일 저장
                file_path = os.path.join(logs_dir, pdf_file.name)
                with open(file_path, "wb") as f:
                    f.write(pdf_file.getbuffer())
                pdf_paths.append(file_path)

            st.success(f"{len(pdf_files)}개의 PDF 파일이 업로드되었습니다.")

        # input_data 생성
        input_data = {
            "user_input": {
                "topic": topic,
                "roles": selected_roles,
                "custom_setting": custom_setting,
                "language": language,
                "output_type": output_type,
                "pdf_paths": pdf_paths,
                "text": user_text,
                "enable_web_search": use_web_search,
            },
        }

        # input_data를 세션 상태에 저장
        st.session_state["input_data"] = input_data

# --- 2번 영역: 스크립트 출력 ---
with col2:
    st.markdown("### 📄 스크립트")

    # 스크립트 생성 영역
    script_container = st.container(height=1000, border=True)
    with script_container:
        script_message_placeholder = st.empty()
        script_result_placeholder = st.empty()

    # 초기 상태 표시
    if not st.session_state.get("button_clicked", False):
        script_result_placeholder.info(
            "입력창에 정보를 입력하고 '생성하기'를 눌러주세요. 이곳에는 생성된 스크립트가 표시됩니다."
        )

# --- 3번 영역: 스튜디오 (오디오 / 비디오) ---
with col3:
    st.markdown("### 🎧 스튜디오")

    # 오디오 영역
    audio_container = st.container(height=235, border=True)
    with audio_container:
        st.markdown("#### 🔊 오디오")
        audio_placeholder = st.empty()

    # 비디오 영역
    video_container = st.container(height=750, border=True)
    with video_container:
        st.markdown("#### 🎥 비디오")
        video_placeholder = st.empty()

    # 초기 상태 표시
    if not st.session_state.get("button_clicked", False):
        audio_placeholder.info("오디오 생성 결과가 여기에 표시됩니다.")
        video_placeholder.info("비디오 생성 결과가 여기에 표시됩니다.")

# 생성 프로세스 실행
if generate and "input_data" in st.session_state:
    input_data = st.session_state["input_data"]

    async def display_progress():
        async for msg in run_graph(input_data):
            node = msg["node"]
            message = msg["message"]

            if node == "prep_material":
                # 자료 준비 단계 - 2번 영역 (자료 준비)
                script_message_placeholder.info(message)

            elif node == "gen_script":
                # 스크립트 생성 단계 - 2번 영역 (스크립트)
                script_message_placeholder.info(message)
                if msg.get("data") is not None:
                    # 스크립트 결과 출력
                    script_result_placeholder.markdown(msg["data"])

            elif node == "gen_audio":
                # 오디오 생성 단계 - 3번 영역 (오디오)
                audio_placeholder.info(message)
                if msg.get("data") is not None:
                    # 실제 오디오 파일이 있다면 st.audio() 사용
                    # audio_placeholder.audio(msg["data"])
                    pass

            elif node == "gen_image":
                # 이미지 생성 단계 - 3번 영역 (이미지)
                video_placeholder.info(message)
                if msg.get("data") is not None:
                    # 실제 이미지 파일이 있다면 st.image() 사용
                    # image_placeholder.image(msg["data"])
                    pass

            elif node == "gen_video":
                # 비디오 생성 단계 - 3번 영역 (비디오)
                video_placeholder.info(message)
                if msg.get("data") is not None:
                    # 실제 비디오 파일이 있다면 st.video() 사용
                    # video_placeholder.video(msg["data"])
                    pass

    # 비동기 함수 실행
    asyncio.run(display_progress())
