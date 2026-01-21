"""Rendu du contenu Markdown en HTML."""
import markdown
from pathlib import Path
from app.config import THEORY_CONTENT_DIR


# Extensions Markdown
MD_EXTENSIONS = [
    'markdown.extensions.fenced_code',
    'markdown.extensions.tables',
    'markdown.extensions.toc',
    'markdown.extensions.attr_list',
    'markdown.extensions.def_list',
    'markdown.extensions.admonition',
]


def render_markdown(text: str) -> str:
    """Convertit du Markdown en HTML."""
    md = markdown.Markdown(extensions=MD_EXTENSIONS)
    return md.convert(text)


async def render_module_content(module_id: int) -> str:
    """Charge et rend le contenu d'un module."""
    # Mapping module_id vers dossier
    module_dirs = {
        1: "01_introduction",
        2: "02_domaine_assurance",
        3: "03_rest_api",
        4: "04_api_gateway",
        5: "05_patterns_avances",
        6: "06_messaging_basics",
        7: "07_event_driven",
        8: "08_saga_transactions",
        9: "09_etl_batch",
        10: "10_cdc_streaming",
        11: "11_data_quality",
        12: "12_resilience",
        13: "13_observability",
        14: "14_security",
        15: "15_architecture_decisions",
        16: "16_projet_final",
    }

    dir_name = module_dirs.get(module_id)
    if not dir_name:
        return "<p>Contenu non disponible.</p>"

    content_dir = THEORY_CONTENT_DIR / dir_name
    if not content_dir.exists():
        return "<p>Contenu en cours de rédaction...</p>"

    # Charger tous les fichiers .md dans l'ordre
    md_files = sorted(content_dir.glob("*.md"))
    if not md_files:
        return "<p>Contenu en cours de rédaction...</p>"

    combined_content = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        combined_content.append(content)

    full_markdown = "\n\n---\n\n".join(combined_content)
    return render_markdown(full_markdown)
