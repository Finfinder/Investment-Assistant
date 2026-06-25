import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AnalysisForm from "@/components/AnalysisForm";

describe("AnalysisForm", () => {
  it("renderuje formularz z polami symbol, timeframe, preset", () => {
    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    expect(screen.getByLabelText("Symbol instrumentu")).toBeInTheDocument();
    expect(screen.getByLabelText("Timeframe")).toBeInTheDocument();
    expect(screen.getByLabelText("Preset wskaźników")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analizuj" })).toBeInTheDocument();
  });

  it("walidacja — puste pole symbol pokazuje błąd", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<AnalysisForm onSubmit={handleSubmit} isLoading={false} />);

    const submitButton = screen.getByRole("button", { name: "Analizuj" });
    await user.click(submitButton);

    expect(screen.getByText("Symbol jest wymagany")).toBeInTheDocument();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("walidacja — symbol krótszy niż 2 znaki pokazuje błąd", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<AnalysisForm onSubmit={handleSubmit} isLoading={false} />);

    const symbolInput = screen.getByLabelText("Symbol instrumentu");
    await user.type(symbolInput, "E");
    await user.click(screen.getByRole("button", { name: "Analizuj" }));

    expect(screen.getByText("Symbol musi mieć co najmniej 2 znaki")).toBeInTheDocument();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("zmiana wartości w polu symbol aktualizuje input", async () => {
    const user = userEvent.setup();

    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    const symbolInput = screen.getByLabelText("Symbol instrumentu");
    await user.type(symbolInput, "EURUSD");

    expect(symbolInput).toHaveValue("EURUSD");
  });

  it("wybór timeframe aktualizuje wartość", async () => {
    const user = userEvent.setup();

    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    const timeframeSelect = screen.getByLabelText("Timeframe");
    await user.selectOptions(timeframeSelect, "D1");

    expect(timeframeSelect).toHaveValue("D1");
  });

  it("wybór preset aktualizuje wartość", async () => {
    const user = userEvent.setup();

    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    const presetSelect = screen.getByLabelText("Preset wskaźników");
    await user.selectOptions(presetSelect, "tradingview");

    expect(presetSelect).toHaveValue("tradingview");
  });

  it("submit z poprawnymi danymi wywołuje onSubmit z odpowiednimi argumentami", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn();

    render(<AnalysisForm onSubmit={handleSubmit} isLoading={false} />);

    await user.type(screen.getByLabelText("Symbol instrumentu"), "GOLD");
    await user.selectOptions(screen.getByLabelText("Timeframe"), "H4");
    await user.selectOptions(screen.getByLabelText("Preset wskaźników"), "tradingview");
    await user.click(screen.getByRole("button", { name: "Analizuj" }));

    expect(handleSubmit).toHaveBeenCalledWith("GOLD", "H4", "tradingview");
  });

  it("isLoading=true wyłącza pola i przycisk", () => {
    render(<AnalysisForm onSubmit={() => {}} isLoading={true} />);

    expect(screen.getByLabelText("Symbol instrumentu")).toBeDisabled();
    expect(screen.getByLabelText("Timeframe")).toBeDisabled();
    expect(screen.getByLabelText("Preset wskaźników")).toBeDisabled();
    expect(screen.getByRole("button", { name: /Analizuj/ })).toBeDisabled();
  });

  it("isLoading=true wyświetla spinner i tekst 'Analizuję...'", () => {
    render(<AnalysisForm onSubmit={() => {}} isLoading={true} />);

    expect(screen.getByText("Analizuję...")).toBeInTheDocument();
  });

  it("lista sugestii pojawia się po wpisaniu znaku", async () => {
    const user = userEvent.setup();

    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    const symbolInput = screen.getByLabelText("Symbol instrumentu");
    await user.type(symbolInput, "EU");

    expect(screen.getByText("EURUSD")).toBeInTheDocument();
    expect(screen.getByText("EURGBP")).toBeInTheDocument();
  });

  it("kliknięcie sugestii ustawia symbol i zamyka listę", async () => {
    const user = userEvent.setup();

    render(<AnalysisForm onSubmit={() => {}} isLoading={false} />);

    const symbolInput = screen.getByLabelText("Symbol instrumentu");
    await user.type(symbolInput, "EU");

    const suggestionButton = screen.getByRole("button", { name: "EURUSD" });
    await user.click(suggestionButton);

    expect(symbolInput).toHaveValue("EURUSD");
  });
});