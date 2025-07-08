from typing import Any, AsyncGenerator, Dict, Optional
from src.agents.graph import graph


def resolve_event_message(event: dict[str, Any]) -> Dict[str, Any] | None:
    """
    이벤트(event) 정보를 바탕으로 사용자에게 보여줄 메시지를 반환합니다.

    Args:
        node_name (str): LangGraph 노드 이름 (예: "gen_script", "gen_video" 등)
        event (dict): 발생한 이벤트 정보 (이벤트 타입, 툴 이름 등 포함)

    Returns:
        Dict[str, Any] | None: 구조화된 메시지 딕셔너리. 해당 이벤트에 해당하는 메시지가 없으면 None.
    """
    node_name = event["metadata"].get("langgraph_node", "")
    event_name = event.get("name", "")
    event_type = event.get("event", "")
    event_data = event.get("data", {})

    # 노드별로 출력할 메시지 정의
    node_messages = {
        "prep_material": {
            "on_chain_start": {"message": "🔄 자료를 준비하는 중..."},
            "on_tool_start:get_lecture_data": {
                "message": "🔄 강의 자료를 가져오는 중..."
            },
            "on_tool_start:read_pdf": {"message": "🔄 PDF 자료를 읽는 중..."},
            "on_tool_start:web_search": {"message": "🔄 웹 검색 중..."},
            "on_tool_end:get_lecture_data": {"message": "✅ 강의 자료 가져오기 완료."},
            "on_tool_end:read_pdf": {"message": "✅ PDF 자료 읽기 완료."},
            "on_tool_end:web_search": {"message": "✅ 웹 검색 완료."},
            "on_chain_end": {
                "message": "✅ 자료 준비 완료.",
                # "data": lambda x: x["output"]["materials"],
            },
        },
        "gen_script": {
            "on_chain_start:gen_script": {"message": "🔄 스크립트를 생성하는 중..."},
            "on_chain_end:gen_script": {
                "message": "✅ 스크립트 생성 완료.",
                "data": lambda x: x["output"]["scripts"],
            },
        },
        "gen_audio": {
            "on_chain_start:gen_audio": {"message": "🔄 오디오를 생성하는 중..."},
            "on_chain_end:gen_audio": {
                "message": "✅ 오디오 생성 완료.",
                "data": lambda x: x["output"]["paths"],
            },
        },
        "gen_image": {
            "on_chain_start:gen_image": {"message": "🔄 이미지를 생성하는 중..."},
            "on_chain_end:gen_image": {
                "message": "✅ 이미지 생성 완료.",
                "data": lambda x: x["output"]["paths"],
            },
        },
        "gen_video": {
            "on_chain_start:gen_video": {"message": "🔄 비디오를 생성하는 중..."},
            "on_chain_end:gen_video": {
                "message": "✅ 비디오 생성 완료.",
                "data": lambda x: x["chunk"]["paths"],
            },
        },
    }

    # 해당 노드에 등록된 메시지 목록 가져오기
    node_events = node_messages.get(node_name, {})

    # 툴 이름이 포함된 이벤트 key가 존재하면 사용 (예: on_tool_start:read_pdf)
    # 아니면 이벤트 타입만 사용 (예: on_chain_start)
    key = (
        f"{event_type}:{event_name}"
        if f"{event_type}:{event_name}" in node_events
        else event_type
    )

    # 매칭되는 메시지 찾기
    msg_config = node_events.get(key)

    if msg_config is None:
        return None

    # 메시지가 함수형이면 실행해서 결과 반환
    if isinstance(msg_config, dict):
        data_func = msg_config.get("data")
        extracted_data = data_func(event_data) if callable(data_func) else None
        message_text = msg_config.get("message")
    else:
        message_text = msg_config
        extracted_data = None

    return {
        "node": node_name,
        "event_name": event_name,
        "event_type": event_type,
        "message": message_text,
        "data": extracted_data,
    }


async def run_graph(input_data: dict) -> AsyncGenerator[Dict[str, Any], None]:
    """
    그래프 진행 중 발생하는 이벤트 메시지를 실시간으로 yield(반환)하는 비동기 제너레이터입니다.
    Streamlit에서 처리하기 쉬운 구조화된 메시지를 반환합니다.

    Args:
        input_data (dict): 그래프에 전달할 사용자 입력 데이터

    Yields:
        Dict[str, Any]: 구조화된 진행 상황 메시지
        {
            "event_type": str,       # 이벤트 타입 (on_chain_start, on_tool_end 등)
            "name": str,             # 툴/체인 이름
            "node": str,             # 노드 이름
            "message": str,          # 사용자에게 보여줄 메시지
            "data": Any,             # 추출된 데이터 (있는 경우)
        }
    """
    config = {
        "configurable": {"thread_id": "chat_id"},
        "recursion_limit": 10,
    }

    # 그래프 실행 이벤트를 실시간으로 받아옴
    async for event in graph.astream_events(input_data, config=config):

        # 메시지 추출
        msg = resolve_event_message(event)

        # 메시지 전달 (유효한 메시지만)
        if msg and msg.get("message"):
            yield msg

    # 최종 완료 메시지
    yield {
        "event_type": "completion",
        "name": "final",
        "node": "final",
        "message": "✅ 모든 작업이 완료되었습니다.",
        "data": None,
    }
