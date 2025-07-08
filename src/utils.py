import errno
import logging
import os
from os.path import dirname, abspath, join
import signal
import json
from functools import wraps
from textwrap import dedent as dedent_
from functools import wraps
import yaml
from glob import glob
from easydict import EasyDict
from elasticsearch import Elasticsearch, AsyncElasticsearch
from langchain_openai import AzureChatOpenAI
from langchain_openai import ChatOpenAI
import tiktoken
import re

from src.config import cfg


# ==================================================
PROJECT_ROOT = dirname(abspath(dirname(__file__)))
# ==================================================


# ==================================================
# Logger
# ==================================================

logger = logging.getLogger()

logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def disable_logger():
    logger.setLevel(logging.WARNING)


def log_step(logger, step_str):
    logger.info("-" * 50)
    logger.info(" > {}".format(step_str))
    logger.info("-" * 50)


def slog(
    msg: str,
    style: str = "BLUE",
    log: str = "info",
    dump: bool = True,
    notify_slack: bool = False,
) -> str:
    """Stylish log message.

    Args:
        msg (str): The message to log.
        color (str): The color of the message. Defaults to "BLUE".
        log (str): The log level. Defaults to "info".
        dump (bool): The dump flag. Defaults to True.

    Returns:
        str: The stylish message.
    """
    styles = {
        "ENDC": "\033[0m",
        "OKBLUE": "\033[94m",
        "OKCYAN": "\033[96m",
        "OKGREEN": "\033[92m",
        "BOLD": "\033[1m",
        "UNDERLINE": "\033[4m",
        "BLUE": "\033[34m",
        "RED": "\033[31m",
        "GREEN": "\033[32m",
        "ORANGE": "\033[33m",
        "PURPLE": "\033[35m",
        "CYAN": "\033[36m",
        "LIGHTGRAY": "\033[37m",
        "DARKGRAY": "\033[90m",
        "LIGHTRED": "\033[91m",
        "YELLOW": "\033[93m",
        "PINK": "\033[95m",
        "DARKORANGE": "\033[38;5;214m",
        "GRAPEFRUIT": "\033[38;5;208m",
    }
    try:
        if dump:
            msg = pretty_dict(msg)
            msg = msg.strip('"')  # remove redundant quotes
    except:
        pass

    if style:
        stylish_msg = f"{styles[style]}{msg}{styles['ENDC']}"
    else:
        stylish_msg = msg

    if log == "info":
        logger.info(stylish_msg)
    elif log == "warning":
        if notify_slack:
            logger.warning(stylish_msg)
        else:
            logger.warning(stylish_msg)
    elif log == "error":
        if notify_slack:
            logger.error(stylish_msg)
        else:
            logger.error(stylish_msg)
    elif log == "critical":
        logger.critical(stylish_msg)
    else:
        print(stylish_msg)

    return stylish_msg


def log_info(msg: str, dump: bool = True) -> None:
    """Stylish info log.

    Args:
        msg (str): The message to log.
        dump (bool): The dump flag. Defaults to True.
    """
    slog(msg, style="GREEN", dump=dump)


def log_warning(msg: str, dump: bool = False, prefix: bool = True) -> str:
    """Stylish warning log.

    Args:
        msg (str): The message to log.
        dump (bool): The dump flag.
        prefix (bool): The prefix flag.
        notify_slack (bool): The notify slack flag.
    """
    if prefix:
        msg = f"[WARNING] {msg}"
    return slog(msg, style="GRAPEFRUIT", log="warning", dump=dump)


def log_error(msg: str, dump: bool = False) -> None:
    """Stylish error log.

    Args:
        msg (str): The message to log.
        dump (bool): The dump flag. Defaults to False.
        notify_slack (bool): The notify slack flag. Defaults to False.
    """
    slog(msg, style="GRAPEFRUIT", log="error", dump=dump)


# ==================================================
# Clients
# ==================================================


class ClientManager:
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(ClientManager, cls).__new__(cls)
        return cls.instance


client_manager = ClientManager()


def get_es_client():
    es = Elasticsearch(
        cloud_id=cfg.es.cloud_id,
        basic_auth=(cfg.es.http_auth.id, cfg.es.http_auth.pw),
        connections_per_node=30,
        max_retries=2,
        retry_on_timeout=True,
        http_compress=True,
    )

    return es


def get_async_es_client():
    es = AsyncElasticsearch(
        cloud_id=cfg.es.cloud_id,
        basic_auth=(cfg.es.http_auth.id, cfg.es.http_auth.pw),
        connections_per_node=30,
        max_retries=2,
        retry_on_timeout=True,
        http_compress=True,
    )

    return es


