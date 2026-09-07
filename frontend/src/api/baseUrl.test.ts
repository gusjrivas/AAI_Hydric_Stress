import { afterEach, describe, expect, it, vi } from "vitest";

describe("API_BASE_URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("defaults to http://localhost:8000 when VITE_API_BASE_URL is not set", async () => {
    vi.resetModules();
    const { API_BASE_URL } = await import("./baseUrl");
    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("uses VITE_API_BASE_URL when it is configured", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://demo.example/api");
    vi.resetModules();
    const { API_BASE_URL } = await import("./baseUrl");
    expect(API_BASE_URL).toBe("https://demo.example/api");
  });
});
