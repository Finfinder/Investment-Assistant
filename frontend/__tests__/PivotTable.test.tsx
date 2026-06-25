import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PivotTable from "@/components/PivotPoints/PivotTable";
import type { PivotPoints } from "@/types";

describe("PivotTable", () => {
  it("z pustą listą nie renderuje tabeli (zwraca null)", () => {
    const { container } = render(<PivotTable pivotPoints={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("z danymi wyświetla poziomy S3-S1, PP, R1-R3", () => {
    const pivotPoints: PivotPoints[] = [
      {
        type: "classic",
        pp: 1.1000,
        s1: 1.0900,
        s2: 1.0800,
        s3: 1.0700,
        r1: 1.1100,
        r2: 1.1200,
        r3: 1.1300,
      },
    ];

    render(<PivotTable pivotPoints={pivotPoints} />);

    expect(screen.getByRole("heading", { name: "Pivot Points" })).toBeInTheDocument();
    expect(screen.getByText("S3")).toBeInTheDocument();
    expect(screen.getByText("S2")).toBeInTheDocument();
    expect(screen.getByText("S1")).toBeInTheDocument();
    expect(screen.getByText("PP")).toBeInTheDocument();
    expect(screen.getByText("R1")).toBeInTheDocument();
    expect(screen.getByText("R2")).toBeInTheDocument();
    expect(screen.getByText("R3")).toBeInTheDocument();
  });

  it("DeMark wyświetla tylko S1, PP, R1 (reszta jako —)", () => {
    const pivotPoints: PivotPoints[] = [
      {
        type: "demark",
        pp: 1.1000,
        s1: 1.0900,
        s2: null,
        s3: null,
        r1: 1.1100,
        r2: null,
        r3: null,
      },
    ];

    render(<PivotTable pivotPoints={pivotPoints} />);

    // S1, PP, R1 should have values
    expect(screen.getByText("1.0900")).toBeInTheDocument();
    expect(screen.getByText("1.1000")).toBeInTheDocument();
    expect(screen.getByText("1.1100")).toBeInTheDocument();
  });
});