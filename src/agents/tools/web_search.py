"""
웹 검색 도구
- 검색 키워드 생성
- Tavily API를 사용한 웹 검색

TODO:
    - 검색 키워드가 비워져있는 경우 topic 으로 검색
    - raw_content 가 포함된 경우 content 앞뒤 단락 추출 or 요약
    - 검색 키워드 별 여러 개 검색 후 reranking
"""

import asyncio
from pydantic import BaseModel, Field
from typing import Any, Type

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_tavily import TavilySearch
from langchain_core.tools import BaseTool

from src.utils import extract_json_from_response, log_info, log_error
from src.agents.prompt import SEARCH_KEYWORD_GENERATE_PROMPT
from src.config import cfg


class ToolSchema(BaseModel):
    topic: str = Field(description="주제")
    data: list[dict] = Field(description="참고 자료 (강의 자료, PDF 등)")
    llm: Any = Field(description="LLM 클라이언트")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "웹 검색이 필요한 경우 사용합니다. 입력은 주제와 참고 자료입니다."
    )
    args_schema: Type[BaseModel] = ToolSchema

    def _run(self, topic: str, data: list[dict], llm: Any) -> list[dict]:

        log_info(f"WebSearchTool Run: topic={topic}, data={len(data)}개")

        # 검색 키워드 생성
        search_keywords = self._generate_search_keywords(topic, data, llm)

        # 검색 키워드가 없으면 주제로 대체
        if not search_keywords:
            search_keywords = [topic]

        # TavilySearch 도구를 사용하여 검색 수행
        search_results = self._tavily_search(search_keywords)

        return search_results

    async def _arun(self, topic: str, data: list[dict], llm: Any) -> list[dict]:

        log_info(f"WebSearchTool Run: topic={topic}, data={len(data)}개")

        # 검색 키워드 생성
        search_keywords = self._generate_search_keywords(topic, data, llm)

        # 검색 키워드가 없으면 주제로 대체
        if not search_keywords:
            search_keywords = [topic]

        # TavilySearch 도구를 사용하여 검색 수행
        search_results = await self._tavily_search_async(search_keywords)

        return search_results

    def _generate_search_keywords(self, topic: str, data: str, llm: Any) -> list[str]:
        """
        주제와 PDF 자료를 바탕으로 검색 키워드를 생성합니다.

        Args:
            llm: LLM 클라이언트
            topic (str): 주제
            data (str): 참고 자료 (강의 자료, PDF 등)

        Returns:
            list[str]: 생성된 검색 키워드 목록
        """
        try:
            # 체인 생성
            prompt_builder = ChatPromptTemplate(
                input_variables=["topic", "materials"],
                messages=[
                    SystemMessagePromptTemplate.from_template(
                        SEARCH_KEYWORD_GENERATE_PROMPT
                    ),
                ],
            )
            chain = prompt_builder | llm

            # 체인 실행
            response = chain.invoke({"topic": topic, "data": data})

            # 후처리
            response_json = extract_json_from_response(response.content)
            log_info("검색 키워드 생성 결과:")
            log_info(response_json)

            search_keywords = response_json["keywords"]
            log_info(
                f"Successfully _generate_search_keywords: 총 {len(search_keywords)}개의 검색 키워드를 생성했습니다."
            )

        except Exception as e:
            log_error(f"Error _generate_search_keywords: {str(e)}")
            search_keywords = []

        return search_keywords

    def _tavily_search(self, search_keywords: list[str]) -> list[dict]:
        """
        Tavily API를 사용하여 검색 키워드에 대한 웹 검색을 수행합니다.

        Args:
            search_keywords (list[str]): 검색 키워드 목록

        Returns:
            list[dict]: 검색 결과 목록
        """
        try:
            # TavilySearchResults 도구 초기화
            tavily_search = TavilySearch(
                max_results=cfg.tavily.max_results,
                tavily_api_key=cfg.tavily.api_key,
                include_raw_content=cfg.tavily.include_raw_content,
            )

            # 검색 수행
            search_results = []
            for keyword in search_keywords:
                res = tavily_search.invoke({"query": keyword})
                search_result = res["results"]
                search_results.extend(search_result)

            log_info(
                f"Successfully _tavily_search: 총 {len(search_results)}개의 검색 결과를 가져왔습니다."
            )
        except Exception as e:
            log_error(f"Error _tavily_search: {str(e)}")
            search_results = []

        return search_results

    async def _tavily_search_async(self, search_keywords: list[str]) -> list[dict]:
        """
        Tavily API를 사용하여 검색 키워드에 대한 웹 검색을 비동기적으로 병렬 수행합니다.

        Args:
            search_keywords (list[str]): 검색 키워드 목록

        Returns:
            list[dict]: 검색 결과 목록
        """
        try:
            # TavilySearchResults 도구 초기화
            tavily_search = TavilySearch(
                max_results=cfg.tavily.max_results,
                tavily_api_key=cfg.tavily.api_key,
                include_raw_content=cfg.tavily.include_raw_content,
            )

            # 비동기 검색 수행
            tasks = [
                tavily_search.ainvoke({"query": keyword}) for keyword in search_keywords
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 합치기
            search_results = []
            for result in results:
                if isinstance(result, Exception):
                    log_error(f"검색 중 오류 발생: {result}")
                    continue

                # results 만 추출
                search_result = result.get("results", [])
                search_results.extend(search_result)

            log_info(
                f"Successfully _tavily_search_async: 총 {len(search_results)}개의 검색 결과를 가져왔습니다."
            )
        except Exception as e:
            log_error(f"Error _tavily_search_async: {str(e)}")
            search_results = []

        return search_results
