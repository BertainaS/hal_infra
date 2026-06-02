#!/usr/bin/env python3
"""
infralatex.py
------------------------------
Récupère les publications associées à l'infrastructure de recherche
INFRANALYTICS via l'API HAL (champs officiels irThesaurus*)
et génère une liste bibliographique en LaTeX structurée en sections :

  1. Articles dans des revues à comité de lecture  (ART)
  2. Communications dans des congrès               (COMM)
  3. Chapitres d'ouvrage                           (COUV)
  4. Ouvrages                                      (OUV)
  5. Posters                                       (POSTER)
  6. Rapports                                      (REPORT)
  7. Thèses                                        (THESE)
  8. Pré-publications / preprints                  (PREPRINT)
  9. Logiciels                                     (SOFTWARE)
 10. Données de recherche                          (DATA)
 11. Autres                                        (OTHER)

Usage :
  python infralatex.py

Dépendances : requests  (pip install requests)
"""

import re
import sys
import unicodedata
import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Acronyme exact tel qu'enregistré dans le référentiel HAL
IR_ACRONYM  = "Infranalytics"

# Sections à générer (types HAL)
SECTIONS = [
    {"types": ["ART"],     "title": r"Articles dans des revues à comité de lecture", "label": "art"},
    {"types": ["COMM"],    "title": r"Communications dans des congrès",               "label": "comm"},
    {"types": ["COUV"],    "title": r"Chapitres d'ouvrage",                           "label": "couv"},
    {"types": ["OUV"],     "title": r"Ouvrages",                                      "label": "ouv"},
    {"types": ["POSTER"],  "title": r"Posters",                                       "label": "poster"},
    {"types": ["REPORT"],  "title": r"Rapports",                                      "label": "report"},
    {"types": ["THESE"],   "title": r"Thèses",                                        "label": "these"},
    {"types": ["UNDEFINED"], "title": r"Pré-publications (preprints)",                "label": "preprint"},
    {"types": ["SOFTWARE"],"title": r"Logiciels",                                     "label": "software"},
    {"types": ["DATA"],    "title": r"Données de recherche",                          "label": "data"},
    {"types": ["OTHER"],   "title": r"Autres",                                        "label": "other"},
]

ROWS_PER_PAGE = 100
OUTPUT_FILE   = "infranalytics_publi.tex"
SORT        = "publicationDateY_i desc"

# ─────────────────────────────────────────────────────────────────────────────
# API HAL
# ─────────────────────────────────────────────────────────────────────────────

HAL_API = "https://api.archives-ouvertes.fr/search/"

FIELDS = ",".join([
    "halId_s",
    "title_s",
    "authFullName_s",
    "journalTitle_s",
    "volume_s",
    "page_s",
    "issue_s",
    "publicationDateY_i",
    "producedDateY_i",
    "doiId_s",
    "docType_s",
    "conferenceTitle_s",
    "city_s",
    "bookTitle_s",
    "publisher_s",
    "softwareVersion_s",
    "swhidId_s",
    "language_s",
    "licence_s",
    "dataSetVersion_s",
    "labStructAcronym_s",
    "instStructAcronym_s",
    "irThesaurusAcronym_s",
    "irThesaurusName_s",
])


def fetch_section(ir_acronym, doc_types):
    """Interroge l'API HAL pour un type de document et une IR donnée, avec pagination."""
    if not doc_types:
        return []

    type_filter = " OR ".join(f"docType_s:{t}" for t in doc_types)
    ir_filter = (
        f'irThesaurusAcronym_s:"{ir_acronym}" OR '
        f'irThesaurusName_t:"{ir_acronym}" OR '
        f'irThesaurus_t:"{ir_acronym}"'
    )
    query = f"({ir_filter}) AND ({type_filter})"
    base_params = {"q": query, "fl": FIELDS, "sort": SORT, "wt": "json"}

    print(f"[HAL] ({', '.join(doc_types)}) ...", file=sys.stderr)
    resp = requests.get(HAL_API, params={**base_params, "rows": 0}, timeout=30)
    resp.raise_for_status()
    total = resp.json().get("response", {}).get("numFound", 0)

    all_docs = []
    start = 0
    while start < total:
        resp = requests.get(
            HAL_API, params={**base_params, "rows": ROWS_PER_PAGE, "start": start}, timeout=30
        )
        resp.raise_for_status()
        all_docs.extend(resp.json().get("response", {}).get("docs", []))
        start += ROWS_PER_PAGE

    print(f"[HAL]  → {total} trouvés, {len(all_docs)} récupérés.", file=sys.stderr)
    all_docs.sort(
        key=lambda d: d.get("publicationDateY_i", d.get("producedDateY_i", 0) or 0),
        reverse=True,
    )
    return all_docs


