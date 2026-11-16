# Change log

## paper1-v0.1.1 — 2026-11-16

Restore the original CRLF bytes in 23 TSV files that Git normalized to LF in paper1-v0.1.0. Numerical values, algorithms and expected results are unchanged. Add `.gitattributes` to preserve exact file bytes on commit and checkout. Version 0.1.0 has manifest mismatches for these files and should not be used for byte-level reproduction; its tag remains unchanged.

## paper1-v0.1.0 — 2026-11-16

New minimal numerical implementations from saved paper indicators and adopted analysis settings. The executable workflow starts from saved indicators; upstream road-generation reproduction is outside its scope.

Selected MIT for original code/tests/technical documentation; data are excluded from that grant. Added research-team and university affiliation credits, licensing scope and software citation metadata.

Released the saved-input disclosure supplement and data terms: adopted classifications/decisions, station representatives, unchanged regional layer, upstream methods and source notices. Scientific code and existing numerical inputs are unchanged; no new analysis.
