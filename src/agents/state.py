from typing import TypedDict, Annotated

# =================================
# Reducers
# =================================


def dict_reducer(a: dict, b: dict | None) -> dict:
    """
    두 개의 딕셔너리를 깊게 병합합니다.

    Args:
        a: First dictionary (current state)
        b: Second dictionary (new state, can be None)

    Returns:
        a와 b를 깊게 병합한 딕셔너리. b가 None이면 a를 그대로 반환

    Examples:
        >>> dict_reducer({'a': 1}, {'b': 2})
        {'a': 1, 'b': 2}
        >>> dict_reducer({'a': 1}, None)
        {'a': 1}
        >>> dict_reducer({'x': {'y': 1}}, {'x': {'z': 2}})
        {'x': {'y': 1, 'z': 2}}
    """
    if b is None:
        return a

    result = a.copy()

    for key, value in b.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # 둘 다 딕셔너리인 경우 재귀적으로 병합
            result[key] = dict_reducer(result[key], value)
        else:
            # 그 외의 경우 b의 값으로 덮어쓰기
            result[key] = value

    return result


def list_reducer(a: list, b: list | None) -> list:
    """
    항상 최신 리스트(b)를 반환합니다. b가 없으면 기존 리스트(a)를 유지합니다.

    Args:
        a: First list (current state)
        b: Second list (new state, can be None)

    Returns:
        b가 존재하면 b를 반환, 그렇지 않으면 a를 반환.

    Examples:
        >>> list_reducer([1, 2], [3, 4])
        [3, 4]
        >>> list_reducer([1, 2], None)
        [1, 2]
    """
    return b if b is not None else a


# =================================
# Schemas
# ==================================


class PathResult(TypedDict):
    material: str
    script: str
    audio: str
    image: list[str]
    video: str


# =================================
# States
# =================================


class InputState(TypedDict):
    user_input: Annotated[dict, dict_reducer]


class OutputState(TypedDict):
    scripts: Annotated[list[dict], list_reducer]
    paths: Annotated[PathResult, dict_reducer]


class OverallState(TypedDict):
    user_input: Annotated[dict, dict_reducer]
    materials: Annotated[list[dict], list_reducer]
    scripts: Annotated[list[dict], list_reducer]
    paths: Annotated[PathResult, dict_reducer]
