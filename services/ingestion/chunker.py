"""
Hierarchical chunking — produces both summary-level and detail-level chunks
so retrieval can match broad topic queries and specific detail questions.
"""

import logging
from typing import List, Dict, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from config.settings import get_settings
from services.ingestion.processor import clean_text

logger = logging.getLogger("privategpt.chunker")


class Chunk:
    """A single chunk of text with metadata."""

    def __init__(
        self,
        content: str,
        chunk_index: int,
        chunk_type: str = "detail",  # "summary" or "detail"
        page_number: Optional[int] = None,
        section_title: Optional[str] = None,
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.chunk_type = chunk_type
        self.page_number = page_number
        self.section_title = section_title
        self.content_length = len(content)


def create_detail_chunks(
    text: str,
    page_contents: Optional[List[Dict]] = None,
    chunk_size: int = None,
    chunk_overlap: int = None,
) -> List[Chunk]:
    """
    Create fine-grained overlapping chunks using RecursiveCharacterTextSplitter.
    If page_contents is provided, chunks retain page/section metadata.
    """
    settings = get_settings()
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: List[Chunk] = []
    chunk_index = 0

    if page_contents:
        # Chunk per page/section, preserving provenance
        for page_info in page_contents:
            content = clean_text(page_info.get("content", ""))
            if not content or len(content) < 20:
                continue

            page_num = page_info.get("page_number")
            section = page_info.get("section_title")

            splits = splitter.split_text(content)
            for split_text in splits:
                chunks.append(Chunk(
                    content=split_text,
                    chunk_index=chunk_index,
                    chunk_type="detail",
                    page_number=page_num,
                    section_title=section,
                ))
                chunk_index += 1
    else:
        # Chunk the full text
        cleaned = clean_text(text)
        if cleaned:
            splits = splitter.split_text(cleaned)
            for split_text in splits:
                chunks.append(Chunk(
                    content=split_text,
                    chunk_index=chunk_index,
                    chunk_type="detail",
                ))
                chunk_index += 1

    logger.info(f"Created {len(chunks)} detail chunks (size={chunk_size}, overlap={chunk_overlap})")
    return chunks


def create_summary_chunk(
    text: str,
    max_length: int = None,
) -> Optional[Chunk]:
    """
    Create a high-level summary chunk for broad topic matching.
    Uses extractive summarization (first N characters of cleaned text).
    For production, this could be replaced with LLM-generated summaries.
    """
    settings = get_settings()
    max_length = max_length or settings.summary_max_length

    cleaned = clean_text(text)
    if not cleaned or len(cleaned) < 100:
        return None

    # Extractive summary: take the first max_length characters at sentence boundaries
    summary = cleaned[:max_length * 2]  # Take more, then trim at sentence

    # Find the last sentence boundary within max_length
    sentences = summary.split('. ')
    summary_parts = []
    current_length = 0

    for sentence in sentences:
        if current_length + len(sentence) > max_length and summary_parts:
            break
        summary_parts.append(sentence)
        current_length += len(sentence) + 2

    summary_text = '. '.join(summary_parts)
    if not summary_text.endswith('.'):
        summary_text += '.'

    logger.info(f"Created summary chunk: {len(summary_text)} chars")

    return Chunk(
        content=summary_text,
        chunk_index=0,
        chunk_type="summary",
        section_title="Document Summary",
    )


def chunk_document(
    text: str,
    page_contents: Optional[List[Dict]] = None,
    enable_hierarchical: bool = None,
) -> List[Chunk]:
    """
    Main chunking function — produces hierarchical chunks
    (summary + detail) or just detail chunks.
    """
    settings = get_settings()
    if enable_hierarchical is None:
        enable_hierarchical = settings.enable_hierarchical_chunking

    all_chunks: List[Chunk] = []

    # Summary chunk (broad topic matching)
    if enable_hierarchical:
        summary = create_summary_chunk(text)
        if summary:
            all_chunks.append(summary)

    # Detail chunks (fine-grained)
    detail_chunks = create_detail_chunks(text, page_contents)

    # Re-index to account for summary chunk
    if all_chunks:
        for i, chunk in enumerate(detail_chunks):
            chunk.chunk_index = i + len(all_chunks)

    all_chunks.extend(detail_chunks)

    logger.info(
        f"Total chunks: {len(all_chunks)} "
        f"(summary={'yes' if enable_hierarchical else 'no'}, "
        f"detail={len(detail_chunks)})"
    )
    return all_chunks
