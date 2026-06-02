"""
Récupération des publications HAL liées à l'infrastructure INFRANALYTICS
via les champs officiels du référentiel IR de HAL :

  irThesaurus_t          — multicritère (tous champs IR)
  irThesaurusName_t      — nom de l'infrastructure
  irThesaurusAcronym_s   — acronyme ← champ principal pour "Infranalytics"
  irThesaurusId_s        — identifiant interne
  irThesaurusDoi_s       — DOI de l'infrastructure

API HAL : https://api.archives-ouvertes.fr/search/
"""

import requests
import json
import csv
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
HAL_API_URL = "https://api.archives-ouvertes.fr/search/"

# Acronyme exact tel qu'enregistré dans le référentiel HAL
IR_ACRONYM = "Infranalytics"

# Champs à récupérer pour chaque publication
FIELDS = [
    # Identification
    "halId_s",              # Identifiant HAL
    "uri_s",                # URL HAL
    "doiId_s",              # DOI
    "version_i",            # Version du dépôt
    "submitType_s",         # Type dépôt : file / notice / affiche
    # Contenu
    "title_s",              # Titre
    "subTitle_s",           # Sous-titre
    "abstract_s",           # Résumé
    "keyword_s",            # Mots-clés auteurs
    "language_s",           # Langue
    "domain_s",             # Domaine(s) scientifique(s)
    # Type & dates
    "docType_s",            # Type de document (ART, COMM, THESE, ...)
    "producedDate_tdate",   # Date de publication
    "producedDateY_i",      # Année de publication
    "submittedDate_tdate",  # Date de dépôt HAL
    # Auteurs
    "authFullName_s",       # Nom complet auteur(s)
    "authIdHal_s",          # IdHAL auteur(s)
    "authOrcidId_s",        # ORCID auteur(s)
    "authQuality_s",        # Rôle auteur(s)
    # Structures / affiliations
    "labStructName_s",      # Nom laboratoire(s)
    "labStructAcronym_s",   # Acronyme laboratoire(s)
    "instStructName_s",     # Nom institution(s)
    "instStructAcronym_s",  # Acronyme institution(s)
    "collCode_s",           # Collection(s) HAL
    # Revue / conférence / ouvrage
    "journalTitle_s",       # Titre revue
    "journalPublisher_s",   # Éditeur revue
    "journalIssn_s",        # ISSN
    "conferenceTitle_s",    # Titre conférence
    "city_s",               # Ville conférence
    "bookTitle_s",          # Titre ouvrage
    "publisher_s",          # Éditeur commercial
    "volume_s",             # Volume
    "issue_s",              # Numéro
    "page_s",               # Pages
    # Accès & licences
    "openAccess_bool",      # Accès ouvert
    "licence_s",            # Licence fichier
    # Financements & projets
    "funding_s",            # Financements (texte libre)
    "anrProjectReference_s",     # Référence projet ANR
    "anrProjectAcronym_s",       # Acronyme projet ANR
    "europeanProjectAcronym_s",  # Acronyme projet européen
    # Infrastructure de recherche — champs officiels HAL
    "irThesaurusAcronym_s", # Acronyme IR  ← champ principal
    "irThesaurusName_s",    # Nom complet IR
    "irThesaurusId_s",      # Identifiant IR
    "irThesaurusDoi_s",     # DOI de l'IR
    # Divers
    "comment_s",            # Commentaire déposant
    "collaboration_s",      # Collaboration / projet
]

ROWS_PER_PAGE = 100


# ─────────────────────────────────────────────
# Requêtes
# ─────────────────────────────────────────────