# ─────────────────────────────────────────────────────────────────────────────
# FORMATAGE AUTEURS
# ─────────────────────────────────────────────────────────────────────────────

def initials(first_name):
    if re.match(r'^([A-Z]\.\s*)+$', first_name.strip()):
        return first_name.strip()
    parts = re.split(r'[-\s]+', first_name.strip())
    init_parts = [p.strip(".")[0].upper() + "." for p in parts if p.strip(".")]
    return "-".join(init_parts) if "-" in first_name else " ".join(init_parts)


def format_author(full_name):
    if re.match(r'^[A-Z]\.\s', full_name):
        return full_name.strip()
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    particles = {"de", "van", "von", "le", "la", "du", "den", "der"}
    last = parts[-1]
    first_parts = parts[:-1]
    if last.lower() in particles and len(parts) > 2:
        last = " ".join(parts[-2:])
        first_parts = parts[:-2]
    return f"{initials(' '.join(first_parts))} {last}"


# ─────────────────────────────────────────────────────────────────────────────
# ÉCHAPPEMENT LATEX
# ─────────────────────────────────────────────────────────────────────────────

UNICODE_MAP = {
    "\u2212": "-",
    "\u2013": "--", "\u2014": "---",
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2015": "---",
    "\u201c": "``", "\u201d": "''", "\u2018": "`", "\u2019": "'",
    "\u00ab": r"\og{}", "\u00bb": r"\fg{}",
    "\u00a0": "~", "\u202f": "~", "\u2009": " ", "\u200b": "",
    "\u00b2": r"$^{2}$", "\u00b3": r"$^{3}$", "\u00b9": r"$^{1}$",
    "\u2070": r"$^{0}$", "\u2074": r"$^{4}$", "\u2075": r"$^{5}$",
    "\u2076": r"$^{6}$", "\u2077": r"$^{7}$", "\u2078": r"$^{8}$",
    "\u2079": r"$^{9}$", "\u207a": r"$^{+}$", "\u207b": r"$^{-}$",
    "\u2080": r"$_{0}$", "\u2081": r"$_{1}$", "\u2082": r"$_{2}$",
    "\u2083": r"$_{3}$", "\u2084": r"$_{4}$", "\u2085": r"$_{5}$",
    "\u2086": r"$_{6}$", "\u2087": r"$_{7}$", "\u2088": r"$_{8}$",
    "\u2089": r"$_{9}$",
    "\u00b1": r"$\pm$",   "\u00d7": r"$\times$", "\u00f7": r"$\div$",
    "\u2265": r"$\geq$",  "\u2264": r"$\leq$",   "\u2260": r"$\neq$",
    "\u221e": r"$\infty$",
    "\u03b1": r"$\alpha$",  "\u03b2": r"$\beta$",   "\u03b3": r"$\gamma$",
    "\u03b4": r"$\delta$",  "\u03b5": r"$\varepsilon$", "\u03b7": r"$\eta$",
    "\u03ba": r"$\kappa$",  "\u03bb": r"$\lambda$",  "\u03bc": r"$\mu$",
    "\u03c0": r"$\pi$",     "\u03c3": r"$\sigma$",   "\u03c4": r"$\tau$",
    "\u03c6": r"$\varphi$", "\u03c7": r"$\chi$",     "\u03c9": r"$\omega$",
    "\u0394": r"$\Delta$",  "\u03a3": r"$\Sigma$",   "\u03a6": r"$\Phi$",
    "\u03a8": r"$\Psi$",    "\u03a9": r"$\Omega$",
    "\u2026": r"\ldots{}", "\u2022": r"\textbullet{}",
    "\u00b0": r"$^{\circ}$", "\u2032": r"$'$", "\u2033": r"$''$",
}


def unicode_to_latex(text):
    for char, repl in UNICODE_MAP.items():
        text = text.replace(char, repl)
    return text


def latex_escape(text):
    special = [
        ("\\", r"\textbackslash{}"), ("&",  r"\&"),  ("%", r"\%"),
        ("$",  r"\$"),               ("#",  r"\#"),  ("_", r"\_"),
        ("{",  r"\{"),               ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),("^",  r"\textasciicircum{}"),
    ]
    for char, repl in special:
        text = text.replace(char, repl)
    return unicode_to_latex(text)


