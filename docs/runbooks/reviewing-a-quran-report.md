# Runbook: reviewing a Qur'an report

Status: the Qur'an comparison tool is **deferred** (decision O-13). It does not
exist in Phase 1 and nothing in the build depends on it. This runbook records how
a report will be reviewed once the tool is built (spec section 8).

What exists today:

- V6 warns about Qur'an references (`«البقرة: ١٨٥»`, `«سورة البقرة: ١٢٣»`) that
  name no surah or a verse beyond the surah's length (standard Hafs count).
- The content-change report lists every change to examples' `ayah` and `surah`
  fields and to matn quotations in a separate section, so a reviewer reads them
  explicitly in every content pull request.

When the tool exists:

1. CI attaches one report per book to any pull request that changes Qur'anic
   content. Read the header first: a "Match" means only that the normalized
   letters agree with one edition of one digital text. It does not check
   diacritics, recitation variants, context or meaning, and nothing in the
   report is ever "verified".
2. Read only the entries marked **new** (quoted text changed since the last
   approved report).
3. For each, compare the quoted text, the cited reference and the edition's text
   of that verse. Decide: correct as is, fix the content, or fix the reference.
4. Record the sign-off as decided by O-10 (still open).
5. The report never blocks a build. A wrong quotation is fixed in the content
   through the normal [content change](changing-content.md).
