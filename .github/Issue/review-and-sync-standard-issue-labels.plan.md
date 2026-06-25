# Review and Sync Standard Issue Labels - Plan Implementacji

## Szczegóły Zadania

| Pole | Wartość |
|---|---|
| Tytuł | Review and sync standard issue labels |
| Opis | Review the standard issue-label set and keep the repo-local metadata in sync with the GitHub repository state. |
| Priorytet | Medium |
| Powiązany Research | - |
| Numer Issue | 4 |
| Link do Issue | https://github.com/Finfinder/Investment-Assistant/issues/4 |

## Proponowane Rozwiązanie

Zadanie polega na synchronizacji lokalnego pliku `.github/gh-sync.json` z aktualnym stanem etykiet (labels) w repozytorium GitHub. Wymaga to:

1. Dodania 6 brakujących etykiet do `gh-sync.json` (etykiety istniejące na GitHub, ale nie w lokalnej konfiguracji)
2. Rozwiązania problemu z nieistniejącymi etykietami w `dependabot.yml` (4 etykiety nieistniejące ani lokalnie ani na GitHub)
3. Weryfikacji spójności referencji do etykiet w szablonach issue i plikach workflow

## Uzasadnienie Rozwiązania

### Wybrane podejście

**Synchronizacja w obie strony** — uaktualnienie `gh-sync.json` o brakujące etykiety z GitHub oraz dodanie brakujących etykiet technologicznych (`dependabot`, `python`, `javascript`, `ci`) wymaganych przez `dependabot.yml`.

### Porównanie z alternatywami

| Kryterium | Pełna synchronizacja (wybrane) | Tylko gh-sync.json | Usunięcie z dependabot.yml |
|---|---|---|---|
| Spójność metadanych | ✅ Pełna | ⚠️ Częściowa | ⚠️ Częściowa |
| Dependabot działa poprawnie | ✅ Tak | ❌ Brak etykiet | ✅ Tak (bez etykiet) |
| Zgodność z best practices | ✅ Tak | ⚠️ Częściowa | ⚠️ Częściowa |

### Dlaczego odrzucono alternatywy
- **Tylko gh-sync.json**: Pozostawia `dependabot.yml` z referencjami do nieistniejących etykiet — Dependabot nie przypisze PR do żadnej etykiety
- **Usunięcie z dependabot.yml**: Utrata wartościowej kategoryzacji PR zależności (dependabot, python, javascript, ci)

## Rejestry Decyzji Architektonicznej (ADR)

### ADR-001: Dodanie etykiet technologicznych dla Dependabota

| Pole | Wartość |
|---|---|
| Status | Proponowany |
| Data | 2026-06-25 |
| Kontekst | `dependabot.odbc` odwołuje się do etykiet `dependabot`, `python`, `javascript`, `ci`, które nie istnieją w repozytorium. Należy zdecydować czy je utworzyć, czy usunąć referencje. |

**Rozważane opcje**:
1. **Dodać 4 etykiety technologiczne** (`dependabot`, `python`, `javascript`, `ci`) do `gh-sync.json` i zsynchronizować z GitHub
2. **Usunąć nieistniejące etykiety** z `dependabot.yml` — PR nie będą miały etykiet technologicznych

**Decyzja**: Opcja 1 — dodanie etykiet technologicznych. Uzasadnienie: lepsza kategoryzacja PR, zgodność z best practices Dependabota.

**Konsekwencje**:
- ✅ Lepsza widoczność i kategoryzacja PR zależności
- ✅ Zachowanie pełnej funkcjonalności `dependabot.yml`
- ⚠️ Zwiększenie liczby etykiet w repozytorium (z 16 do 20)

## Analiza Aktualnej Implementacji

### Już Zaimplementowane
Lista istniejących komponentów, funkcji i narzędzi, które zostaną ponownie użyte:
- `gh-sync.json` - `.github/gh-sync.json` - lokalna konfiguracja 10 etykiet (wymaga rozszerzenia)
- `issue-seed.json` - `.github/issue-seed.json` - seed issue używający tylko istniejących etykiet (technical-debt, infrastructure, priority:high, frontend, documentation)
- `bug-report.yml` - `.github/ISSUE_TEMPLATE/bug-report.yml` - szablon z etykietą `bug` (istnieje)
- `feature-request.yml` - `.github/ISSUE_TEMPLATE/feature-request.yml` - szablon z etykietą `enhancement` (istnieje)
- `dependabot.yml` - `.github/dependabot.yml` - konfiguracja z referencjami do 4 nieistniejących etykiet

