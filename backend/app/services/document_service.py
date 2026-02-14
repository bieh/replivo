"""Document parsing, structure-aware chunking, and ingestion."""
import os
import re
import uuid
from typing import Optional

import pdfplumber
from sqlalchemy import text

from ..extensions import db
from ..models import Document, DocumentChunk
from ..utils.text import count_tokens, clean_text
from .embedding_service import generate_embeddings_batch


def extract_text_from_pdf(filepath: str) -> tuple[str, int, list[str]]:
    """Extract text from PDF, return (full_text, page_count, pages_text). Falls back to OCR for scanned PDFs."""
    pages_text = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ''
            pages_text.append(t)

    total_chars = sum(len(p) for p in pages_text)
    page_count = len(pages_text)

    # If very little text extracted, try OCR
    if total_chars < 100 and page_count > 0:
        print(f"  Low text extraction ({total_chars} chars), attempting OCR...")
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(filepath, dpi=300)
            pages_text = []
            for i, img in enumerate(images):
                t = pytesseract.image_to_string(img)
                pages_text.append(t)
                if (i + 1) % 5 == 0:
                    print(f"    OCR'd {i + 1}/{len(images)} pages...")
            print(f"    OCR complete: {sum(len(p) for p in pages_text)} chars extracted")
        except Exception as e:
            print(f"  OCR failed: {e}")

    full_text = '\n\n'.join(pages_text)
    return clean_text(full_text), page_count, pages_text


def detect_document_style(text: str) -> str:
    """Detect CC&R document style for parsing strategy."""
    # Gleneagle: "Section 117." or "Section 137." (3-digit section numbers)
    if re.search(r'Section\s+\d{3}', text):
        return 'gleneagle'
    # Mission Street: "7.6 ANIMALS." decimal numbered sections
    if re.search(r'\d+\.\d+\s+[A-Z]{2,}\.', text):
        return 'mission-street'
    # Timber Ridge: Roman numeral articles "ARTICLE VIII" or OCR variants like "Ill." for "III."
    if re.search(r'ARTICLE\s+[IVXLC]+', text, re.IGNORECASE) or re.search(r'\b[IVXLC]{2,}\.\s+', text):
        return 'timber-ridge'
    return 'generic'


def chunk_mission_street(full_text: str, pages_text: list[str]) -> list[dict]:
    """Chunk Mission Street style: Article N / Section N.N TITLE."""
    chunks = []
    current_article = ''
    current_article_title = ''

    # Split on section headers like "7.6 ANIMALS." or "4.9 DELINQUENT ASSESSMENTS."
    # Also capture article headers like "ARTICLE 7" or "Article 6"
    pattern = r'(?=(?:ARTICLE\s+\d+[^\n]*|(\d+\.\d+)\s+([A-Z][A-Z\s\/&\-]+)\.))'
    parts = re.split(pattern, full_text)

    # Rebuild by scanning for section headers
    sections = []
    for match in re.finditer(r'(\d+)\.(\d+)\s+([A-Z][A-Z\s\/&\-]+)\.\s*', full_text):
        sections.append({
            'start': match.start(),
            'article_number': match.group(1),
            'section_number': f"{match.group(1)}.{match.group(2)}",
            'title': match.group(3).strip(),
        })

    # Also find article headers
    for match in re.finditer(r'ARTICLE\s+(\d+)\s*[\.\-:]*\s*([^\n]*)', full_text, re.IGNORECASE):
        pass  # Articles are captured via section numbering

    for i, sec in enumerate(sections):
        end = sections[i + 1]['start'] if i + 1 < len(sections) else len(full_text)
        content = full_text[sec['start']:end].strip()
        if not content:
            continue

        article_num = sec['article_number']
        chunks.append({
            'content': content,
            'article_number': f"Article {article_num}",
            'article_title': '',
            'section_group': '',
            'section_number': f"Section {sec['section_number']}",
            'page_number': _estimate_page(sec['start'], full_text, pages_text),
        })

    # If no sections found, fall back to generic chunking
    if not chunks:
        return chunk_generic(full_text, pages_text)

    return _enforce_chunk_limits(chunks)


