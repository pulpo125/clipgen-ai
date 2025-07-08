"""
PDF 파일을 읽는 도구

- pdf 파일 로드
- pdf 파싱: 텍스트 추출

TODO:
    - 유효한 경로인지 확인
    - 최대 pdf 파일 크기, 페이지 수, 개수 제한
    - marker-ai 또는 docling을 사용하여 추출 성능 개선
    - 이미지 추출 기능 추가
"""

from pydantic import BaseModel, Field
from typing import Type
import os
from pathlib import Path
from tqdm import tqdm
from tqdm.asyncio import tqdm_asyncio

from langchain_core.tools import BaseTool
from langchain.document_loaders import PyPDFLoader

from src.utils import log_info, log_error


class ToolSchema(BaseModel):
    pdf_paths: list[str] = Field(
        description="pdf 파일 경로 목록. e.g., ['/path/to/file1.pdf', '/path/to/file2.pdf']"
    )


class ReadPdfTool(BaseTool):
    name: str = "read_pdf"
    description: str = (
        "pdf 파일을 읽어 텍스트를 추출해야 하는 경우 사용합니다. pdf 파일 경로 목록을 입력으로 받습니다."
    )
    args_schema: Type[BaseModel] = ToolSchema

    def _run(self, pdf_paths: list[str]) -> list[dict]:
        log_info(f"ReadPdfTool Run: pdf_paths={pdf_paths}")
        return self._load_and_extract(pdf_paths)

    async def _arun(self, pdf_paths: list[str]) -> list[dict]:
        log_info(f"ReadPdfTool Run: pdf_paths={pdf_paths}")
        return await self._load_and_extract_async(pdf_paths)

    def _load_and_extract(self, paths: list[str]) -> list[dict]:
        """
        PDF 파일을 로드하여 텍스트를 추출합니다.

        Args:
            paths (list[str]): PDF 파일 경로 목록

        Returns:
            list[dict]: 'title', 'content' key 를 가진 딕셔너리 목록
        """

        originals = []

        # Get all files
        all_files = []
        for path in paths:
            try:
                p = Path(path)
                if p.is_file():
                    all_files.append(p)
                elif p.is_dir():
                    for root, _, files in os.walk(p):
                        all_files.extend([Path(root) / file for file in files])
            except Exception as e:
                log_error(f"Error _load_pdf_files: Invalid path {path} - {str(e)}")
                continue

        # PyPDFLoader를 사용하여 PDF 파일을 로드하고 텍스트 추출
        for file_path in tqdm(all_files):
            file_name, extension = file_path.stem, file_path.suffix

            # 파일 확장자가 PDF가 아닌 경우 건너뜀
            if extension != ".pdf":
                continue

            try:
                pdf_loader = PyPDFLoader(str(file_path))
                pages = [page.page_content for page in pdf_loader.lazy_load()]
                content = "\n\n".join(pages)
                originals.append({"title": file_name, "content": content})
            except Exception as e:
                # TODO: marker-ai or docling
                log_error(
                    f"Error _load_pdf_files: Failed to parse {file_path} - {str(e)}"
                )
                continue

        log_info(f"Successfully _load_pdf_files: {len(originals)}개 PDF 문서 추출 완료")
        return originals

    async def _load_and_extract_async(self, paths: list[str]) -> list[dict]:
        """
        비동기로 PDF 파일을 로드하여 텍스트를 추출합니다.

        Args:
            paths (list[str]): PDF 파일 경로 목록

        Returns:
            list[dict]: 'title', 'content' key 를 가진 딕셔너리 목록
        """

        originals = []

        # Get all files
        all_files = []
        for path in paths:
            try:
                p = Path(path)
                if p.is_file():
                    all_files.append(p)
                elif p.is_dir():
                    for root, _, files in os.walk(p):
                        all_files.extend([Path(root) / file for file in files])
            except Exception as e:
                log_error(f"Error _load_pdf_files: Invalid path {path} - {str(e)}")
                continue

        async def _process_pdf_file(file_path: Path):
            file_name, extension = file_path.stem, file_path.suffix
            if extension != ".pdf":
                return None

            try:
                pdf_loader = PyPDFLoader(str(file_path))
                pages = [page.page_content for page in pdf_loader.lazy_load()]
                content = "\n\n".join(pages)
                return {"title": file_name, "content": content}

            except Exception as e:
                log_error(
                    f"Error process_pdf_file: Failed to parse {file_path} - {str(e)}"
                )
                return None

        # PyPDFLoader를 사용하여 PDF 파일을 로드하고 텍스트 추출
        tasks = [_process_pdf_file(file_path) for file_path in all_files]
        for f in tqdm_asyncio.as_completed(tasks):
            result = await f
            if result:
                originals.append(result)

        log_info(
            f"Successfully _load_pdf_files_async: {len(originals)}개 PDF 문서 추출 완료"
        )
        return originals