def get_azure_chat_llm_client():
    key = "AzureChatOpenAI"
    if not hasattr(client_manager, key):
        llm = AzureChatOpenAI(
            azure_endpoint=cfg.azure.openai_eastus.api_base,
            openai_api_key=cfg.azure.openai_eastus.api_key,
            deployment_name=cfg.azure.openai_eastus.llm_deployment,
            model=cfg.azure.openai_eastus.llm_model,
            openai_api_version=cfg.azure.openai_eastus.api_version,
            max_tokens=cfg.azure.openai_eastus.llm_max_tokens,
            max_retries=0,
            temperature=0,
        )
        setattr(client_manager, key, llm)
    return getattr(client_manager, key)

def get_openai_chat_llm_client():
    key = "ChatOpenAI"
    if not hasattr(client_manager, key):
        chat_llm = ChatOpenAI(
            model=cfg.openai.llm_model,
            max_tokens=cfg.openai.llm_max_tokens,
            api_key=cfg.openai.api_key,
            temperature=0,
        )
        setattr(client_manager, key, chat_llm)
    return getattr(client_manager, key)


# ==================================================
# General util
# ==================================================


def dedent(text: str) -> str:
    return dedent_(text)


def load_yamls(dir_path: str, easy_dict=True) -> list[dict]:
    yamls = []
    for path in glob(join(PROJECT_ROOT, dir_path, "*.yaml")):
        yaml: list[dict] = load_yaml(path, easy_dict)
        yamls.extend(yaml)
    return yamls


def load_yaml(path: str, easy_dict=True) -> dict:
    with open(join(PROJECT_ROOT, path)) as f:
        cfg = yaml.safe_load(f)
    if easy_dict:
        return EasyDict(cfg)
    else:
        return cfg


def pretty_dict(s: str) -> str:
    """Pretty print dictionary.

    Args:
        s (str): The dictionary to pretty print.

    Returns:
        str: The pretty printed dictionary.
    """
    return json.dumps(s, indent=2, ensure_ascii=False)


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.setitimer(signal.ITIMER_REAL, seconds)  # used timer instead of alarm
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


def get_token_length(text: str, model: str) -> int:
    """Get the token length of the given text."""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def extract_json_from_response(response: str) -> dict:
    """LLM 응답에서 JSON 부분만 추출

    LLM이 JSON 구조를 응답으로 반환했을 때, 코드 블록 안에 있든 아니든
    유효한 JSON 형식을 감지하고 추출합니다.

    Args:
        response: LLM의 전체 응답 텍스트

    Returns:
        dict: 추출된 JSON 객체

    Raises:
        json.JSONDecodeError: 유효한 JSON을 찾지 못했을 경우
    """

    # 1. 코드 블록 내의 JSON 추출 시도
    json_block_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    json_blocks = re.findall(json_block_pattern, response)

    # 코드 블록이 있으면 처리
    if json_blocks:
        # 가장 긴 블록을 선택 (가장 완전한 JSON일 가능성이 높음)
        json_str = max(json_blocks, key=len).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 실패하면 다음 방법 시도
            logger.error(f"Failed to parse JSON from code block: {json_str[:200]}...")

    # 2. 응답 전체에서 JSON 구조 찾기 시도
    try:
        # 기존 방식: 코드 블록 마커 제거 후 전체를 JSON으로 파싱
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        # 실패하면 추가 정리 시도
        pass

    # 3. 대괄호나 중괄호로 둘러싸인 부분 찾기 시도
    try:
        # 가장 바깥쪽 JSON 형태의 구조 찾기 (배열 또는 객체)
        json_pattern = r"(\[[\s\S]*\]|\{[\s\S]*\})"
        matches = re.findall(json_pattern, response)

        if matches:
            # 가장 긴 매치 선택 (가장 완전한 JSON일 가능성이 높음)
            json_str = max(matches, key=len)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # 모든 방법이 실패하면 마지막으로 원본 응답 그대로 시도
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        # 최종 실패 - 자세한 오류 로깅
        logger.error(f"Failed to extract JSON from response: {str(e)}")
        logger.error(f"Response excerpt: {response[:300]}...")
        # 원래 예외 다시 발생
        raise json.JSONDecodeError(
            f"Could not extract valid JSON from LLM response: {str(e)}", response, e.pos
        )


def save_json(path: str, data):
    """
    지정한 경로(path)에 데이터를 JSON 형식으로 저장합니다.
    Args:
        path (str): 저장할 파일 경로
        data (Any): 저장할 데이터 (JSON 직렬화 가능 객체)
    """
    try:
        # 폴더가 없으면 생성
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Successfully save_json: {path}")
    except Exception as e:
        logger.error(f"Error save_json: {str(e)}")

    return path


def load_json(path: str):
    """지정한 경로(path)에서 JSON 파일을 읽어 데이터를 반환합니다."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

        logger.info(f"Successfully loaded JSON from {path}")

    except Exception as e:
        logger.error(f"Error loading JSON from {path}: {str(e)}")
        return None