def chunk_timber_ridge(full_text: str, pages_text: list[str]) -> list[dict]:
    """Chunk Timber Ridge style: ARTICLE VIII with lettered subsections."""
    chunks = []

    # Find articles: "ARTICLE VIII" or "ARTICLE X"
    article_pattern = r'ARTICLE\s+([IVXLC]+)\s*[\.\-:]*\s*([^\n]*)'
    article_matches = list(re.finditer(article_pattern, full_text, re.IGNORECASE))

    # Find subsections like "A.", "B.", "C." or "A ." at start of line within articles
    subsection_pattern = r'\n\s*([A-Z])\s*\.\s+'

    for i, art in enumerate(article_matches):
        art_start = art.start()
        art_end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(full_text)
        art_text = full_text[art_start:art_end]
        art_num = art.group(1)
        art_title = art.group(2).strip().rstrip('.')

        # Find subsections within this article
        sub_matches = list(re.finditer(subsection_pattern, art_text))

        if sub_matches:
            # Add article header as preamble if there's text before first subsection
            if sub_matches[0].start() > len(art.group(0)) + 10:
                preamble = art_text[:sub_matches[0].start()].strip()
                if preamble and count_tokens(preamble) >= 30:
                    chunks.append({
                        'content': preamble,
                        'article_number': f"Article {art_num}",
                        'article_title': art_title,
                        'section_group': '',
                        'section_number': '',
                        'page_number': _estimate_page(art_start, full_text, pages_text),
                    })

            for j, sub in enumerate(sub_matches):
                sub_start = sub.start()
                sub_end = sub_matches[j + 1].start() if j + 1 < len(sub_matches) else len(art_text)
                content = art_text[sub_start:sub_end].strip()
                if not content:
                    continue
                letter = sub.group(1)
                chunks.append({
                    'content': content,
                    'article_number': f"Article {art_num}",
                    'article_title': art_title,
                    'section_group': '',
                    'section_number': f"Article {art_num}.{letter}",
                    'page_number': _estimate_page(art_start + sub_start, full_text, pages_text),
                })
        else:
            # No subsections — whole article is one chunk
            chunks.append({
                'content': art_text.strip(),
                'article_number': f"Article {art_num}",
                'article_title': art_title,
                'section_group': '',
                'section_number': '',
                'page_number': _estimate_page(art_start, full_text, pages_text),
            })

    if not chunks:
        return chunk_generic(full_text, pages_text)

    return _enforce_chunk_limits(chunks)


def chunk_gleneagle(full_text: str, pages_text: list[str]) -> list[dict]:
    """Chunk Gleneagle style: Section NNN. numbered sections."""
    chunks = []

    # Find sections like "Section 117." or "Section 137."
    section_pattern = r'(Section\s+(\d+)\s*\.?\s*([^\n]*))'
    matches = list(re.finditer(section_pattern, full_text))

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        content = full_text[start:end].strip()
        if not content:
            continue

        sec_num = match.group(2)
        sec_title = match.group(3).strip().rstrip('.')

        chunks.append({
            'content': content,
            'article_number': '',
            'article_title': '',
            'section_group': '',
            'section_number': f"Section {sec_num}",
            'page_number': _estimate_page(start, full_text, pages_text),
        })

    if not chunks:
        return chunk_generic(full_text, pages_text)

    return _enforce_chunk_limits(chunks)


