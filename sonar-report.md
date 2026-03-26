# Raport SonarQube - Investment Assistant (Rewizja 2)

## Przegląd

| Pole | Wartość |
|---|---|
| Repozytorium | Investment Assistant |
| Projekt SonarCloud | Nie skonfigurowany — analiza lokalna via SonarQube for IDE |
| Data analizy | 2026-03-27 |

> **Uwaga**: Projekt Investment Assistant nie jest skonfigurowany w SonarCloud. Poniższe wyniki pochodzą z lokalnej analizy SonarQube for IDE na wybranych plikach krytycznych.

## Analizowane pliki

| Plik | Język | Wynik |
|---|---|---|
| `backend/app/api/v1/analysis.py` | Python | 1 issue |
| `backend/app/main.py` | Python | Czysto |
| `backend/app/api/v1/fundamental.py` | Python | Czysto |
| `backend/app/core/database.py` | Python | Czysto |
| `backend/app/modules/pipeline.py` | Python | Czysto |
| `backend/app/modules/fundamental_analysis/indices.py` | Python | 2 issues |
| `backend/app/modules/pattern_recognition/iki_detector.py` | Python | 1 issue |
| `frontend/src/app/page.tsx` | TypeScript | Czysto |
| `frontend/src/components/Chart/CandlestickChart.tsx` | TypeScript | Czysto |
| `frontend/src/lib/api.ts` | TypeScript | Czysto |

## Znalezione issues

| # | Severity | Typ | Reguła | Plik | Linia | Opis |
|---|---|---|---|---|---|---|
| 1 | MAJOR | Code Smell | python:S1192 | `analysis.py` | 72 | Zduplikowany literał `"Analysis not found"` — użyty 3× (L72, L80, ~WS). Wyekstrahować do stałej. |
| 2 | MAJOR | Code Smell | python:S3776 | `iki_detector.py` | 65 | Cognitive Complexity = **30** (limit: 15). Funkcja `_find_iki()` wymaga refaktoryzacji. |
| 3 | MINOR | Code Smell | python:S3358 | `indices.py` | 71 | Zagnieżdżone wyrażenie warunkowe: `"luzna" if rate < baseline else "restrykcyjna" if rate > baseline else "neutralna"` — wyekstrahować do niezależnego wyrażenia. |
| 4 | MINOR | Code Smell | python:S3358 | `indices.py` | 150 | Zagnieżdżone wyrażenie warunkowe: `"bycza" if total_score > 10 else "niedzwiedzia" if total_score < -10 else "neutralna"` — jak wyżej. |

## Podsumowanie

| Severity | Bug | Vulnerability | Code Smell | Razem |
|---|---|---|---|---|
| BLOCKER | 0 | 0 | 0 | 0 |
| CRITICAL | 0 | 0 | 0 | 0 |
| MAJOR | 0 | 0 | 2 | 2 |
| MINOR | 0 | 0 | 2 | 2 |
| **Razem** | **0** | **0** | **4** | **4** |

## Security Hotspots

> Brak Security Hotspots wykrytych w analizowanych plikach.

## Korelacja z code-quality-report.md

| SonarQube Issue | Powiązany finding w raporcie jakości |
|---|---|
| S1192: Zduplikowany literał w analysis.py | Nowy — nieujęty wcześniej. Dodać jako Nice to Have. |
| S3776: _find_iki() Cognitive Complexity 30 | Backend Usp. #8 (🟡 Ważne): `_find_iki()` ~65 linii, 4 nesting levels |
| S3358: Zagnieżdżone ternary w indices.py | Powiązane z Backend MK #1: `_score_inflation()` dead logic — cały moduł wymaga przeglądu |

## Rekomendacje

1. **Skonfigurować SonarCloud** dla projektu Investment Assistant, aby uzyskać pełne metryki (coverage, duplications, gate status) na każdym PR.
2. **S3776** (`_find_iki` Cognitive Complexity 30): Priorytetowe — potwierdza ustalenie z code review. Rozbić na mniejsze metody.
3. **S1192** (zduplikowany literal): Wyekstrahować `"Analysis not found"` do stałej `_NOT_FOUND_MSG` w `analysis.py`.
4. **S3358** (nested ternary): Opcjonalne — czytelność, nie krytyczne.

---

## Podsumowanie i rekomendacje

Projekt SeqMcpServer prezentuje się bardzo dobrze pod względem jakości kodu w SonarCloud. Quality Gate przechodzi pomyślnie ze wszystkimi warunkami spełnionymi. Brak bugów i vulnerabilities (rating A w obu kategoriach) świadczy o solidnym podejściu do niezawodności i bezpieczeństwa. Utrzymywalność jest na poziomie A z jedynie 13 code smells, a duplikacja kodu wynosi 0%.

Coverage ogólny (76.6%) jest przyzwoity, choć mógłby być wyższy — natomiast new code coverage na poziomie 96.3% wskazuje, że nowe zmiany są bardzo dobrze pokryte testami, co jest pozytywnym trendem. Wszystkie 13 wykrytych issues to code smells o niskiej do średniej wadze — żadnych BLOCKER ani CRITICAL issues.

Główne wzorce issues to: (1) brak przekazywania `cancellationToken` do metod async (5× CA2016) — systematyczny problem wskazujący na potrzebę ustandaryzowania obsługi tokenu anulowania w narzędziach, (2) brak format providera przy parsowaniu dat (2× S6580) — ryzyko błędów kulturowych, (3) brak await na async method (1× S6966). Wszystkie issues są łatwe do naprawy i nie stanowią zagrożenia dla stabilności aplikacji.

### Natychmiastowe działania
1. Naprawić 2 issues S6580 w `DateRangeHelper.cs` — dodać `CultureInfo.InvariantCulture` lub odpowiedni format provider do parsowania dat. Brak format providera może prowadzić do błędów w środowiskach z różnymi ustawieniami regionalnymi.
2. Naprawić S6966 w `Program.cs` — użyć `await WriteLineAsync()` zamiast synchronicznego `WriteLine` w kontekście async.

### Krótkoterminowe
1. Ustandaryzować przekazywanie `CancellationToken` we wszystkich narzędziach (5 plików: AlertsTool, DashboardsTool, QueryLogsTool, RetentionPoliciesTool, SignalsTool, SqlQueryTool) — dodać propagację tokenu do metod `ListAsync`/`QueryAsync`.
2. Naprawić S6573 w `release.yml` — dodać prefix `./` do ścieżek glob w GitHub Actions workflow.
3. Zastosować `StartsWith(char)` zamiast `StartsWith(string)` w `QueryLogsTool.cs` (S6610/CA1866).
4. Rozważyć eliminację hardkodowanego URI w `Program.cs` (S1075).

## Powiązane raporty

| Raport | Opis |
|---|---|
| [code-quality-report.md](code-quality-report.md) | Raport jakości kodu — martwy kod, duplikacje, usprawnienia, architektura |
