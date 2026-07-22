# backend/file_import.py
"""
Converts supported uploaded files into HTML that can be loaded straight into
the rich-text editor on the frontend.

Supported formats (kept intentionally small and clearly documented so the
UI/README can state limits honestly):
  - .txt   -> each line becomes a paragraph
  - .md    -> converted via the `markdown` library (headings, bold, lists, etc.)
  - .docx  -> paragraphs converted via python-docx, preserving bold/italic
              runs, mapping Word heading styles to HTML headings, and
              inlining any embedded images as base64 <img> tags
"""
import base64
import html
import re

import markdown as md_lib
from docx import Document as DocxDocument
from docx.oxml.ns import qn

SUPPORTED_EXTENSIONS = {"txt", "md", "markdown", "docx"}


class UnsupportedFileType(Exception):
    pass


def get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _collapse_whitespace(html_str: str) -> str:
    """
    Removes insignificant whitespace text nodes between block tags.
    Without this, libraries like `markdown` emit HTML with real newline
    characters between tags (e.g. "<p>Hello</p>\n<h2>...</h2>"), and Quill's
    HTML-to-delta conversion treats that whitespace as an extra blank line,
    making imported documents look double-spaced.
    """
    return re.sub(r">\s+<", "><", html_str).strip()


def convert_txt(file_stream) -> str:
    text = file_stream.read().decode("utf-8", errors="replace")
    lines = text.splitlines() or [""]
    return "".join(f"<p>{html.escape(line) or '<br>'}</p>" for line in lines)


def convert_md(file_stream) -> str:
    text = file_stream.read().decode("utf-8", errors="replace")
    rendered = md_lib.markdown(text, extensions=["extra"])
    return _collapse_whitespace(rendered)


def _extract_run_images(run, doc) -> list[str]:
    """Finds any inline images in a run and returns them as base64 <img> tags."""
    imgs = []
    blips = run._element.findall(".//" + qn("a:blip"))
    for blip in blips:
        rId = blip.get(qn("r:embed"))
        if not rId:
            continue
        try:
            image_part = doc.part.related_parts[rId]
        except KeyError:
            continue
        b64 = base64.b64encode(image_part.blob).decode("ascii")
        imgs.append(
            f'<img src="data:{image_part.content_type};base64,{b64}" '
            f'style="max-width:100%;">'
        )
    return imgs


def convert_docx(file_stream) -> str:
    doc = DocxDocument(file_stream)
    parts = []
    for para in doc.paragraphs:
        run_pieces = []
        for r in para.runs:
            run_pieces.append(_run_to_html(r))
            run_pieces.extend(_extract_run_images(r, doc))
        inner = "".join(p for p in run_pieces if p)

        if not inner:
            continue  # empty paragraph (no text, no image) — skip

        style = (para.style.name or "").lower()
        if "heading 1" in style:
            parts.append(f"<h1>{inner}</h1>")
        elif "heading 2" in style:
            parts.append(f"<h2>{inner}</h2>")
        elif "heading 3" in style:
            parts.append(f"<h3>{inner}</h3>")
        elif "list bullet" in style:
            parts.append(f"<ul><li>{inner}</li></ul>")
        elif "list number" in style:
            parts.append(f"<ol><li>{inner}</li></ol>")
        else:
            parts.append(f"<p>{inner}</p>")
    return _collapse_whitespace("".join(parts)) if parts else "<p></p>"


def _run_to_html(run) -> str:
    text = html.escape(run.text)
    if not text:
        return ""
    if run.bold:
        text = f"<strong>{text}</strong>"
    if run.italic:
        text = f"<em>{text}</em>"
    if run.underline:
        text = f"<u>{text}</u>"
    return text


def file_to_html(filename: str, file_stream) -> str:
    ext = get_extension(filename)
    if ext == "txt":
        return convert_txt(file_stream)
    if ext in ("md", "markdown"):
        return convert_md(file_stream)
    if ext == "docx":
        return convert_docx(file_stream)
    raise UnsupportedFileType(
        f"'.{ext}' files can't be converted into a document yet. "
        f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )