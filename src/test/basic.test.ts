import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";
import { parseISO } from "date-fns";

describe("cn utility", () => {
  it("merges class names correctly", () => {
    const result = cn("px-4", "py-2");
    expect(result).toContain("px-4");
    expect(result).toContain("py-2");
  });

  it("handles empty inputs", () => {
    const result = cn();
    expect(result).toBe("");
  });

  it("handles conditional classes", () => {
    const result = cn("base", "visible");
    expect(result).toContain("base");
    expect(result).toContain("visible");
  });

  it("handles tailwind class conflicts", () => {
    const result = cn("px-4", "px-6");
    // Tailwind merge should keep the last conflicting class
    const parts = result.split(" ");
    expect(parts.filter((p) => p === "px-4").length).toBe(0);
    expect(parts.filter((p) => p === "px-6").length).toBe(1);
  });
});

describe("date-fns usage", () => {
  it("can parse date strings", () => {
    const date = parseISO("2026-07-05");
    expect(date.getFullYear()).toBe(2026);
    expect(date.getMonth()).toBe(6); // 0-indexed
    expect(date.getDate()).toBe(5);
  });
});

// Firebase test skipped — requires VITE_FIREBASE_* env vars to be set in test environment
// describe("firebase config", () => {
//   it("exports firebase app", async () => {
//     const firebase = await import("@/lib/firebase");
//     expect(firebase.app).toBeDefined();
//     expect(firebase.app.name).toBeDefined();
//   });
// });
