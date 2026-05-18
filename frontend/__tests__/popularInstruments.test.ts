import { describe, it, expect } from "vitest";
import { POPULAR_INSTRUMENTS } from "@/components/AnalysisForm";

describe("POPULAR_INSTRUMENTS", () => {
  it("nie zawiera symbolu USOIL", () => {
    expect(POPULAR_INSTRUMENTS).not.toContain("USOIL");
  });

  it("filtrowanie po prefiksie USO nie zwraca żadnych sugestii", () => {
    const usoSuggestions = POPULAR_INSTRUMENTS.filter((s) => s.startsWith("USO"));
    expect(usoSuggestions).toHaveLength(0);
  });

  it("zawiera wspierane przez backend symbole ropy", () => {
    expect(POPULAR_INSTRUMENTS).toContain("OIL");
    expect(POPULAR_INSTRUMENTS).toContain("OILWTI");
  });

  it("sugeruje wspierany indeks FR40 dla prefiksu FR", () => {
    const frSuggestions = POPULAR_INSTRUMENTS.filter((s) => s.startsWith("FR"));

    expect(POPULAR_INSTRUMENTS).toContain("FR40");
    expect(frSuggestions).toContain("FR40");
  });

  it("nie zawiera duplikatów", () => {
    const uniqueSet = new Set(POPULAR_INSTRUMENTS);
    expect(uniqueSet.size).toBe(POPULAR_INSTRUMENTS.length);
  });
});
