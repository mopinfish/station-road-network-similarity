# Updating this reproduction package

1. Identify the accepted paper version and the specific scientific procedure being added or corrected. New exploratory results do not enter a release until separately accepted.
2. Record the current public release and file hashes, the accepted source inputs/results and their hashes, and a mapping from each procedure to its code, data and expected output. Keep private source paths and research discussions in the private maintenance record.
3. Implement only the required calculation in this package. Do not copy the private repository or import its modules. Preserve previous paper settings; a later study gets separate settings rather than silently changing an earlier paper's defaults.
4. Check data redistribution conditions and attribution for each selected file, including derived data. Review code, metadata, logs and history for private information. Prepare a sanitized provenance record separately from the original records.
5. Test changed rules with small known inputs, reproduce the affected accepted outputs, and run the package's full test suite when integrating changes. Verify execution from an independent directory using only the package and its documented inputs. Reuse fresh unchanged evidence; a documentation-only change does not require road regeneration or rerunning every study.
6. Have an independent reviewer check scientific rules, identifiers, numerical values and data scope. Record findings and fixes. If numerical results change, explain the cause and impact and obtain the author's scientific decision before publishing a correction.
7. Present the exact selected files, hashes, tests, review results, destination, visibility and licensing for author approval. Commit, push and publication are separate from local preparation. Once authorized, create a new immutable version; never overwrite a previously cited release.
8. Verify the published version is retrievable and matches its manifest. Only then update authorized paper availability text with the actual URL and version.

The private maintenance skill is `update-public-research-repo`. It is not needed to execute this package. There is no automatic two-way synchronization or automatic publication.
