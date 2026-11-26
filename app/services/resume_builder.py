from html import escape
from pathlib import Path
import re
import textwrap
import zipfile


SECTIONS = ("Summary", "Skills", "Education", "Projects", "Experience", "Certifications")


def build_resume_text(profile: dict, confirmed_skills: list[str]) -> str:
    name = (profile.get("name") or "").strip()
    lines = [name] if name else []
    contact = [profile.get(key) for key in ("email", "phone") if profile.get(key)]
    contact.extend(value for value in (profile.get("linkedin"), profile.get("github"), profile.get("portfolio")) if value)
    if contact:
        lines.append(" | ".join(str(value) for value in contact))

    sections = {
        "Summary": profile.get("summary"),
        "Skills": ", ".join(sorted(set(confirmed_skills))),
        "Education": profile.get("education"),
        "Projects": profile.get("projects"),
        "Experience": profile.get("experience"),
        "Certifications": profile.get("certifications"),
    }
    for title in SECTIONS:
        value = str(sections[title] or "").strip()
        if not value:
            continue
        lines.extend(["", title])
        items = [item.strip(" •-*\t") for item in value.splitlines() if item.strip(" •-*\t")]
        if title in ("Projects", "Experience", "Certifications"):
            lines.extend(f"• {item}" for item in items)
        else:
            lines.append(" ".join(items))
    return "\n".join(lines).strip() + "\n"


def _paragraph_xml(text: str, *, heading: bool = False, bullet: bool = False) -> str:
    safe_text = escape(text)
    ppr = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ""
    if bullet and not text.startswith(("• ", "- ", "* ")):
        safe_text = "&#8226; " + safe_text
    return (
        f"<w:p>{ppr}<w:r><w:rPr><w:rFonts w:ascii=\"Arial\" w:hAnsi=\"Arial\"/>"
        f"<w:sz w:val=\"22\"/></w:rPr><w:t xml:space=\"preserve\">{safe_text}</w:t></w:r></w:p>"
    )


def write_docx(path: Path, resume_text: str) -> None:
    paragraphs = []
    current_section = None
    first_line = resume_text.splitlines()[0] if resume_text.splitlines() else ""
    for index, line in enumerate(resume_text.splitlines()):
        if not line:
            continue
        if line in SECTIONS:
            current_section = line
            paragraphs.append(_paragraph_xml(line, heading=True))
        elif index == 0 and line == first_line:
            paragraphs.append(_paragraph_xml(line, heading=True))
        else:
            for part in textwrap.wrap(line, width=115, break_long_words=False) or [line]:
                paragraphs.append(_paragraph_xml(part, bullet=current_section in ("Projects", "Experience", "Certifications")))
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + "".join(paragraphs) +
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"/></w:sectPr>'
        '</w:body></w:document>'
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/>'
        '<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="22"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="160" w:after="40"/></w:pPr>'
        '<w:rPr><w:b/><w:sz w:val="26"/></w:rPr></w:style></w:styles>'
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>""")
        archive.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        archive.writestr("word/_rels/document.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""")
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles_xml)


def _pdf_escape(value: str) -> str:
    text = value.encode("cp1252", errors="replace").decode("cp1252")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text


def write_pdf(path: Path, resume_text: str) -> None:
    lines = []
    for raw_line in resume_text.splitlines():
        if not raw_line:
            lines.append("")
        else:
            lines.extend(textwrap.wrap(raw_line, width=92, break_long_words=False) or [raw_line])
    chunks = [lines[index:index + 48] for index in range(0, max(len(lines), 1), 48)]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    page_ids = []
    next_id = 3
    font_id = 3 + 2 * len(chunks)
    for chunk in chunks:
        page_id, stream_id = next_id, next_id + 1
        next_id += 2
        page_ids.append(page_id)
        commands = ["BT", "/F1 10 Tf", "54 744 Td", "14 TL"]
        for line in chunk:
            commands.append(f"({_pdf_escape(line)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("cp1252", errors="replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {stream_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objects[1:1] = []
    pages_object = f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] /Count {len(page_ids)} >>".encode()
    objects.insert(1, pages_object)
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    output = bytearray(b"%PDF-1.4\n%SkillPath text resume\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())
    path.write_bytes(output)


def generate_resume_files(profile: dict, skills: list[str], docx_path: Path, pdf_path: Path) -> str:
    resume_text = build_resume_text(profile, skills)
    docx_path.parent.mkdir(parents=True, exist_ok=True)
    write_docx(docx_path, resume_text)
    write_pdf(pdf_path, resume_text)
    return resume_text