### Do Modyfikacji
Lista istniejącego kodu, który wymaga zmian lub rozszerzeń:
- `gh-sync.json` - `.github/gh-sync.json` - dodać 10 etykiet (6 z GitHub + 4 technologiczne dla Dependabota)

### Do Utworzenia
Lista nowych komponentów, funkcji i narzędzi, które trzeba zbudować od podstaw:
- Brak — zadanie wyłącznie konfiguracyjne

## Otwarte Pytania

| # | Pytanie | Odpowiedź | Status |
|---|----------|-----------|--------|
| 1 | Czy etykiety technologiczne (`dependabot`, `python`, `javascript`, `ci`) mają zostać dodane do repozytorium? | Tak — wymagane przez `dependabot.yml` | ✅ Rozwiązane |
| 2 | Czy kolory dla nowych etykiet technologicznych są zgodne z konwencją? | Użyto kolorów zgodnych z konwecją GitHub (np. `dependabot` = `0366d6`, `python` = `3572A5`, `javascript` = `f1e05a`, `ci` = `5319e7`) | ✅ Rozwiązane |

## Plan Implementacji

### Faza 1: Aktualizacja gh-sync.json

#### Zadanie 1.1 - [MODYFIKUJ] Dodaj brakujące etykiety z GitHub do gh-sync.json
**Opis**: Rozszerzyć sekcję `labels` w `.github/gh-sync.json` o 6 etykiet istniejących na GitHub, ale brakujących w lokalnej konfiguracji: `duplicate`, `good first issue`, `help wanted`, `invalid`, `question`, `wontfix`. Każda etykieta musi mieć zgodny `name`, `color` i `description` z danymi z GitHub API.

**Definicja Ukończenia (Definition of Done)**:
- [x] Dodano etykietę `duplicate` (color: `cfd3d7`, description: "This issue or pull request already exists")
- [x] Dodano etykietę `good first issue` (color: `7057ff`, description: "Good for newcomers")
- [x] Dodano etykietę `help wanted` (color: `008672`, description: "Extra attention is needed")
- [x] Dodano etykietę `invalid` (color: `e4e669`, description: "This doesn't seem right")
- [x] Dodano etykietę `question` (color: `d876e3`, description: "Further information is requested")
- [x] Dodano etykietę `wontfix` (color: `ffffff`, description: "This will not be worked on")
- [x] Plik `gh-sync.json` jest poprawnym JSON (walidacja `ConvertFrom-Json`)

#### Zadanie 1.2 - [MODYFIKUJ] Dodaj etykiety technologiczne dla Dependabota do gh-sync.json
**Opis**: Dodać 4 etykiety wymagane przez `.github/dependabot.yml`: `dependabot`, `python`, `javascript`, `ci`. Kolory zgodne z konwencją GitHub i unikalne względem istniejących etykiet.

**Definicja Ukończenia (Definition of Done)**:
- [x] Dodano etykietę `dependabot` (color: `006b75`, description: "Dependabot dependency update.")
- [x] Dodano etykietę `python` (color: `3572a5`, description: "Python language or ecosystem topic.")
- [x] Dodano etykietę `javascript` (color: `f1e05a`, description: "JavaScript/TypeScript language or ecosystem topic.")
- [x] Dodano etykietę `ci` (color: `bfdadc`, description: "Continuous integration, workflows, or automation topic.")
- [x] Wszystkie kolory etykiet są unikalne i w formacie lowercase hex
- [x] Plik `gh-sync.json` zawiera łącznie 20 etykiet (10 oryginalnych + 6 z GitHub + 4 technologiczne)

### Faza 2: Weryfikacja spójności

#### Zadanie 2.1 - [REUSE] Weryfikacja referencji do etykiet w szablonach i workflow
**Opis**: Sprawdzić, czy wszystkie referencje do etykiet w `.github/ISSUE_TEMPLATE/*.yml`, `.github/dependabot.yml` oraz `.github/workflows/*.yml` wskazują na istniejące etykiety (po aktualizacji `gh-sync.json`).

**Definicja Ukończenia (Definition of Done)**:
- [x] Wszystkie etykiety w `bug-report.yml` istnieją w `gh-sync.json`
- [x] Wszystkie etykiety w `feature-request.yml` istnieją w `gh-sync.json`
- [x] Wszystkie etykiety w `dependabot.yml` istnieją w `gh-sync.json`
- [x] Wszystkie etykiety w `issue-seed.json` istnieją w `gh-sync.json`
- [x] Brak referencji do nieistniejących etykiet w żadnym pliku konfiguracyjnym

### Faza 3: Walidacja i dokumentacja

#### Zadanie 3.1 - [REUSE] Uruchomienie dry-run synchronizacji
**Opis**: Uruchomić workflow `sync-dry-run` (lub lokalnie skrypt PowerShell) weryfikując spójność `gh-sync.json` z GitHub.

**Definicja Ukończenia (Definition of Done)**:
- [x] Workflow `sync-dry-run` przechodzi bez błędów
- [x] Brak ostrzeżeń o nieistniejących etykietach
- [x] Log dry-run nie zawiera komunikatów o potencjalnych konfliktach

#### Zadanie 3.2 - [MODYFIKUJ] Aktualizacja CHANGELOG.md
**Opis**: Dodać wpis w sekcji `[Unreleased]` opisujący synchronizację etykiet.

**Definicja Ukończenia (Definition of Done)**:
- [x] Dodano wpis w `CHANGELOG.md` w sekcji `[Unreleased]` zgodnie z format Keep a Changelog
- [x] Wpis opisuje dodanie brakujących etykiet i synchronizację z GitHub

## Aspekty Bezpieczeństwa

- Brak — zadanie dotyczy wyłącznie metadanych repozytorika (etykiety), nie wprowadza zmian w kodzie ani konfiguracji bezpieczeństwa.

## Strategia Testowania

### Piramida testów

| Typ testu | Zakres | Szacowana liczba | Pokrycie |
|---|---|---|------|
| Jednostkowe | Walidacja JSON, unikalność nazw etykiet | 2 | 100% poprawności struktury |
| Integracyjne | Spójność referencji między plikami | 1 | Wszystkie pliki konfiguracyjne |
| E2E | Brak — zadanie konfiguracyjne | 0 | N/A |

### Podejście do testowania
- [x] Walidacja struktury JSON (`ConvertFrom-Json` w PowerShell)
- [x] Weryfikacja unikalności nazw etykiet
- [x] Cross-check referencji do etykiet między plikami

### Testy wydajnościowe
Nie dotyczy — zadanie konfiguracyjne bez wpływu na wydajność.

### Testy dostępności
Nie dotyczy — zadanie konfiguracyjne bez komponentów UI.

### Testy architektoniczne
Nie dotyczy — zadanie nie definiuje granic modułów.

### Testy mutacyjne
Nie dotyczy — zadanie konfiguracyjne bez logiki biznesowej.

## Zapewnienie Jakości

Lista kontrolna kryteriów akceptacji do weryfikacji, że implementacja spełnia zdefiniowane wymagania:

- [x] `gh-sync.json` zawiera wszystkie 20 etykiet (10 oryginalnych + 6 brakujących z GitHub + 4 technologiczne)
- [x] Wszystkie etykiety mają poprawne pola: `name`, `color`, `description`
- [x] Kolory etykiet są zgodne z GitHub (format hex bez `#`), unikalne i lowercase
- [x] Wszystkie referencje w `dependabot.yml` wskazują na istniejące etykiety
- [x] Wszystkie referencje w `ISSUE_TEMPLATE/*.yml` wskazują na istniejące etykiety
- [x] Plik `gh-sync.json` jest poprawnym JSON
- [x] Workflow `sync-dry-run` przechodzi bez błędów
- [x] `CHANGELOG.md` zawiera wpis o zmianie (w sekcjach `### Added` i `### Fixed`)

### Planowane quality gates z kontraktu `code-reviewing`

| Obszar | Planowana kontrola | Kryterium akceptacji |
| --- | --- | --- |
| Bezpieczeństwo | Brak sekretów w konfiguracji | `gh-sync.json` nie zawiera poświadczeń ani kluczy |
| Architektura i jakość | Poprawność JSON, spójność referencji | Walidacja JSON przechodzi, brak referencji do nieistniejących etykiet |
| Operacyjność | Workflow sync-dry-run przechodzi | Brak błędów w logu dry-run |

## Usprawnienia (Poza Zakresem)

Potencjalne usprawnienia zidentyfikowane podczas planowania, które nie są częścią bieżącego zadania:

### Usprawnienie 1: Automatyczna synchronizacja etykiet przez GitHub Actions

- **Opis**: Utworzenie workflow automatycznie synchronizującego etykiety z `gh-sync.json` do GitHub przy każdym push do main.
- **Uzasadnienie**: Obecnie synchronizacja wymaga ręcznego uruchomienia skryptów. Automatyzacja zapobiegnie rozbieżnościom w przyszłości.
- **Korzyści**: Eliminacja ryzyka rozbieżności między lokalną konfiguracją a stanem na GitHub, redukcja manualnej pracy przy zarządzaniu metadanymi repozytorium.

### Usprawnienie 2: Walidacja etykiet w PR template

- **Opis**: Dodanie walidacji etykiet w `PULL_REQUEST_TEMPLATE.md` — przypomnienie o przypisaniu odpowiednich etykiet (backend/frontend/infrastructure) do PR.
- **Uzasadnienie**: Ułatwia kategoryzację PR i śledzenie postępu według obszarów.
- **Korzyści**: Lepsza widoczność pracy według obszarów, łatwiejsze filtrowanie i raportowanie postępu.

## Code Review Findings

Przegląd wykonany 2026-06-25 przez trzy wyspecjalizowane podprompty: `/review-it`, `/review-security`, `/review-code`.

### IT/Business Review

| Aspekt | Ocena |
|---|---|
| Definition of Done | ✅ Wszystkie zadania ukończone (6/6 Faza 1, 5/5 Faza 2, 3/3 Faza 3) |
| Kryteria akceptacji | ✅ 8/8 spełnione |
| Quality gates | ✅ 3/3 zielone |
| Blokery | ❌ Brak |

**Ostrzeżenia:**
- W1: Współdzielone kolory — `frontend`/`dependabot` → `0366d6`, `backend`/`ci` → `5319e7`
- W2: Wielkość liter w kolorze — `python` ma `3572A5` (wielkie A), reszta małe litery

### Security Review

| Aspekt | Ocena |
|---|---|
| Sekrety/credentials | ✅ Czyste |
| Poprawność JSON | ✅ Poprawny |
| UTF-8 BOM | ✅ Brak |
| XSS/Injection | ✅ Czyste |

**Ostrzeżenia:**
- W1: Brak walidacji path traversal w `bodyPath` (w `sync-github-meta.ps1`, nie w tym pliku)
- W2: Brak sanityzacji `repo.slug` w wywołaniach API (w `sync-github-meta.ps1`, nie w tym pliku)

**Uwaga:** Oba ostrzeżenia dotyczą skryptu konsumującego `gh-sync.json`, nie samego pliku konfiguracji. Rekomendowane jako follow-up task.

### Code Quality Review

| Aspekt | Ocena |
|---|---|
| Poprawność JSON | ✅ Walidacja `json.load()` bez błędów |
| Kodowanie | ✅ UTF-8 bez BOM, LF, brak U+FFFD |
| Spójność formatowania | ⚠️ Drobne niezgodności (W1-W3) |

**Ostrzeżenia:**
- W1: `python` kolor `3572A5` → powinno być `3572a5` (spójność z resztą)
- W2: Zduplikowane kolory między etykietami (backend/ci, frontend/dependabot)
- W3: 6 etykiet bez kropki kończącej opis (zgodne z oryginalnymi opisami GitHub)

### Podsumowanie przeglądu

| Kategoria | Liczba |
|---|---|
| Krytyczne | 0 |
| Ostrzeżenia | 5 (niekrytyczne, kosmetyczne) |
| Info | 8 |

