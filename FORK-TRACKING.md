# Fork tracking

Open follow-ups for the `marlon-costa-dc/rope` fork. Update this file whenever an item changes.

## Working rule

- External PRs are followed until their cycle ends (merged or closed).
- Only remote branches are kept. A local worktree is removed as soon as its work is pushed, and recreated when the branch needs work again.
- Unique local work is first pushed to a `preserve/*` ref, judged, then adopted or retired.

## Fork state

- `main` mirrors `python-rope/rope:master`; the scheduled workflow lives on the
  fork's default branch (`master`).
- `dc-use` is the downstream integration branch. Use the full producer commit
  or the artifact SHA-256 when comparing installations.
- The published [1.15.2+dc.6](https://github.com/marlon-costa-dc/rope/releases/tag/1.15.2%2Bdc.6)
  identifies `41b96032`; the later consumer Git pin `4cb40a6f` also declares
  that version. The next downstream package uses a new local version.

## Upstream contributions

Merged: [#845](https://github.com/python-rope/rope/pull/845),
[#921](https://github.com/python-rope/rope/pull/921), and
[#922](https://github.com/python-rope/rope/pull/922).
[#938](https://github.com/python-rope/rope/pull/938) was closed; any upstream
follow-up should be split by behavior for review.

Open with the maintainers:

- [ ] python-rope/rope#920 — Resolve inherited class attributes along the C3 method resolution order (`pr/c3-mro`)
- [ ] python-rope/rope#919 — Type saveit so decorated members keep their return type (`pr/typed-saveit`)
- [ ] python-rope/rope#918 — Add match_filter and import_filter hooks to Restructure (`pr/restructure-hooks`)
- [ ] python-rope/rope#911 — Route filesystem queries through the fscommands owner (`pr/fscommands-routing`)
- [ ] python-rope/rope#910 — Honor namespace-package precedence when resolving imports (`pr/namespace-precedence`)
- [ ] python-rope/rope#909 — Compute scope regions from native AST positions (`pr/scope-regions`)
- [ ] python-rope/rope#908 — Guard type-hint providers and infer X | Y union annotations (`pr/type-hinting-guards`)
- [ ] python-rope/rope#907 — Walk positional-only, keyword-only and annotated parameters in patchedast (`pr/signature-tokens`)
- [ ] python-rope/rope#906 — Find textual occurrence offsets through the tokenizer (`pr/occurrences-tokenizer`)
- [ ] python-rope/rope#882 — patchedast: locate multi-line f-strings, replacement fields and match-sequence delimiters by parser coordinates (`pr/parser-coordinates`)
- [ ] python-rope/rope#844 — Fix patchedast aborting on ''' inside a double-quoted f-string (`fix/joinedstr-triple-quote-in-body`)

## Consumer propagation

Update the Rope pin in FLEXT Infra's codegen configuration and propagate it
through the native generation and upgrade flow. Verify the installed producer
commit and run the consumer refactorings from the new environment. A lockfile
alone does not prove what a consumer imports.

Keep historical `datacosmos` and `Sync` refs until dependent locks and residual
contracts have been reconciled. The MCB lock still refers to `datacosmos`.
