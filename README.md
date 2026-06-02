[![Logo Infranalytics](img/INFRANALYTICS-logo.png)](https://infranalytics.fr/)

# HAL Infranalytics

Scripts Python pour récupérer les publications de l'infrastructure de recherche **[Infranalytics](https://infranalytics.fr/)** via l'[API HAL](https://api.archives-ouvertes.fr/search/) et les exporter en différents formats.

## Prérequis

- Python 3.6+
- Installer la dépendance :

```bash
pip install requests
```

## Scripts disponibles

### `hal_infra.py` — Export CSV et JSON

Interroge l'API HAL et exporte les publications dans deux fichiers horodatés.

```bash
python hal_infra.py
```

Génère :
- `hal_infranalytics_YYYYMMDD_HHMMSS.csv` — liste formatée, séparateur `;`, encodage UTF-8 BOM (compatible Excel)
- `hal_infranalytics_YYYYMMDD_HHMMSS.json` — réponse brute de l'API HAL

---

### `infralatex.py` — Export LaTeX

Interroge l'API HAL et génère une bibliographie structurée en sections par type de document.

```bash
python infralatex.py
```

Génère :
- `infranalytics_publi.tex` — document LaTeX prêt à compiler

#### Sections générées

| Section | Types HAL |
|---|---|
| Articles dans des revues à comité de lecture | ART |
| Communications dans des congrès | COMM |
| Chapitres d'ouvrage | COUV |
| Ouvrages | OUV |
| Posters | POSTER |
| Rapports | REPORT |
| Thèses | THESE |
| Pré-publications (preprints) | UNDEFINED |
| Logiciels | SOFTWARE |
| Données de recherche | DATA |
| Autres | OTHER |

#### Numérotation

Au sein de chaque section, les publications sont triées de la plus récente (en haut) à la plus ancienne (en bas). La numérotation est en **compte à rebours** : `[1]` désigne la publication la plus ancienne, `[N]` la plus récente.

#### Compiler le fichier LaTeX

```bash
pdflatex infranalytics_publi.tex
```

## Configuration

Les deux scripts partagent les mêmes constantes de configuration en tête de fichier :

| Constante | Rôle |
|---|---|
| `IR_ACRONYM` | Acronyme exact tel qu'enregistré dans le référentiel HAL |
| `FIELDS` | Champs Solr HAL récupérés par document |
| `ROWS_PER_PAGE` | Taille de pagination des requêtes API (défaut : 100) |

> **Important :** `IR_ACRONYM` est sensible à la casse et doit correspondre exactement à la valeur dans le référentiel HAL. Pour vérifier :
> `https://api.archives-ouvertes.fr/ref/metadatalist/?metaName_s=ir`

## Structure du projet

```
hal_infra/
├── hal_infra.py          # Export CSV + JSON
├── infralatex.py         # Export LaTeX
├── img/
│   └── INFRANALYTICS-logo.png
└── tests/
    ├── test_infranalytics_hal.py
    └── test_infralatex.py
```

## Tests

```bash
pip install pytest
pytest tests/
```

## Licence

Ce projet est distribué sous licence [CeCILL-2.1](https://cecill.info/licences/Licence_CeCILL_V2.1-fr.html), licence française open source compatible avec la GPL, recommandée pour les logiciels issus de la recherche publique française.
