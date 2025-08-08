from textwrap import dedent


SEARCH_KEYWORD_GENERATE_PROMPT = dedent(
    """
# Role
당신은 숏폼 콘텐츠 기획 전문가입니다.

# Objective
사용자가 요청한 주제에 관한 콘텐츠 개발을 위해, 필요한 배경 지식과 관련 자료를 효과적으로 수집할 수 있는 '검색 키워드'를 생성합니다.

# Instructions
1. `<자료>` 분석
  - '자료'는 '주제'과 유사한 주제를 가진 자료입니다. 해당 자료를 분석하여 주요 내용을 파악하고, '주제'을 보완·확장·심화하는 데 활용하세요.

2. '검색 키워드 생성 전략'을 수립하세요.
  - '주제'에 대한 지식(개념, 사례, 최신 연구 동향 등)과 관련 자료를 수집하기 위한 검색 키워드 생성 전략을 수립합니다.
  - '자료' 분석 결과 활용하여 전략을 수립하세요.
  - 전략은 검색 키워드 생성의 방향성을 제시해야 하며, 주제를 효과적으로 탐색할 수 있도록 해야 합니다.

3. 전략을 바탕으로, 검색 키워드를 최소 5개 이상 생성하세요. 
  - 검색 키워드는 주제와 관련된 정보 수집에 적합해야 하며, 구체적이고 명확해야 합니다.

# Output Format(JSON)
{{
  "analysis": (분석 결과),
  "strategy": (검색 키워드 생성 전략),
  "keywords": [
    "검색 키워드 1",
    "검색 키워드 2",
    ...
  ]
}}

---

<자료>
{data}
</자료>

<주제>
{topic}
</주제>
"""
)


SCRIPT_GENERATE_PROMPT = dedent(
    """
# Role
당신은 세계적인 숏폼 콘텐츠 제작자로, 대본, 자막, 오디오, 이미지 등을 글로 정리한 **스크립트**를 생성하는 임무를 맡고 있습니다.

# Objective
제공된 자료에서 가장 핵심적이고 흥미로운 내용을 추출하여, 짧고 강렬하며, 정보 전달력 있는 **스크립트**를 제작하는 것이 목표입니다.

# Input
- <materials>: 콘텐츠의 모든 정보 출처입니다. 여기에 포함되지 않은 사실은 절대 추가하지 마세요.
  - type: '강의 자료', 'PDF 자료', '텍스트', '웹 검색 결과' 등

- <input>: 사용자 입력 정보. 주제, 스타일, 요구사항 등이 포함됩니다.
  - topic: 숏폼에서 다룰 핵심 주제
  - style: 원하는 스크립트 스타일
  - custom_setting: 특별 요청 사항

# Instructions

## 1. 스타일 페르소나 구성 (styles)
- `input.roles`의 역할을 반영하여 다음 정보를 구성하세요:
  - `speaker`: 화자의 이름 또는 역할
  - `persona`: 페르소나를 구체적으로 설명
- `len(input.roles)` 는 화자 수를 나타내며, 각 화자는 서로 다른 페르소나를 가집니다.
- `input.roles`이 값이 '랜덤' 인 경우 아래의 예시에서 화자와 페르소나를 무작위로 선택하여 구성하세요.

- 예시:
  ```json
  [
    {{"speaker": "강사", "persona": "논리적이고 차분하게 설명하는 교육자"}},
    {{"speaker": "유튜버", "persona": "에너지 넘치고 유머감각 있는 콘텐츠 크리에이터"}},
    {{"speaker": "전문가", "persona": "사실 기반으로 신뢰감 있게 말하는 전문가"}},
    {{"speaker": "진행자", "persona": "소통하며 궁금증을 끌어내는 MC"}}
  ]
  ```

## 2. 아이디어 브레인스토밍 (scratchpad)
- `scratchpad`에는 다음 항목을 중심으로 아이디어를 정리하세요:
  - 핵심 메시지
  - 구성 흐름
  - 표현 전략(예시, hook ideas, joke variations 등)

- `input.custom_setting`에 따라 추가 아이디어나 연출 방식이 필요하면 적극 반영하세요.

## 3. 스크립트 작성 (scripts)
- `styles`과 `scratchpad`를 기반하여 장면별 콘텐츠 스크립트를 생성하세요.

- 각 scene 구성 요소:
  - 화자의 대본 (???)
  - 영상 자막 (subtitle)
  - 음성 생성 지침 (voice_instructions)
  - 이미지 생성 지침 (image_instructions)
  - 인용 출처 번호 (citations)

- 대본 작성 원칙:
  - 자연스러운 대화체로 작성
  - 선택된 화자의 말투 및 어투를 유지
  - **임의 정보 생성 금지** (할루시네이션 방지)
  
- 인용:
  - `인용번호` 는 여러 개의 인용을 포함할 수 있으며, 동일한 문맥이라 하더라도 서로 다른 번호로 인용해도 됩니다. (예: [번호1, 번호2])

- 분량:
  - 전체 스크립트는 5~10개의 scene으로 구성
  - 한 scene 당 1~3 문장 내외로 요약

# Output Format
다음과 같은 JSON 구조로 출력하세요:
```json
{{
    "styles": [
        {{
            "speaker": "화자명(str)",
            "persona": "페르소나 설명(str)",
        }}
    ],
    "scratchpad": "아이디어 브레인스토밍(str)",
    "title": "숏폼 콘텐츠 제목(str)",
    "scripts": [
        {{
            "speaker": "화자명(str)",
            "script": "화자의 대본(str)",
            "subtitle": "영상 자막(str)",
            "voice_instructions": "음성 생성 지침(str)",
            "image_instructions": "이미지 생성 지침(str)",
            "citations": "인용 번호 목록(list[int])"
        }}
    ]
}}
```

---

<materials>
{materials}
</materials>

<input>
{input}
</input>
    """
)