def fetch_page(query, start=0, rows=ROWS_PER_PAGE):
    """Récupère une page de résultats depuis l'API HAL."""
    params = {
        "q":     query,
        "fl":    ",".join(FIELDS),
        "rows":  rows,
        "start": start,
        "wt":    "json",
        "sort":  "producedDate_tdate desc",
    }
    response = requests.get(HAL_API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if "response" not in data:
        raise ValueError(f"Réponse HAL inattendue (champ 'response' absent) : {data}")
    return data


def fetch_all(query, label=""):
    """Récupère toutes les pages de résultats pour une requête donnée."""
    # Comptage
    data = fetch_page(query, start=0, rows=0)
    total = data["response"]["numFound"]
    print(f"   {label} → {total} résultat(s)")
    if total == 0:
        return []

    all_docs = []
    start = 0
    while start < total:
        end = min(start + ROWS_PER_PAGE, total)
        print(f"     Récupération {start + 1}–{end} / {total}...")
        page = fetch_page(query, start=start)
        all_docs.extend(page["response"]["docs"])
        start += ROWS_PER_PAGE

    return all_docs


def deduplicate(docs):
    """Déduplique par halId_s. Les docs sans identifiant valide sont tous conservés."""
    seen = set()
    unique = []
    for d in docs:
        hid = d.get("halId_s") or d.get("docid") or None
        if hid is None:
            unique.append(d)
        elif hid not in seen:
            seen.add(hid)
            unique.append(d)
    return unique


# ─────────────────────────────────────────────
# Formatage
# ─────────────────────────────────────────────

def _first(val, default=""):
    if isinstance(val, list):
        return val[0] if val and val[0] is not None else default
    return val if val is not None else default


def _join(val, sep=" ; "):
    if isinstance(val, list):
        return sep.join(str(v) for v in val)
    return str(val) if val is not None else ""


def format_doc(doc):
    return {
        "hal_id":               doc.get("halId_s", ""),
        "titre":                _first(doc.get("title_s")),
        "sous_titre":           _first(doc.get("subTitle_s")),
        "auteurs":              _join(doc.get("authFullName_s")),
        "orcid":                _join(doc.get("authOrcidId_s")),
        "idhal":                _join(doc.get("authIdHal_s")),
        "role_auteurs":         _join(doc.get("authQuality_s")),
        "date_publication":     str(_first(doc.get("producedDate_tdate", "")))[:10],
        "annee":                doc.get("producedDateY_i", ""),
        "date_depot":           str(_first(doc.get("submittedDate_tdate", "")))[:10],
        "type_document":        doc.get("docType_s", ""),
        "type_depot":           doc.get("submitType_s", ""),
        "langue":               _join(doc.get("language_s")),
        "domaine":              _join(doc.get("domain_s")),
        "revue":                doc.get("journalTitle_s", ""),
        "editeur_revue":        doc.get("journalPublisher_s", ""),
        "issn":                 doc.get("journalIssn_s", ""),
        "conference":           doc.get("conferenceTitle_s", ""),
        "ville":                doc.get("city_s", ""),
        "ouvrage":              doc.get("bookTitle_s", ""),
        "editeur":              doc.get("publisher_s", ""),
        "volume":               doc.get("volume_s", ""),
        "numero":               doc.get("issue_s", ""),
        "pages":                doc.get("page_s", ""),
        "doi":                  doc.get("doiId_s", ""),
        "url_hal":              doc.get("uri_s", ""),
        "acces_ouvert":         doc.get("openAccess_bool", ""),
        "licence":              doc.get("licence_s", ""),
        "laboratoire":          _join(doc.get("labStructName_s")),
        "acronyme_labo":        _join(doc.get("labStructAcronym_s")),
        "institution":          _join(doc.get("instStructName_s")),
        "acronyme_inst":        _join(doc.get("instStructAcronym_s")),
        "collections":          _join(doc.get("collCode_s")),
        # Champs IR officiels
        "ir_acronyme":          _join(doc.get("irThesaurusAcronym_s")),
        "ir_nom":               _join(doc.get("irThesaurusName_s")),
        "ir_identifiant":       _join(doc.get("irThesaurusId_s")),
        "ir_doi":               _join(doc.get("irThesaurusDoi_s")),
        # Financements
        "financement":          _join(doc.get("funding_s")),
        "projet_anr":           _join(doc.get("anrProjectReference_s")),
        "acronyme_anr":         _join(doc.get("anrProjectAcronym_s")),
        "projet_europeen":      _join(doc.get("europeanProjectAcronym_s")),
        "collaboration":        _join(doc.get("collaboration_s")),
        "mots_cles":            _join(doc.get("keyword_s")),
        "resume":               str(_first(doc.get("abstract_s")))[:400],
        "commentaire":          doc.get("comment_s", ""),
    }


# ─────────────────────────────────────────────
# Affichage terminal
# ─────────────────────────────────────────────

def print_summary(docs, counts):
    print("\n" + "=" * 72)
    print(f"  PUBLICATIONS HAL — INFRANALYTICS  ({len(docs)} résultats)")
    print("=" * 72)

    print(f"\n  Sources :")
    for label, n in counts.items():
        print(f"    {label:<45} : {n}")

    type_counts = {}
    for d in docs:
        t = d["type_document"] or "?"
        type_counts[t] = type_counts.get(t, 0) + 1

    print(f"\n  Répartition par type de document :")
    for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t:10s} : {n}")

    print(f"\n  {'#':<4} {'Année':<6} {'Type':<6} {'Titre':<48} {'IR déclaré'}")
    print("  " + "-" * 90)
    for i, doc in enumerate(docs, 1):
        titre = doc["titre"][:46] + ".." if len(doc["titre"]) > 48 else doc["titre"]
        ir = doc["ir_acronyme"][:30] if doc["ir_acronyme"] else "—"
        print(f"  {i:<4} {str(doc['annee']):<6} {doc['type_document']:<6} {titre:<48} {ir}")

    print("\n" + "=" * 72)