def format_authors_latex(full_names):
    """Formate la liste d'auteurs — sans soulignement d'aucun nom."""
    out = []
    for name in full_names:
        fmt = format_author(name)
        out.append(latex_escape(fmt))
    return ", ".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# FORMATAGE D'UNE ENTRÉE
# ─────────────────────────────────────────────────────────────────────────────

def _href_url(url):
    """Protège les accolades LaTeX dans la partie URL d'un \\href{} (évite l'injection)."""
    return url.replace("{", "%7B").replace("}", "%7D")


def hal_str(value, sep=", "):
    if value is None:
        return ""
    if isinstance(value, list):
        return sep.join(str(v) for v in value if v is not None)
    return str(value)


def format_entry_latex(doc, index, section_label):
    dtype = hal_str(doc.get("docType_s", "ART"))

    # Auteurs
    authors_raw = doc.get("authFullName_s", [])
    if not isinstance(authors_raw, list):
        authors_raw = [authors_raw] if authors_raw else []
    author_line = (format_authors_latex(authors_raw)
                   if authors_raw else r"\textit{(auteurs non disponibles)}")

    # Titre
    titles = doc.get("title_s", [])
    if not isinstance(titles, list):
        titles = [titles] if titles else []
    title = titles[0] if titles else "(titre non disponible)"
    title_latex = r"\textit{" + latex_escape(title) + r"}"

    # Année
    year = doc.get("publicationDateY_i") or doc.get("producedDateY_i") or ""

    # Référence selon le type
    ref_parts = []

    if dtype in ("ART", "PREPRINT", "UNDEFINED"):
        journal = hal_str(doc.get("journalTitle_s", ""))
        volume  = hal_str(doc.get("volume_s", ""))
        issue   = hal_str(doc.get("issue_s", ""))
        pages   = hal_str(doc.get("page_s", ""))
        if journal:
            ref_parts.append(r"\textbf{" + latex_escape(journal) + r"}")
        if volume:
            ref_parts.append(latex_escape(volume) + (f"({latex_escape(issue)})" if issue else ""))
        if pages:
            ref_parts.append(latex_escape(pages))
        if dtype in ("PREPRINT", "UNDEFINED") and not journal:
            ref_parts.append(r"\textit{Preprint}")

    elif dtype == "COMM":
        conf  = hal_str(doc.get("conferenceTitle_s", ""))
        city  = hal_str(doc.get("city_s", ""))
        if conf:
            ref_parts.append(r"\textbf{" + latex_escape(conf) + r"}")
        if city:
            ref_parts.append(latex_escape(city))

    elif dtype in ("OUV", "COUV"):
        book      = hal_str(doc.get("bookTitle_s", ""))
        publisher = hal_str(doc.get("publisher_s", ""))
        pages     = hal_str(doc.get("page_s", ""))
        if book:
            ref_parts.append(r"\textbf{" + latex_escape(book) + r"}")
        if publisher:
            ref_parts.append(latex_escape(publisher))
        if pages:
            ref_parts.append(latex_escape(pages))

    elif dtype == "POSTER":
        conf = hal_str(doc.get("conferenceTitle_s", ""))
        city = hal_str(doc.get("city_s", ""))
        ref_parts.append(r"\textbf{Poster}")
        if conf:
            ref_parts.append(latex_escape(conf))
        if city:
            ref_parts.append(latex_escape(city))

    elif dtype == "REPORT":
        publisher = hal_str(doc.get("publisher_s", ""))
        ref_parts.append(r"\textbf{Rapport}")
        if publisher:
            ref_parts.append(latex_escape(publisher))

    elif dtype == "THESE":
        publisher = hal_str(doc.get("publisher_s", ""))
        ref_parts.append(r"\textbf{Thèse}")
        if publisher:
            ref_parts.append(latex_escape(publisher))

    elif dtype == "SOFTWARE":
        ref_parts.append(r"\textbf{Logiciel}")
        version  = hal_str(doc.get("softwareVersion_s", ""))
        language = hal_str(doc.get("language_s", ""))
        licence  = hal_str(doc.get("licence_s", ""))
        swhid    = hal_str(doc.get("swhidId_s", ""))
        if version:
            ref_parts.append(f"v.~{latex_escape(version)}")
        if language:
            ref_parts.append(latex_escape(language))
        if licence:
            ref_parts.append(latex_escape(licence))
        if swhid:
            ref_parts.append(
                r"\href{https://archive.softwareheritage.org/" + _href_url(swhid)
                + r"}{\texttt{SWH:} \texttt{" + latex_escape(swhid[:30]) + r"\ldots{}}}"
            )

    elif dtype == "DATA":
        ref_parts.append(r"\textbf{Jeu de données}")
        version = hal_str(doc.get("dataSetVersion_s", ""))
        if version:
            ref_parts.append(f"v.~{latex_escape(version)}")

    else:
        journal = hal_str(doc.get("journalTitle_s", ""))
        if journal:
            ref_parts.append(r"\textbf{" + latex_escape(journal) + r"}")

    ref_line = ", ".join(ref_parts)
    if year:
        ref_line += f" ({year})"

    # Liens DOI / HAL
    doi    = hal_str(doc.get("doiId_s", ""))
    hal_id = hal_str(doc.get("halId_s", ""))
    link_parts = []
    if doi:
        link_parts.append(
            r"\href{https://doi.org/" + _href_url(doi) + r"}{DOI:~" + latex_escape(doi) + r"}")
    if hal_id:
        link_parts.append(
            r"\href{https://hal.science/" + _href_url(hal_id) + r"}{HAL:~" + latex_escape(hal_id) + r"}")
    link_line = r" \quad ".join(link_parts)

    # Assemblage
    lines = [r"\item[\textbf{[" + str(index) + r"]}]\label{" + section_label + str(index) + r"}"]
    lines.append(author_line + r"\\")
    lines.append(title_latex + r"\\")
    if ref_line.strip():
        lines.append(ref_line + r"\\")
    if link_line.strip():
        lines.append(link_line)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# GÉNÉRATION D'UNE SECTION LATEX
