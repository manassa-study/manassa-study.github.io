"""Content loaders (spec section 2, layer 2). Phase 1 has the Python loader only."""
from .python_loader import load_python_content

LOADERS = {"python": load_python_content}


def load_content(repo_root, slug, book):
    loader = LOADERS[book["content"]["loader"]]
    return loader(repo_root, slug, book)