# ─────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────

def export_csv(docs, filename):
    if not docs:
        return
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(docs[0].keys()), delimiter=";")
        writer.writeheader()
        writer.writerows(docs)
    print(f"📄 Export CSV  → {filename}")


def export_json(docs_raw, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(docs_raw, f, ensure_ascii=False, indent=2)
    print(f"📦 Export JSON → {filename}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n🔍 Recherche des publications HAL — Infrastructure INFRANALYTICS")
    print("=" * 72)

    # ── Requête 1 : par acronyme (champ officiel recommandé par le webmaster HAL)
    q1 = f'irThesaurusAcronym_s:"{IR_ACRONYM}"'
    print(f"\n[1] Acronyme IR         : {q1}")
    docs1 = fetch_all(q1, label="irThesaurusAcronym_s")

    # ── Requête 2 : par nom (au cas où l'acronyme diffère)
    q2 = f'irThesaurusName_t:"{IR_ACRONYM}"'
    print(f"\n[2] Nom IR              : {q2}")
    docs2 = fetch_all(q2, label="irThesaurusName_t")

    # ── Requête 3 : multicritère IR (filet de sécurité)
    q3 = f'irThesaurus_t:"{IR_ACRONYM}"'
    print(f"\n[3] Multicritère IR     : {q3}")
    docs3 = fetch_all(q3, label="irThesaurus_t")

    # ── Fusion et déduplication (ordre de priorité : acronyme > nom > multi)
    all_raw = deduplicate(docs1 + docs2 + docs3)

    counts = {
        "irThesaurusAcronym_s (acronyme officiel)": len(docs1),
        "irThesaurusName_t    (nom)":               len(docs2),
        "irThesaurus_t        (multicritère)":      len(docs3),
        "Total après déduplication":                len(all_raw),
    }

    print(f"\n✅ Total après déduplication : {len(all_raw)} publication(s)")

    if not all_raw:
        print("⚠️  Aucune publication trouvée.")
        print("   Vérifiez que l'acronyme 'Infranalytics' est bien enregistré")
        print("   dans le référentiel HAL : https://api.archives-ouvertes.fr/ref/metadatalist/?metaName_s=ir")
    else:
        # Tri par année décroissante
        all_raw.sort(
            key=lambda d: d.get("producedDateY_i", 0) or 0,
            reverse=True
        )

        formatted = [format_doc(d) for d in all_raw]

        print_summary(formatted, counts)

        csv_file  = f"hal_infranalytics_{timestamp}.csv"
        json_file = f"hal_infranalytics_{timestamp}.json"

        export_csv(formatted, csv_file)
        export_json(all_raw, json_file)

        print(f"\n✨ Terminé ! {len(formatted)} publication(s) exportée(s).")
        print(f"   CSV  : {csv_file}")
        print(f"   JSON : {json_file}\n")