# ─────────────────────────────────────────────────────────────────────────────

def build_section_latex(section, docs):
    if not docs:
        return ""
    title = section["title"]
    label = section["label"]
    n     = len(docs)

    entries = [
        format_entry_latex(doc, n - i, label)
        for i, doc in enumerate(docs)
    ]

    return "\n".join([
        f"\\section*{{{latex_escape(title)}}}",
        f"% {n} entrée(s)",
        r"\begin{itemize}[leftmargin=*, itemsep=0.5em, parsep=0pt, label={}]",
        "",
        "\n\n".join(entries),
        "",
        r"\end{itemize}",
    ])


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT LATEX
# ─────────────────────────────────────────────────────────────────────────────

def build_preamble(ir_acronym, total):
    return rf"""% ============================================================
% Publications associées à l'infrastructure  {ir_acronym}
% Générées automatiquement depuis HAL — hal_infranalytics_to_latex.py
% {total} entrée(s) au total
% ============================================================
\documentclass[a4paper, 11pt]{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[french]{{babel}}
\usepackage{{hyperref}}
\usepackage{{url}}
\usepackage{{geometry}}
\usepackage{{enumitem}}
\usepackage{{titlesec}}
\geometry{{margin=2cm}}

\hypersetup{{colorlinks=true, linkcolor=blue, urlcolor=blue, citecolor=blue}}

\titleformat{{\section}}[block]{{\large\bfseries}}{{}}{{}}{{}}[\titlerule]
\titlespacing*{{\section}}{{0pt}}{{1.8ex plus .4ex}}{{0.8ex}}

\begin{{document}}

\begin{{center}}
  {{\LARGE\bfseries Publications — Infrastructure {ir_acronym}}}\\[0.5em]
  {{\large Extraites de HAL}}\\[0.3em]
  {{\normalsize {total} publication(s) recensée(s)}}
\end{{center}}

\bigskip
"""

POSTAMBLE = "\n\\end{document}\n"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    blocks       = []
    total        = 0
    section_stats = []

    for section in SECTIONS:
        docs  = fetch_section(IR_ACRONYM, section["types"])
        block = build_section_latex(section, docs)
        if block:
            blocks.append(block)
            total += len(docs)
            section_stats.append((section["title"], len(docs)))

    if total == 0:
        print(
            f"⚠️  Aucune publication trouvée pour '{IR_ACRONYM}'.\n"
            "   Vérifiez que l'acronyme correspond à la valeur dans le référentiel HAL.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Résumé terminal
    print(f"\n✅ {total} publication(s) récupérée(s) pour {IR_ACRONYM} :", file=sys.stderr)
    for title, n in section_stats:
        print(f"   {n:3d}  {title}", file=sys.stderr)

    full_latex = (
        build_preamble(IR_ACRONYM, total)
        + "\n\n".join(blocks)
        + "\n"
        + POSTAMBLE
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_latex)
    print(f"\n[OK] → « {OUTPUT_FILE} »", file=sys.stderr)


if __name__ == "__main__":
    main()