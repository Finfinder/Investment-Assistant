"""Candlestick pattern detection using TA-Lib."""

import numpy as np
import talib

from app.core.models import OHLCVData, PatternCategory, PatternDetection

# Liczba świec wstecz do skanowania (ostatnia to "wyłaniająca się", starsze to "wypełnione")
_SCAN_CANDLES = 10

_INDICATION_REVERSAL = "Odwrót"
_INDICATION_BULLISH_REVERSAL = "Odwrót bycza"
_INDICATION_BEARISH_REVERSAL = "Odwrót niedźwiedzi"
_INDICATION_STRONG_MOMENTUM = "Silny impet"
_INDICATION_BULLISH_MOMENTUM = "Silny impet bycza"
_INDICATION_BEARISH_MOMENTUM = "Silny impet niedźwiedzia"
_INDICATION_TREND_CONTINUATION = "Kontynuacja trendu"
_INDICATION_BULLISH_CONTINUATION = "Kontynuacja bycza"
_INDICATION_BEARISH_CONTINUATION = "Kontynuacja niedźwiedzia"

# Mapowanie: nazwa funkcji TA-Lib → metadane formacji
# Klucze: name (EN), description (EN), indication (PL), detailed_description (PL)
CANDLESTICK_PATTERNS: dict[str, dict[str, str]] = {
    "CDLENGULFING": {
        "name": "Engulfing",
        "description": "Bullish/Bearish Engulfing pattern",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Formacja objęcia (Engulfing) składa się z dwóch świec, gdzie druga świeca całkowicie "
            "obejmuje ciało pierwszej. Wersja bycza — duża zielona świeca po małej czerwonej — sygnalizuje "
            "odwrót trendu spadkowego. Wersja niedźwiedzia (nóż) — duża czerwona świeca po małej zielonej — "
            "wskazuje na możliwy koniec trendu wzrostowego."
        ),
    },
    "CDLHAMMER": {
        "name": "Hammer",
        "description": "Hammer — potential bullish reversal",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Młot (Hammer) to formacja jednościecowa z małym ciałem na górze i długim dolnym cieniem "
            "(co najmniej 2× ciało). Pojawia się po trendzie spadkowym i sugeruje, że byki zaczęły "  # noqa: RUF001
            "przejmować kontrolę. Im dłuższy dolny cień i mniejsze górne, tym silniejszy sygnał."
        ),
    },
    "CDLDOJI": {
        "name": "Doji",
        "description": "Doji — market indecision",
        "indication": "Niezdecydowanie",
        "detailed_description": (
            "Doji to formacja jednościecowa, w której cena otwarcia i zamknięcia są praktycznie równe, "
            "tworząc krzyż lub znak plus. Oznacza równowagę sił między bykami a niedźwiedziami. "
            "Pojawienie się Doji po długim trendzie może zapowiadać odwrót lub konsolidację."
        ),
    },
    "CDLSHOOTINGSTAR": {
        "name": "Shooting Star",
        "description": "Shooting Star — potential bearish reversal",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Spadająca gwiazda (Shooting Star) ma małe ciało na dole i długi górny cień (co najmniej 2× ciało). "  # noqa: RUF001
            "Pojawia się po trendzie wzrostowym — byki wypchnęły cenę wysoko, ale niedźwiedzie zepchnęły ją "
            "z powrotem na zamknięcie blisko otwarcia. Silny sygnał odwrotu przy dużym wolumenie."
        ),
    },
    "CDLMORNINGSTAR": {
        "name": "Morning Star",
        "description": "Morning Star — bullish reversal",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Gwiazda poranna (Morning Star) to trójświecowa formacja bycza: duża czarna świeca, mała "
            "świeca (luka w dół), duża biała świeca zamykająca się powyżej środka pierwszej. "
            "Jeden z najpewniejszych sygnałów zakończenia trendu spadkowego i początku wzrostowego."
        ),
    },
    "CDLEVENINGSTAR": {
        "name": "Evening Star",
        "description": "Evening Star — bearish reversal",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Gwiazda wieczorna (Evening Star) to trójświecowa formacja niedźwiedzia: duża biała świeca, "
            "mała świeca (luka w górę), duża czarna świeca zamykająca się poniżej środka pierwszej. "
            "Zapowiada koniec trendu wzrostowego i możliwy początek spadkowego."
        ),
    },
    "CDLHARAMI": {
        "name": "Harami",
        "description": "Harami — potential reversal",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Harami (z japońskiego: ciężarna) to dwuświecowa formacja, gdzie mała świeca mieści się "
            "całkowicie wewnątrz ciała poprzedniej dużej świecy. Sygnalizuje utratę impetu przez "
            "dominującą stronę rynku i możliwy odwrót lub konsolidację."
        ),
    },
    "CDLPIERCING": {
        "name": "Piercing",
        "description": "Piercing Line — bullish reversal",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Linia przebicia (Piercing Line) to dwuświecowa bycza formacja odwrotu. Składa się z dużej "
            "czarnej świecy i następującej po niej białej świecy, która otwiera się poniżej minimum "
            "poprzedniej, a zamyka powyżej jej połowy. Sugeruje, że byki przejęły inicjatywę."
        ),
    },
    "CDLDARKCLOUDCOVER": {
        "name": "Dark Cloud Cover",
        "description": "Dark Cloud Cover — bearish reversal",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Czarna chmura (Dark Cloud Cover) to dwuświecowa niedźwiedzia formacja odwrotu. Duża biała "
            "świeca zostaje przykryta czarną świecą, która otwiera się powyżej maximum poprzedniej, "
            "a zamyka poniżej jej środka. Wskazuje na przejęcie kontroli przez niedźwiedzie."
        ),
    },
    "CDL3WHITESOLDIERS": {
        "name": "Three White Soldiers",
        "description": "Three White Soldiers — strong bullish continuation",
        "indication": _INDICATION_BULLISH_CONTINUATION,
        "detailed_description": (
            "Trzej biali żołnierze (Three White Soldiers) to trzy kolejne długie białe świece, każda "
            "otwierająca się w ciele poprzedniej i zamykająca przy własnym maksimum. To jeden z "
            "najsilniejszych sygnałów byczej kontynuacji — pokazuje konsekwentny napływ kupujących."
        ),
    },
    "CDL3BLACKCROWS": {
        "name": "Three Black Crows",
        "description": "Three Black Crows — strong bearish continuation",
        "indication": _INDICATION_BEARISH_CONTINUATION,
        "detailed_description": (
            "Trzy czarne kruki (Three Black Crows) to trzy kolejne długie czarne świece, każda "
            "otwierająca się w ciele poprzedniej i zamykająca przy własnym minimum. Silny sygnał "
            "niedźwiedziej kontynuacji — pokazuje systematyczny napływ sprzedających."
        ),
    },
    "CDLINVERTEDHAMMER": {
        "name": "Inverted Hammer",
        "description": "Inverted Hammer — potential bullish reversal",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Odwrócony młot (Inverted Hammer) to jednościecowa formacja z małym ciałem na dole "
            "i długim górnym cieniem. Pojawia się po trendzie spadkowym — mimo że niedźwiedzie "
            "zepchnęły cenę, byki próbowały walczyć. Wymaga potwierdzenia kolejną byczą świecą."
        ),
    },
    "CDLHANGINGMAN": {
        "name": "Hanging Man",
        "description": "Hanging Man — potential bearish reversal",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Wisielec (Hanging Man) wygląda jak Hammer, ale pojawia się po trendzie wzrostowym. "
            "Małe ciało na górze z długim dolnym cieniem sugeruje, że mimo próby wzrostu "
            "niedźwiedzie zepchnęły cenę wyraźnie w dół. Wymaga potwierdzenia kolejną świecą."
        ),
    },
    "CDLMARUBOZU": {
        "name": "Marubozu",
        "description": "Marubozu — strong momentum candle",
        "indication": _INDICATION_STRONG_MOMENTUM,
        "detailed_description": (
            "Marubozu to świeca bez cieni (lub z bardzo krótkimi) — otwarcie równa się minimum/maksimum, "
            "zamknięcie równa się maksimum/minimum. Biała Marubozu to znak dominacji byków przez całą "
            "sesję, czarna — dominacji niedźwiedzi. Bardzo silny sygnał momentum."
        ),
    },
    "CDLSPINNINGTOP": {
        "name": "Spinning Top",
        "description": "Spinning Top — market indecision",
        "indication": "Niezdecydowanie",
        "detailed_description": (
            "Kręcący bąk (Spinning Top) to świeca z małym ciałem i relatywnie długimi cieniami po "
            "obu stronach. Oznacza niepewność rynku i równowagę sił. Po silnym trendzie może "
            "zapowiadać konsolidację lub odwrót — wymaga potwierdzenia kolejną świecą."
        ),
    },
    # 13 NOWYCH FORMACJI
    "CDLHARAMICROSS": {
        "name": "Harami Cross",
        "description": "Harami Cross — Doji inside previous candle",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Harami Cross to wzmocniona wersja Harami, gdzie mała wewnętrzna świeca jest Doji "
            "(otwarcie ≈ zamknięcie). Pokazuje całkowite niezdecydowanie rynku po wyraźnym ruchu "
            "dominującej strony. Silniejszy sygnał odwrotu niż zwykłe Harami."
        ),
    },
    "CDLEVENINGDOJISTAR": {
        "name": "Evening Doji Star",
        "description": "Evening Doji Star — bearish reversal with Doji gap",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Wieczorna gwiazda Doji (Evening Doji Star) to wersja Gwiazdy Wieczornej, gdzie środkowa "
            "świeca jest Doji. Doji po luce w górę od dużej białej świecy sygnalizuje całkowite "
            "zatrzymanie hossy. Uważany za jeden z najsilniejszych niedźwiedzich sygnałów odwrotu."
        ),
    },
    "CDLMORNINGDOJISTAR": {
        "name": "Morning Doji Star",
        "description": "Morning Doji Star — bullish reversal with Doji gap",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Poranna gwiazda Doji (Morning Doji Star) to wersja Gwiazdy Porannej, gdzie środkowa "
            "świeca jest Doji. Doji po luce w dół od dużej czarnej świecy sygnalizuje całkowite "
            "zatrzymanie bessy. Jeden z najsilniejszych byczych sygnałów odwrotu."
        ),
    },
    "CDLDOJISTAR": {
        "name": "Doji Star",
        "description": "Doji Star — reversal signal with gap",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Gwiazda Doji (Doji Star) to Doji pojawiający się z luką od poprzedniej świecy. "
            "Po trendzie wzrostowym z luką w górę sygnalizuje niedźwiedzi odwrót; po trendzie "
            "spadkowym z luką w dół — byczy. Wymaga potwierdzenia kolejną świecą."
        ),
    },
    "CDL3OUTSIDE": {
        "name": "Three Outside Up/Down",
        "description": "Three Outside Up/Down — confirmed Engulfing reversal",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Trzy zewnętrzne (Three Outside Up/Down) to rozszerzenie formacji Engulfing o potwierdzającą "
            "trzecią świecę. Three Outside Up (bycza): Engulfing + biała świeca zamykająca się wyżej. "
            "Three Outside Down (niedźwiedzia): Engulfing niedźwiedzi + czarna świeca zamykająca się niżej. "
            "Potwierdzenie trzecią świecą zwiększa wiarygodność sygnału."
        ),
    },
    "CDL3INSIDE": {
        "name": "Three Inside Up/Down",
        "description": "Three Inside Up/Down — confirmed Harami reversal",
        "indication": _INDICATION_REVERSAL,
        "detailed_description": (
            "Trzy wewnętrzne (Three Inside Up/Down) to rozszerzenie formacji Harami o potwierdzającą "
            "trzecią świecę. Three Inside Up (bycza): Harami bycza + biała świeca zamykająca się wyżej "
            "niż pierwsza. Three Inside Down (niedźwiedzia): Harami niedźwiedzia + czarna świeca niżej. "
            "Potwierdzenie trzecią świecą czyni sygnał bardziej wiarygodnym."
        ),
    },
    "CDLRISEFALL3METHODS": {
        "name": "Rising/Falling Three Methods",
        "description": "Rising/Falling Three Methods — trend continuation",
        "indication": _INDICATION_TREND_CONTINUATION,
        "detailed_description": (
            "Trzy metody rosnące/spadające (Rising/Falling Three Methods) to pięcioświecowa formacja "
            "kontynuacji. Rising Three Methods: duża biała świeca, trzy małe czerwone (korekta w górnym "
            "kanale), duża biała świeca powyżej poprzednich. Falling Three Methods — lustrzane odbicie. "
            "Sygnalizuje pauzę i kontynuację dominującego trendu."
        ),
    },
    "CDLXSIDEGAP3METHODS": {
        "name": "Upside/Downside Gap Three Methods",
        "description": "Gap Three Methods — gap continuation pattern",
        "indication": _INDICATION_TREND_CONTINUATION,
        "detailed_description": (
            "Trzy metody z luką (Gap Three Methods) to formacja kontynuacji z luką. Po dużej białej "
            "świecy i luce w górę pojawia się czarna świeca, która zamknięciem wypełnia lukę — ale "
            "trend wzrostowy jest kontynuowany. Lustrzane odbicie dla trendu spadkowego. "
            "Wskazuje, że korekta to tylko chwilowa pauza przed kontynuacją ruchu."
        ),
    },
    "CDLADVANCEBLOCK": {
        "name": "Advance Block",
        "description": "Advance Block — weakening bull momentum",
        "indication": "Osłabienie hossy",
        "detailed_description": (
            "Blok postępu (Advance Block) to trzy białe świece podobne do Trzech Białych Żołnierzy, "
            "ale każda kolejna ma mniejsze ciało i/lub dłuższe górne cienie. Sygnalizuje stopniowe "
            "wyczerpywanie się siły byków — kupujący mają coraz trudniej. "
            "Ostrzeżenie o możliwym odwrocie lub korekcie trendu wzrostowego."
        ),
    },
    "CDLSTALLEDPATTERN": {
        "name": "Deliberation",
        "description": "Deliberation / Stalled Pattern — bull momentum pause",
        "indication": "Osłabienie hossy",
        "detailed_description": (
            "Deliberacja (Deliberation, znana też jako Stalled Pattern) to trzy białe świece, "
            "gdzie ostatnia jest wyraźnie mniejsza i otwiera się przy szczycie poprzedniej. "
            "Wskazuje na zmęczenie byków i niepewność co do kontynuacji trendu wzrostowego. "
            "Sygnał ostrzegawczy — nie jest jeszcze potwierdzeniem odwrotu."
        ),
    },
    "CDLDRAGONFLYDOJI": {
        "name": "Dragonfly Doji",
        "description": "Dragonfly Doji — bullish reversal Doji variant",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Doji ważki (Dragonfly Doji) to Doji z bardzo długim dolnym cieniem i bez górnego — "
            "otwarcie, zamknięcie i maximum są praktycznie równe. Po trendzie spadkowym sygnalizuje, "
            "że niedźwiedzie wypchnęły cenę wyraźnie w dół, ale byki całkowicie odreagowały. "
            "Jeden z silniejszych byczych sygnałów odwrotu z rodziny Doji."
        ),
    },
    "CDL2CROWS": {
        "name": "Two Crows",
        "description": "Two Crows — bearish reversal after gap",
        "indication": _INDICATION_BEARISH_REVERSAL,
        "detailed_description": (
            "Dwa kruki (Two Crows) to trójświecowa formacja niedźwiedzia. Po dużej białej świecy "
            "pojawia się czarna z luką w górę, po czym druga czarna świeca otwiera się powyżej "
            "pierwszego kruka i zamyka w ciało białej świecy. Sugeruje, że niedźwiedzie stopniowo "
            "przejmują kontrolę po nieudanej próbie kontynuacji wzrostów."
        ),
    },
    "CDLSTICKSANDWICH": {
        "name": "Stick Sandwich",
        "description": "Stick Sandwich — bullish reversal with matching close",
        "indication": _INDICATION_BULLISH_REVERSAL,
        "detailed_description": (
            "Kanapka (Stick Sandwich) to trójświecowa formacja bycza: czarna świeca, biała świeca "
            "zamykająca się wyżej, czarna świeca zamykająca się na tym samym poziomie co pierwsza. "
            "Dwie czarne świece z tą samą ceną zamknięcia tworzą poziom wsparcia. "
            "Wskazuje na możliwy odwrót — byki bronią poziomu wsparcia."
        ),
    },
}