def chunk_generic(full_text: str, pages_text: list[str]) -> list[dict]:
    """Fallback: chunk by paragraphs with max 512 tokens."""
    chunks = []
    paragraphs = re.split(r'\n\n+', full_text)
    current_chunk = ''
    current_chunk_start = 0
    char_pos = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            # Track position past the empty split
            char_pos = full_text.find(para, char_pos) + len(para) if para else char_pos + 2
            continue

        para_start = full_text.find(para, char_pos)
        if para_start == -1:
            para_start = char_pos

        test = current_chunk + '\n\n' + para if current_chunk else para
        if count_tokens(test) > 512 and current_chunk:
            chunks.append({
                'content': current_chunk,
                'article_number': '',
                'article_title': '',
                'section_group': '',
                'section_number': '',
                'page_number': _estimate_page(current_chunk_start, full_text, pages_text),
            })
            current_chunk = para
            current_chunk_start = para_start
        else:
            if not current_chunk:
                current_chunk_start = para_start
            current_chunk = test

        char_pos = para_start + len(para)

    if current_chunk:
        chunks.append({
            'content': current_chunk,
            'article_number': '',
            'article_title': '',
            'section_group': '',
            'section_number': '',
            'page_number': _estimate_page(current_chunk_start, full_text, pages_text),
        })

    return chunks


def _find_page(content: str, pages_text: list[str]) -> Optional[int]:
    """Find which PDF page contains the start of this chunk content."""
    for length in (100, 60, 30):
        snippet = content[:length].strip()
        if not snippet:
            continue
        for i, page in enumerate(pages_text):
            cleaned_page = clean_text(page)
            if snippet in cleaned_page:
                return i + 1
    return None


def _estimate_page(char_pos: int, full_text: str, pages_text: list[str]) -> Optional[int]:
    """Estimate which page a character position falls on (legacy fallback)."""
    running = 0
    for i, page in enumerate(pages_text):
        running += len(page) + 2  # +2 for the \n\n join
        if char_pos < running:
            return i + 1
    return len(pages_text)


def _enforce_chunk_limits(chunks: list[dict], max_tokens: int = 512, min_tokens: int = 50) -> list[dict]:
    """Split oversized chunks and merge tiny ones."""
    result = []
    for chunk in chunks:
        tokens = count_tokens(chunk['content'])
        if tokens > max_tokens:
            # Split at paragraph boundaries
            paragraphs = chunk['content'].split('\n\n')
            current = ''
            for para in paragraphs:
                test = current + '\n\n' + para if current else para
                if count_tokens(test) > max_tokens and current:
                    new_chunk = dict(chunk)
                    new_chunk['content'] = current
                    result.append(new_chunk)
                    current = para
                else:
                    current = test
            if current:
                new_chunk = dict(chunk)
                new_chunk['content'] = current
                result.append(new_chunk)
        elif tokens < min_tokens and result:
            # Merge with previous
            result[-1]['content'] += '\n\n' + chunk['content']
        else:
            result.append(chunk)
    return result


def _assign_page_numbers(chunks_data: list[dict], pages_text: list[str]) -> list[dict]:
    """Assign accurate page numbers to chunks by matching content to PDF pages."""
    for chunk in chunks_data:
        page = _find_page(chunk['content'], pages_text)
        if page is not None:
            chunk['page_number'] = page
    return chunks_data


