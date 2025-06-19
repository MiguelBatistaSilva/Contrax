import zipfile
import difflib
import re
import html
from lxml import etree

def extrair_comentarios(arquivo_uploadedfile):
    """
    Extrai os comentários de um arquivo DOCX enviado diretamente (UploadedFile).
    """
    comentarios = {}
    with zipfile.ZipFile(arquivo_uploadedfile) as docx_zip:
        if "word/comments.xml" in docx_zip.namelist():
            xml_content = docx_zip.read("word/comments.xml")
            tree = etree.fromstring(xml_content)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for comment in tree.xpath("//w:comment", namespaces=ns):
                comment_id = comment.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
                autor = comment.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}author", "desconhecido")
                texto_comentario = "".join(comment.itertext()).strip()
                comentarios[comment_id] = f"💬 {autor}: {texto_comentario}"
    return comentarios

def extrair_paragrafos_com_tooltip(arquivo_uploadedfile, comentarios):
    """
    Extrai parágrafos do DOCX (com comentários vinculados) diretamente da memória.
    """
    if comentarios is None:
        comentarios = {}

    paragraphs = []
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(arquivo_uploadedfile) as z:
        xml_content = z.read("word/document.xml")
    tree = etree.fromstring(xml_content)

    for para in tree.xpath("//w:p", namespaces=ns):
        para_html = ""
        tooltip_list = []
        active_comment_ids = []
        for elem in para.iter():
            tag = etree.QName(elem).localname
            if tag == "t":
                text = elem.text if elem.text else ""
                para_html += text
            elif tag == "br":
                para_html += "<br>"
            elif tag == "commentRangeStart":
                cid = elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
                if cid:
                    active_comment_ids.append(cid)
            elif tag == "commentRangeEnd":
                if active_comment_ids:
                    active_comment_ids.pop()
            elif tag == "commentReference":
                cid = elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
                if cid:
                    active_comment_ids.append(cid)

        if active_comment_ids:
            tooltip_texts = [comentarios.get(cid, "") for cid in active_comment_ids if cid in comentarios]
            tooltip_summary = "<br>".join([html.escape(tt) for tt in tooltip_texts])
        else:
            tooltip_summary = ""

        blocks = [block.strip() for block in para_html.split("<br>") if block.strip()]
        if blocks:
            for block in blocks:
                paragraphs.append((block, tooltip_summary))
        else:
            paragraphs.append((para_html, tooltip_summary))
    return paragraphs

def highlight_differences(old_text, new_text):
    """
    Destaca diferenças entre dois textos usando HTML.
    """
    old_words = old_text.split()
    new_words = new_text.split()
    sm = difflib.SequenceMatcher(None, old_words, new_words)
    highlighted_old = []
    highlighted_new = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            highlighted_old.append(" ".join(old_words[i1:i2]))
            highlighted_new.append(" ".join(new_words[j1:j2]))
        elif tag == 'delete':
            segment = " ".join(old_words[i1:i2])
            highlighted_old.append(f"<span class='diff-removed'>{segment}</span>")
        elif tag == 'insert':
            segment = " ".join(new_words[j1:j2])
            highlighted_new.append(f"<span class='diff-added'>{segment}</span>")
        elif tag == 'replace':
            segment_old = " ".join(old_words[i1:i2])
            segment_new = " ".join(new_words[j1:j2])
            highlighted_old.append(f"<span class='diff-removed'>{segment_old}</span>")
            highlighted_new.append(f"<span class='diff-added'>{segment_new}</span>")
    return " ".join(highlighted_old), " ".join(highlighted_new)

def gerar_tabela_com_diff_somente_diferencas(parags_antigos_tooltip, parags_novos_tooltip):
    """
    Gera uma tabela HTML exibindo apenas as diferenças entre duas versões.
    Agora ignora linhas onde ambos os lados (antigo e novo) estão vazios.
    """
    textos_antigos = [p for p, _ in parags_antigos_tooltip]
    textos_novos = [p for p, _ in parags_novos_tooltip]

    matcher = difflib.SequenceMatcher(None, textos_antigos, textos_novos)

    html_table = "<table class='diff-table'><thead><tr><th>Versão Antiga</th><th>Versão Nova</th></tr></thead><tbody>"

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            continue

        if tag == 'replace':
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                p_antigo, tooltip_antigo = ("", "")
                p_novo, tooltip_novo = ("", "")

                if i1 + k < i2:
                    p_antigo, tooltip_antigo = parags_antigos_tooltip[i1 + k]
                if j1 + k < j2:
                    p_novo, tooltip_novo = parags_novos_tooltip[j1 + k]

                if not p_antigo.strip() and not p_novo.strip():
                    continue

                highlighted_old, highlighted_new = highlight_differences(p_antigo, p_novo)

                if tooltip_antigo:
                    highlighted_old += f"<div class='comment-summary'>{tooltip_antigo}</div>"
                if tooltip_novo:
                    highlighted_new += f"<div class='comment-summary'>{tooltip_novo}</div>"

                html_table += f"<tr><td>{highlighted_old}</td><td>{highlighted_new}</td></tr>"

        elif tag == 'delete':
            for i in range(i1, i2):
                p_antigo, tooltip_antigo = parags_antigos_tooltip[i]
                if not p_antigo.strip():
                    continue
                if tooltip_antigo:
                    p_antigo += f"<div class='comment-summary'>{tooltip_antigo}</div>"
                html_table += f"<tr><td>{p_antigo}</td><td></td></tr>"

        elif tag == 'insert':
            for j in range(j1, j2):
                p_novo, tooltip_novo = parags_novos_tooltip[j]
                if not p_novo.strip():
                    continue
                if tooltip_novo:
                    p_novo += f"<div class='comment-summary'>{tooltip_novo}</div>"
                html_table += f"<tr><td></td><td>{p_novo}</td></tr>"

    html_table += "</tbody></table>"
    return html_table


def extrair_secoes(arquivo_uploadedfile):
    """
    Extrai as seções do DOCX diretamente da memória baseado nos headings.
    """
    secoes = {}
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(arquivo_uploadedfile) as z:
        xml_content = z.read("word/document.xml")
    tree = etree.fromstring(xml_content)

    current_secao = "sem seção"
    secoes[current_secao] = []
    for para in tree.xpath("//w:p", namespaces=ns):
        pPr = para.find(".//w:pPr", namespaces=ns)
        is_heading = False
        if pPr is not None:
            pStyle = pPr.find(".//w:pStyle", namespaces=ns)
            if pStyle is not None:
                style_val = pStyle.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
                if style_val and style_val.lower().startswith("heading"):
                    is_heading = True
        para_text = "".join(para.xpath(".//w:t/text()", namespaces=ns)).strip()
        if is_heading and para_text:
            current_secao = para_text
            if current_secao not in secoes:
                secoes[current_secao] = []
        else:
            if para_text:
                secoes[current_secao].append(para_text)
    return secoes

def split_paragraphs(text_list):
    """
    Divide parágrafos numerados como 1.2.1 em sub-parágrafos.
    """
    result = []
    for text in text_list:
        parts = re.split(r'^(?=\d+(?:\.\d+)+\s*)', text, flags=re.MULTILINE)
        parts = [part.strip() for part in parts if part.strip()]
        result.extend(parts)
    return result
