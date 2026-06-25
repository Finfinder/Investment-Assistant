import { describe, it, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Section from "@/components/Section";

describe("Section", () => {
  afterEach(() => {
    cleanup();
  });

  it("renderuje tytuł i dzieci domyślnie otwarte", () => {
    render(
      <Section title="Test Section" id="test-section">
        <p>Test content</p>
      </Section>,
    );

    expect(screen.getByRole("heading", { name: "Test Section" })).toBeInTheDocument();
    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("przycisk zwija/rozwija sekcję", async () => {
    const user = userEvent.setup();

    render(
      <Section title="Test Section" id="test-section">
        <p>Test content</p>
      </Section>,
    );

    const button = screen.getByRole("button", { name: /Test Section/ });
    expect(button).toHaveAttribute("aria-expanded", "true");

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Test content")).not.toBeInTheDocument();

    await user.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("defaultOpen=false ukrywa dzieci początkowo", () => {
    render(
      <Section title="Test Section" id="test-section" defaultOpen={false}>
        <p>Test content</p>
      </Section>,
    );

    expect(screen.queryByText("Test content")).not.toBeInTheDocument();
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });

  it("ma poprawne aria-controls", () => {
    render(
      <Section title="Test Section" id="test-section">
        <p>Test content</p>
      </Section>,
    );

    const button = screen.getByRole("button", { name: /Test Section/ });
    expect(button).toHaveAttribute("aria-controls");
  });
});