def ingest_document(community_id: str, filepath: str) -> Document:
    """Full ingestion pipeline: parse → chunk → embed → store."""
    filename = os.path.basename(filepath)
    file_type = 'pdf' if filename.lower().endswith('.pdf') else 'txt'

    if file_type == 'pdf':
        full_text, page_count, pages_text = extract_text_from_pdf(filepath)
    else:
        with open(filepath, 'r') as f:
            full_text = clean_text(f.read())
        page_count = None
        pages_text = [full_text]

    # Detect style and chunk
    style = detect_document_style(full_text)
    print(f"  Detected document style: {style}")

    if style == 'mission-street':
        chunks_data = chunk_mission_street(full_text, pages_text)
    elif style == 'timber-ridge':
        chunks_data = chunk_timber_ridge(full_text, pages_text)
    elif style == 'gleneagle':
        chunks_data = chunk_gleneagle(full_text, pages_text)
    else:
        chunks_data = chunk_generic(full_text, pages_text)

    # Assign accurate page numbers from PDF pages
    chunks_data = _assign_page_numbers(chunks_data, pages_text)

    print(f"  Created {len(chunks_data)} chunks")

    # Create document record
    doc = Document(
        community_id=community_id,
        filename=filename,
        file_type=file_type,
        file_path=filepath,
        file_size=os.path.getsize(filepath),
        total_pages=page_count,
        full_text=full_text,
        status='processing',
    )
    db.session.add(doc)
    db.session.flush()

    # Generate embeddings in batch
    texts = [c['content'] for c in chunks_data]
    print(f"  Generating embeddings for {len(texts)} chunks...")
    embeddings = generate_embeddings_batch(texts)

    # Create chunk records
    total_tokens = 0
    for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
        token_count = count_tokens(chunk_data['content'])
        total_tokens += token_count

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk_data['content'],
            article_number=chunk_data.get('article_number', ''),
            article_title=chunk_data.get('article_title', ''),
            section_group=chunk_data.get('section_group', ''),
            section_number=chunk_data.get('section_number', ''),
            page_number=chunk_data.get('page_number'),
            token_count=token_count,
            embedding=embedding,
        )
        db.session.add(chunk)

    db.session.flush()

    # Generate tsvectors for BM25 search
    for chunk in doc.chunks.all():
        db.session.execute(
            text(
                "UPDATE document_chunks SET search_vector = to_tsvector('english', :content) WHERE id = :id"
            ),
            {'content': chunk.content, 'id': chunk.id}
        )

    doc.total_chunks = len(chunks_data)
    doc.total_tokens = total_tokens
    doc.status = 'ready'
    db.session.commit()

    print(f"  Total tokens: {total_tokens}")
    return doc


def process_document(doc_id: str):
    """Process an uploaded document (called from API)."""
    doc = Document.query.get(doc_id)
    if not doc:
        raise ValueError(f"Document {doc_id} not found")

    try:
        filepath = doc.file_path
        file_type = doc.file_type

        if file_type == 'pdf':
            full_text, page_count, pages_text = extract_text_from_pdf(filepath)
        else:
            with open(filepath, 'r') as f:
                full_text = clean_text(f.read())
            page_count = None
            pages_text = [full_text]

        doc.full_text = full_text
        doc.total_pages = page_count

        style = detect_document_style(full_text)
        if style == 'mission-street':
            chunks_data = chunk_mission_street(full_text, pages_text)
        elif style == 'timber-ridge':
            chunks_data = chunk_timber_ridge(full_text, pages_text)
        elif style == 'gleneagle':
            chunks_data = chunk_gleneagle(full_text, pages_text)
        else:
            chunks_data = chunk_generic(full_text, pages_text)

        # Assign accurate page numbers from PDF pages
        chunks_data = _assign_page_numbers(chunks_data, pages_text)

        texts = [c['content'] for c in chunks_data]
        embeddings = generate_embeddings_batch(texts)

        total_tokens = 0
        for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            token_count = count_tokens(chunk_data['content'])
            total_tokens += token_count
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=i,
                content=chunk_data['content'],
                article_number=chunk_data.get('article_number', ''),
                article_title=chunk_data.get('article_title', ''),
                section_group=chunk_data.get('section_group', ''),
                section_number=chunk_data.get('section_number', ''),
                page_number=chunk_data.get('page_number'),
                token_count=token_count,
                embedding=embedding,
            )
            db.session.add(chunk)

        db.session.flush()

        for chunk in doc.chunks.all():
            db.session.execute(
                text("UPDATE document_chunks SET search_vector = to_tsvector('english', :content) WHERE id = :id"),
                {'content': chunk.content, 'id': chunk.id}
            )

        doc.total_chunks = len(chunks_data)
        doc.total_tokens = total_tokens
        doc.status = 'ready'
        db.session.commit()

    except Exception as e:
        doc.status = 'error'
        db.session.commit()
        raise
