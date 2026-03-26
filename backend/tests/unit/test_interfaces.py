from app.modules.data_acquisition.interfaces import DataProvider, DataProviderPriority
from app.modules.data_acquisition.providers.fmp_provider import FMPProvider
from app.modules.data_acquisition.providers.twelve_data_provider import TwelveDataProvider
from app.modules.data_acquisition.providers.yfinance_provider import YFinanceProvider


class TestDataProviderProtocol:
    """Verify that all providers satisfy the DataProvider Protocol."""

    def test_yfinance_is_data_provider(self) -> None:
        provider = YFinanceProvider()
        assert isinstance(provider, DataProvider)

    def test_twelve_data_is_data_provider(self) -> None:
        provider = TwelveDataProvider(api_key="test")
        assert isinstance(provider, DataProvider)

    def test_fmp_is_data_provider(self) -> None:
        provider = FMPProvider(api_key="test")
        assert isinstance(provider, DataProvider)


class TestDataProviderPriority:
    def test_priority_values(self) -> None:
        assert DataProviderPriority.PRIMARY == "primary"
        assert DataProviderPriority.SECONDARY == "secondary"
        assert DataProviderPriority.TERTIARY == "tertiary"
        assert DataProviderPriority.FALLBACK == "fallback"

    def test_provider_priorities(self) -> None:
        yf = YFinanceProvider()
        td = TwelveDataProvider(api_key="test")
        fmp = FMPProvider(api_key="test")
        assert yf.priority == DataProviderPriority.PRIMARY
        assert td.priority == DataProviderPriority.SECONDARY
        assert fmp.priority == DataProviderPriority.TERTIARY