def _reliability_from_signal(abs_value: int) -> int:
    """Mapuje wartość bezwzględną sygnału TA-Lib na poziom wiarygodności (1-3)."""
    if abs_value >= 200:
        return 3
    if abs_value >= 100:
        return 2
    return 1


def _confidence_from_signal(abs_value: int) -> float:
    """Mapuje wartość bezwzględną sygnału TA-Lib na współczynnik pewności (0.0-1.0)."""
    if abs_value >= 200:
        return 1.0
    if abs_value >= 100:
        return 0.7
    return 0.5


def _directional_indication(indication: str, bullish: bool) -> str:
    """Doprecyzowuje wskazanie obukierunkowej formacji na podstawie kierunku sygnału."""
    if indication == _INDICATION_REVERSAL:
        return _INDICATION_BULLISH_REVERSAL if bullish else _INDICATION_BEARISH_REVERSAL
    if indication == _INDICATION_STRONG_MOMENTUM:
        return _INDICATION_BULLISH_MOMENTUM if bullish else _INDICATION_BEARISH_MOMENTUM
    if indication == _INDICATION_TREND_CONTINUATION:
        return _INDICATION_BULLISH_CONTINUATION if bullish else _INDICATION_BEARISH_CONTINUATION
    return indication


def _description_for_signal(func_name: str, description: str, bullish: bool) -> str:
    """Zwraca opis formacji z uwzględnieniem wyjątków zależnych od kierunku sygnału."""
    if func_name == "CDLENGULFING" and not bullish:
        return "Objęcie bessy (nóż) — strong bearish reversal signal"
    return description


