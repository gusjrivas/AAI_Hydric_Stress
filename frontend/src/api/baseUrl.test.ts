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

describe("PRODUCER_API_BASE_URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("falls back to API_BASE_URL when VITE_PRODUCER_API_BASE_URL is not set (preserves prior behavior)", async () => {
    vi.resetModules();
    const { API_BASE_URL, PRODUCER_API_BASE_URL } = await import("./baseUrl");
    expect(PRODUCER_API_BASE_URL).toBe(API_BASE_URL);
  });

  it("falls back to a configured VITE_API_BASE_URL when VITE_PRODUCER_API_BASE_URL is not set", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8299");
    vi.resetModules();
    const { API_BASE_URL, PRODUCER_API_BASE_URL } = await import("./baseUrl");
    expect(PRODUCER_API_BASE_URL).toBe(API_BASE_URL);
    expect(PRODUCER_API_BASE_URL).toBe("http://127.0.0.1:8299");
  });

  it("uses VITE_PRODUCER_API_BASE_URL when configured, independently of VITE_API_BASE_URL", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8299");
    vi.stubEnv("VITE_PRODUCER_API_BASE_URL", "http://127.0.0.1:8199");
    vi.resetModules();
    const { API_BASE_URL, PRODUCER_API_BASE_URL } = await import("./baseUrl");
    expect(API_BASE_URL).toBe("http://127.0.0.1:8299");
    expect(PRODUCER_API_BASE_URL).toBe("http://127.0.0.1:8199");
    expect(PRODUCER_API_BASE_URL).not.toBe(API_BASE_URL);
  });
});
