import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { formatBytes, truncate } from "@/lib/utils";

describe("utils", () => {
  it("formats byte sizes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1024 * 1024)).toBe("1 MB");
  });

  it("truncates long strings", () => {
    expect(truncate("short")).toBe("short");
    expect(truncate("x".repeat(100), 10)).toHaveLength(13);
    expect(truncate("x".repeat(100), 10).endsWith("...")).toBe(true);
  });
});

describe("Badge", () => {
  it("renders children with default variant", () => {
    render(<Badge>Indexed</Badge>);
    expect(screen.getByText("Indexed")).toBeInTheDocument();
  });

  it("applies the destructive variant class", () => {
    render(<Badge variant="destructive">Failed</Badge>);
    expect(screen.getByText("Failed")).toHaveClass("bg-destructive");
  });
});
