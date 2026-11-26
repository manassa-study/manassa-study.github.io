"""Validators (spec section 7). Each module has one job and fixed severities.

V1  configuration          mudhakarah.config (and lock identity in mudhakarah.ids)
V2  content structure      v02_structure (types and options: mudhakarah.model)
V3  IDs                    mudhakarah.ids
V4  duplicates             v04_duplicates (fingerprints: mudhakarah.ids)
V5  internal links         v05_links (item topics: mudhakarah.model)
V6  references             v06_references (page references: format only, a warning, until N4)
V7  missing assets         v07_assets
V8  HTML output            v08_html (data line: mudhakarah.output)
V9  committed output       tools/build.py check
V10 reproducibility        v10_reproducibility
V11 content integrity      v11_integrity
V12 Qur'an comparison      deferred (O-13)
V13 published paths        v13_paths
"""
from . import v02_structure, v04_duplicates, v05_links, v06_references


def model_findings(raw, model, book, where):
    """Stage 4: the validators that read the content and the model."""
    out = []
    out += v02_structure.check(raw, where)
    out += v04_duplicates.check(raw, where)
    out += v05_links.check(model, where)
    out += v06_references.check(model, where)
    return out