**Werdykt:** ✅ Implementacja zgodna z planem, gotowa do merge. Ostrzeżenia niekrytyczne — mogą być adresowane opcjonalnie.

## Post-Review Fixes (commit 1f15543)

### W1 (Code Quality) — Kolor python
- **Zmiana**: `3572A5` → `3572a5` w `.github/gh-sync.json`
- **Status**: ✅ Naprawione

### W2 (Code Quality/IT) — Współdzielone kolory
- **Zmiana**: `dependabot` → `006b75` (ciemny teal), `ci` → `bfdadc` (jasny teal)
- **Status**: ✅ Naprawione

### W3 (Code Quality) — Opisy bez kropki
- **Status**: ✅ Zachowane celowo (zgodne z oryginalnymi opisami GitHub)

### W4 (Security) — Path traversal w bodyPath
- **Zmiana**: Dodano walidację `[System.IO.Path]::GetFullPath()` + `StartsWith($repoRoot)` w `Sync-RoadmapIssue`
- **Status**: ✅ Naprawione

### W5 (Security) — Sanityzacja repo.slug
- **Zmiana**: Dodano walidację regex `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` w `Get-SyncConfig`
- **Status**: ✅ Naprawione

## Post-Fixes Review (2026-06-25)

### IT/Business Review
| Aspekt | Ocena |
|---|---|
| Definition of Done | ✅ Wszystkie zadania ukończone |
| Kryteria akceptacji | 7/8 ✅, 1 ❓ (sync-dry-run nie zweryfikowany w review) |
| Poprawki W1-W5 | ✅ Wszystkie wdrożone |

**Ostrzeżenia:**
- Plan nie zaktualizowany po review fixes (kolory w DoD nadal oryginalne)
- sync-dry-run nie zweryfikowany w tym review

### Security Review
| Aspekt | Ocena |
|---|---|
| Path traversal guard | ✅ Działa, ale edge case z prefiksem (W4-1) |
| Slug validation | ✅ Poprawny regex |

**Ostrzeżenia:**
- W4-1: `StartsWith` bez separatora katalogu — teoretyczny prefix bypass
- W5-1: Komunikat błędu ujawnia surową wartość slug

### Code Quality Review
| Aspekt | Ocena |
|---|---|
| JSON | ✅ Poprawny, 20 etykiet, wszystkie kolory unikalne i lowercase |
| PowerShell | ✅ Idiomatyczny, czytelny |
| CHANGELOG | ⚠️ Wpis pod `### Added` zamiast `### Fixed` |

**Ostrzeżenia:**
- W1: Path traversal prefix bypass (jedno z Security)
- W2: CHANGELOG wpis powinien być pod `### Fixed` zamiast `### Added`

### Podsumowanie

| Kategoria | Liczba |
|---|---|
| Krytyczne | 0 |
| Ostrzeżenia | 4 (W4-1, W5-1, plan niespójny, CHANGELOG sekcja) |
| Info | 6 |

**Werdykt:** ✅ Poprawki prawidłowo wdrożone. Ostrzeżenia niekrytyczne — mogą być adresowane opcjonalnie.

## Changelog

| Data | Opis Zmiany |
|------|-------------------|
| 2026-06-25 | Utworzono wstępny plan synchronizacji etykiet |
| 2026-06-25 | Zaktualizowano gh-sync.json o 10 etykiet (6 z GitHub + 4 technologiczne) |
| 2026-06-25 | Zweryfikowano spójność referencji do etykiet w szablonach i workflow |
| 2026-06-25 | Uruchomiono dry-run synchronizacji bez błędów |
| 2026-06-25 | Zaktualizowano CHANGELOG.md |
| 2026-06-25 | Wykonano code review (IT/Security/Quality) — 0 krytycznych, 5 ostrzeżeń niekrytycznych |
| 2026-06-25 | Naprawiono W1 (kolor python), W2 (unikalne kolory), W4 (path traversal), W5 (sanityzacja slug) |
| 2026-06-25 | Wykonano post-fixes review — 0 krytycznych, 4 ostrzeżenia niekrytyczne |
| 2026-06-25 | Naprawiono W4-1 (separator katalogu w path traversal), W5-1 (ogólny komunikat błędu slug), CHANGELOG sekcja, plan DoD |
