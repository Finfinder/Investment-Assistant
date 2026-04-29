from dataclasses import dataclass
from enum import StrEnum

from app.core.models import Timeframe


class DataTimeframe(StrEnum):
    M15 = "M15"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"

    @classmethod
    def from_public(cls, timeframe: Timeframe) -> "DataTimeframe":
        return cls(timeframe.value)

    def to_public(self) -> Timeframe | None:
        if self == DataTimeframe.W1:
            return None
        return Timeframe(self.value)


TimeframeLike = Timeframe | DataTimeframe


def normalize_data_timeframe(timeframe: TimeframeLike) -> DataTimeframe:
    if isinstance(timeframe, DataTimeframe):
        return timeframe
    return DataTimeframe.from_public(timeframe)


SCANNER_DATA_TIMEFRAMES: tuple[DataTimeframe, ...] = (
    DataTimeframe.D1,
    DataTimeframe.H1,
    DataTimeframe.M15,
)


@dataclass(frozen=True, slots=True)
class AnalysisTimeframePlan:
    main_timeframe: DataTimeframe
    pivot_points_timeframe: DataTimeframe = DataTimeframe.D1
    long_term_trend_timeframe: DataTimeframe = DataTimeframe.W1
    pattern_scanner_timeframes: tuple[DataTimeframe, ...] = SCANNER_DATA_TIMEFRAMES

    @property
    def required_timeframes(self) -> tuple[DataTimeframe, ...]:
        seen: set[DataTimeframe] = set()
        ordered: list[DataTimeframe] = []

        for timeframe in (
            self.main_timeframe,
            self.pivot_points_timeframe,
            self.long_term_trend_timeframe,
            *self.pattern_scanner_timeframes,
        ):
            if timeframe not in seen:
                seen.add(timeframe)
                ordered.append(timeframe)

        return tuple(ordered)


def resolve_analysis_timeframes(public_timeframe: Timeframe) -> AnalysisTimeframePlan:
    return AnalysisTimeframePlan(main_timeframe=DataTimeframe.from_public(public_timeframe))