def _detection_from_signal(
    func_name: str,
    meta: dict[str, str],
    idx: int,
    last_idx: int,
    raw_value: int,
) -> PatternDetection:
    """Buduje wynik detekcji świecowej z metadanych i wartości sygnału TA-Lib."""
    bullish = raw_value > 0
    abs_value = abs(raw_value)

    return PatternDetection(
        pattern_type=meta["name"],
        confidence=_confidence_from_signal(abs_value),
        description=_description_for_signal(func_name, meta["description"], bullish),
        location="emerging" if idx == last_idx else "completed",
        bullish=bullish,
        category=PatternCategory.CANDLESTICK,
        detected_at_index=idx,
        indication=_directional_indication(meta["indication"], bullish),
        reliability=_reliability_from_signal(abs_value),
        detailed_description=meta["detailed_description"],
    )


def detect_candlestick_patterns(ohlcv: list[OHLCVData]) -> list[PatternDetection]:
    """Wykrywa formacje świecowe za pomocą funkcji TA-Lib CDL*.

    Skanuje ostatnie _SCAN_CANDLES świec (nie tylko ostatnią).
    Formacja na ostatniej świecy to 'emerging' (wyłaniająca się),
    starsze to 'completed' (wypełnione).
    TA-Lib zwraca: -200/-100 (niedźwiedzia), 0 (brak), +100/+200 (bycza).
    """
    if len(ohlcv) < 5:
        return []

    open_ = np.array([c.open for c in ohlcv], dtype=np.float64)
    high = np.array([c.high for c in ohlcv], dtype=np.float64)
    low = np.array([c.low for c in ohlcv], dtype=np.float64)
    close = np.array([c.close for c in ohlcv], dtype=np.float64)

    n = len(ohlcv)
    last_idx = n - 1
    scan_start = max(0, n - _SCAN_CANDLES)
    results: list[PatternDetection] = []
    seen: set[tuple[str, int]] = set()  # deduplication: (pattern_type, index)

    for func_name, meta in CANDLESTICK_PATTERNS.items():
        func = getattr(talib, func_name)
        signal = func(open_, high, low, close)

        for idx in range(scan_start, n):
            raw_value = int(signal[idx])
            if raw_value == 0:
                continue

            pattern_name = meta["name"]
            key = (pattern_name, idx)
            if key in seen:
                continue
            seen.add(key)

            results.append(_detection_from_signal(func_name, meta, idx, last_idx, raw_value))

    return results
