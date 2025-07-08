from typing import Union
import json

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate

from src.agents.state import InputState, OverallState, OutputState
from src.agents.tools.read_pdf import ReadPdfTool
from src.agents.tools.web_search import WebSearchTool
from src.agents.prompt import SCRIPT_GENERATE_PROMPT
from src.utils import (
    get_openai_chat_llm_client,
    save_json,
    extract_json_from_response,
    log_info,
    log_error,
)

llm_client = get_openai_chat_llm_client()
# =========================
# 노드 정의
# =========================


async def prep_material(state: InputState) -> OverallState:
    """
    자료를 준비하는 노드입니다.
    - 강의 자료
    - PDF 자료
    - 웹 검색 자료
    - 텍스트 자료
    """

    # ToolNode 설정
    tool_node = ToolNode([ReadPdfTool(), WebSearchTool()])

    # 사용자 입력 추출
    user_input = state["user_input"]
    topic = user_input["topic"]
    pdf_paths = user_input["pdf_paths"]
    enable_web_search = user_input["enable_web_search"]
    text = user_input["text"]

    # 결과 초기화
    pdf_data, search_data = [], []

    # Tool 호출 구성
    tool_calls = []
    if pdf_paths:
        tool_calls.append(
            {
                "name": "read_pdf",
                "args": {"pdf_paths": pdf_paths},
                "id": "pdf_paths_tool_call_id",
                "type": "tool_call",
            }
        )
    print(f"Tool calls: {tool_calls}")

    # Tool 호출 실행
    if tool_calls:
        tool_msg = AIMessage(content="", tool_calls=tool_calls)
        response = await tool_node.ainvoke({"messages": [tool_msg]})
        for i, call in enumerate(tool_calls):
            tool_result = json.loads(response["messages"][i].content)
            if call["name"] == "read_pdf":
                pdf_data = tool_result

    # 웹 검색
    if enable_web_search:
        search_call = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "web_search",
                    "args": {
                        "topic": topic,
                        "data": pdf_data,
                        "llm": llm_client,
                    },
                    "id": "web_search_tool_call_id",
                    "type": "tool_call",
                }
            ],
        )
        response = await tool_node.ainvoke({"messages": [search_call]})
        search_data = json.loads(response["messages"][0].content)

    # Post-process: 자료 타입 지정 및 인용 번호 추가
    for d in pdf_data:
        d["type"] = "pdf"
    for d in search_data:
        d["type"] = "web_search"

    text_data = []
    if text:
        text_data = [{"title": "사용자 입력 텍스트", "content": text, "type": "text"}]

    # 전체 자료 통합
    materials = pdf_data + search_data + text_data
    for i, material in enumerate(materials):
        material["number"] = i

    # 상태 업데이트
    state["materials"] = materials

    return state


def gen_script(state: OverallState) -> OverallState:
    """스크립트를 생성하는 노드입니다."""

    try:
        # 체인 생성
        prompt = ChatPromptTemplate(
            input_variables=["materials", "input"],
            messages=[
                SystemMessagePromptTemplate.from_template(SCRIPT_GENERATE_PROMPT)
            ],
        )
        chain = prompt | llm_client  # TODO: llm 클라이언트 따로 관리

        # 체인 실행
        script_input = {
            "topic": state["user_input"]["topic"],
            "roles": state["user_input"]["roles"],
            "custom_setting": state["user_input"]["custom_setting"],
        }
        materials = state["materials"]
        res = chain.invoke({"input": script_input, "materials": materials})
        result = extract_json_from_response(res.content)
        log_info("Generated script:")
        log_info(result)

    except Exception as e:
        log_error(f"Error gen_script: {str(e)}")
        result = {}

    # 스크립트 저장
    # path = f"data/output/{id}/scripts.json" # TODO: uuid로 변경 필요
    path = f"data/output/scripts.json"
    save_json(path=path, data=result)

    # 상태 업데이트
    state["scripts"] = result
    state["paths"] = {"scripts": path}

    return state


def gen_audio(state: OverallState) -> OverallState:
    """
    오디오를 생성하는 노드입니다.
    - TTS를 사용하여 스크립트로부터 오디오 생성
    """

    state["paths"] = {"audio": ["/paths/to/audio_1.mp3"]}
    return state


async def gen_image(state: OverallState) -> OverallState:
    """
    이미지를 생성하는 노드입니다.
    - 스크립트로부터 이미지 생성
    """

    # 상태 업데이트
    state["paths"] = {"images": ["/path/to/image_1.png", "/path/to/image_2.png"]}
    return state


async def gen_video(state: OverallState) -> OverallState:
    """
    비디오를 생성하는 노드입니다.
    - 비디오 랜더링: 자막 + 오디오 + 이미지
    """

    # 상태 업데이트
    state["paths"] = {"video": "/path/to/video_1.mp4"}
    return state


# =========================
# 그래프 정의
# =========================


builder = StateGraph(OverallState, input=InputState, output=OverallState)

# ===== 그래프 노드 추가 =====
builder.add_node("prep_material", prep_material)
builder.add_node("gen_script", gen_script)
builder.add_node("gen_audio", gen_audio)
builder.add_node("gen_image", gen_image)
builder.add_node("gen_video", gen_video)


# ===== 라우팅 함수 정의 =====
def route_gen_script(
    state: OverallState,
) -> Union[str, list[str]]:
    """
    스크립트 생성 후 다음 노드로 라우팅합니다.
    """
    output_type = state["user_input"]["output_type"]
    if output_type == "script":
        return END
    elif output_type == "audio":
        return "gen_audio"  # 오디오 생성 노드로 이동
    elif output_type == "video":
        return ["gen_audio", "gen_image"]  # 오디오, 이미지 생성 노드 병렬 실행
    else:
        return END


def route_gen_audio(
    state: OverallState,
) -> Union[str, list[str]]:
    """
    오디오 생성 후 다음 노드로 라우팅합니다.
    """
    output_type = state["user_input"]["output_type"]
    if output_type == "audio":
        return END
    elif output_type == "video":
        return "gen_video"  # gen_image와 병렬로 실행되었으므로, gen_video로 이동
    else:
        return END


# ===== 그래프 엣지 추가 =====
builder.add_edge(START, "prep_material")
builder.add_edge("prep_material", "gen_script")

gen_script_intermediates = [END, "gen_audio", "gen_image"]
builder.add_conditional_edges("gen_script", route_gen_script, gen_script_intermediates)

gen_script_intermediates = [END, "gen_video"]
builder.add_conditional_edges("gen_audio", route_gen_audio, gen_script_intermediates)
builder.add_edge("gen_image", "gen_video")
builder.add_edge("gen_video", END)


# ===== 그래프 컴파일 =====
graph = builder.compile()
graph.name = "ClipGen"
