# OQL + OQLOS Refactoring Plan

## Cel

- [ ] Wydzielić stabilny runtime OQL z `oqlos` do osobnego pakietu (`oql-runtime` / `oql-core`).
- [ ] Ustawić `oql` jako cienki CLI (UX + integracje), bez logiki parser/interpreter.
- [ ] Utrzymać zgodność wsteczną (v3) oraz domyślny runtime v4 z jasną polityką wersjonowania.

## Założenia architektury docelowej

- [ ] `oql-runtime`:
  - parser/tokenizer/builder/interpreter/executor,
  - `oql_versioning` i polityka `legacy/current/supported`,
  - stabilne API Python (`run`, `validate`, `parse`, `resolve_version`).
- [ ] `oql`:
  - tylko CLI (`click`) + adaptery I/O,
  - zero importów do wewnętrznych modułów `oqlos.core.*`.
- [ ] `oqlos`:
  - API HTTP, hardware gateway, plugins,
  - używa `oql-runtime` przez publiczne API.

## Faza 0 — Inwentaryzacja i kontrakty

- [ ] Spisać aktualne punkty wejścia runtime używane przez `oql` i `oqlos`.
- [ ] Zdefiniować kontrakt publicznego API runtime (moduły + klasy + wyjątki).
- [ ] Zamrozić zachowanie referencyjne (golden tests) dla:
  - [ ] `run` (dry-run/execute),
  - [ ] `validate`,
  - [ ] raportowanie (`json`, `junit`, `html`),
  - [ ] rozpoznawanie wersji DSL.

## Faza 1 — Ekstrakcja `oql-runtime`

- [ ] Utworzyć nowe repo/pakiet `oql-runtime` z semver od `0.1.0`.
- [ ] Przenieść z `oqlos/core` do `oql-runtime`:
  - [ ] parsery i tokenizację,
  - [ ] interpreter i executor,
  - [ ] `oql_versioning.py` i walidację wersji,
  - [ ] minimalne modele/typy wymagane przez runtime.
- [ ] Odseparować runtime od FastAPI/hardware (brak importów `oqlos.api`, `oqlos.hardware`).
- [ ] Dodać warstwę kompatybilności importów (deprecation shims) po stronie `oqlos`.

## Faza 2 — Wersjonowanie DSL (v3/v4)

- [ ] Zdefiniować politykę:
  - [ ] `current = 4`,
  - [ ] `legacy = 3`,
  - [ ] jawne błędy dla wersji spoza `supported`.
- [ ] Dodać tryb kompatybilności:
  - [ ] auto-detekcja wersji po nagłówku,
  - [ ] kontrolowany fallback dla scenariuszy bez `VERSION`.
- [ ] Dodać narzędzia migracji:
  - [ ] `oqlctl migrate --from 3 --to 4` (preview + apply),
  - [ ] raport zmian semantycznych (ostrzeżenia i ryzyka).

## Faza 3 — Refaktoryzacja `oql`

- [ ] Zamienić zależność `oqlos>=...` na `oql-runtime>=...` (runtime) + opcjonalnie `oqlos-client` (API).
- [ ] Przepiąć komendy `run/validate/cmd/shell` na API `oql-runtime`.
- [ ] Wydzielić adaptery:
  - [ ] `LocalRuntimeAdapter` (bezpośrednio runtime),
  - [ ] `RemoteApiAdapter` (HTTP do `oqlos`).
- [ ] Zachować kompatybilność CLI (`oqlctl`) i obecnych flag.

## Faza 4 — Refaktoryzacja `oqlos`

- [ ] Podmienić wewnętrzne wywołania runtime na `oql-runtime` API.
- [ ] Uprościć `oqlos/core` do warstwy integracyjnej lub usunąć duplikaty.
- [ ] Przenieść odpowiedzialności:
  - [ ] runtime logic -> `oql-runtime`,
  - [ ] hardware/protocol/api -> `oqlos`.
- [ ] Utrzymać endpointy i kontrakty API bez regresji funkcjonalnych.

## Faza 5 — Testy i jakość

- [ ] Testy kontraktowe runtime (v3/v4, parser/interpreter/executor).
- [ ] Testy integracyjne `oql` (CLI) z mock runtime oraz z real `oql-runtime`.
- [ ] Testy integracyjne `oqlos` (API + hardware mocks) na nowym runtime.
- [ ] Macierz CI:
  - [ ] `oql` x `oql-runtime` (min/max wspierane wersje),
  - [ ] `oqlos` x `oql-runtime` (min/max wspierane wersje).

## Faza 6 — Wydania i migracja zespołu

- [ ] Opublikować `oql-runtime` i oznaczyć status stabilności API.
- [ ] Wydać `oql` z nową zależnością (`oql-runtime`) i changelogiem migracyjnym.
- [ ] Wydać `oqlos` po przepięciu na `oql-runtime`.
- [ ] Dodać deprecations timeline:
  - [ ] kiedy usuwamy stare importy,
  - [ ] kiedy kończy się wsparcie dla v3.

## Kryteria akceptacji

- [ ] `oql` uruchamia scenariusze bez bezpośrednich importów z `oqlos.core.*`.
- [ ] `oqlos` używa tylko publicznego API `oql-runtime`.
- [ ] DSL v4 jest domyślny, v3 działa w trybie kompatybilności.
- [ ] Brak regresji w kluczowych przepływach: `run`, `validate`, `cmd`, raporty.
- [ ] Każdy projekt ma jawnie zdefiniowaną i testowaną kompatybilność wersji runtime.

## Kolejność commitów (proponowana)

- [ ] `chore(runtime): scaffold oql-runtime package`
- [ ] `feat(runtime): move parser/interpreter/versioning from oqlos`
- [ ] `refactor(oql): consume oql-runtime instead of oqlos core`
- [ ] `refactor(oqlos): switch execution path to oql-runtime`
- [ ] `test(ci): add cross-version compatibility matrix`
- [ ] `docs: migration guide v3->v4 and dependency upgrade paths`
