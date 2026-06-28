import { describe, expect, it } from "vitest";
import postcss from "postcss";

/**
 * Test bezpieczeństwa: weryfikuje, że instalowana wersja postcss
 * escapuje sekwencje </style> w stringifikowanym outputcie CSS.
 *
 * CVE: PostCSS XSS via unescaped </style> (postcss < 8.5.10)
 * Issue: #133
 */

describe("PostCSS XSS security", () => {
  it("escapes </style> sequences in stringified CSS output", () => {
    const maliciousCSS =
      'body { content: "</style><script>alert(1)</script><style>"; }';
    const ast = postcss.parse(maliciousCSS);
    const output = ast.toResult().css;

    // Output NIE MOŻE zawierać nieprzepisanej sekwencji </style>
    expect(output).not.toContain("</style>");
    // Output POWINIEN zawierać escaped wersję
    expect(output).toContain("\\3c /style>");
  });

  it("escapes </style> with different casing", () => {
    const maliciousCSS =
      'body { content: "</STYLE><img src=x onerror=alert(1)>"; }';
    const ast = postcss.parse(maliciousCSS);
    const output = ast.toResult().css;

    expect(output).not.toContain("</STYLE>");
    expect(output).not.toContain("</style>");
  });

  it("escapes multiple </style> occurrences", () => {
    const maliciousCSS =
      'a::before { content: "</style>"; } b::after { content: "</style>"; }';
    const ast = postcss.parse(maliciousCSS);
    const output = ast.toResult().css;

    const unescapedCount = (output.match(/<\/style>/gi) || []).length;
    expect(unescapedCount).toBe(0);
  });

  it("does not escape legitimate CSS content", () => {
    const legitimateCSS = "body { color: red; background: blue; }";
    const ast = postcss.parse(legitimateCSS);
    const output = ast.toResult().css;

    expect(output).toContain("color: red");
    expect(output).toContain("background: blue");
  });
});
