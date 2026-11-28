# Book sources

One folder per book, named by its slug (Architecture Specification, section 1):

- `book.json`: the book's settings (section 3)
- `content/`: the book's existing Python content files, unchanged (AD-20)
- `ids.lock.json`: the ID lock and change record (section 6, AD-17)
- `README.md`: edition, page numbering, sources and reviewers

This folder is not published (`_config.yml`, decision O-1).

Optional supplementary materials belong in `<slug>/resources/`, with provenance, revision, hash, and a short index in that book's `README.md`. Keep these distinct from original sources, baselines, renderer content, fixtures, ID locks, and generated pages. Link to a canonical external copy instead of duplicating it. See [the onboarding runbook](../docs/runbooks/adding-a-book.md).
