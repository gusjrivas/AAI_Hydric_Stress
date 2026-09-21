import { afterEach, describe, expect, it, vi } from "vitest";

describe("DEMO_CONTROL_BASE_URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("is null when VITE_DEMO_CONTROL_BASE_URL is not set (no forced default)", async () => {
    vi.resetModules();
    const { DEMO_CONTROL_BASE_URL } = await import("./demoControlUrl");
    expect(DEMO_CONTROL_BASE_URL).toBeNull();
  });

  it("uses VITE_DEMO_CONTROL_BASE_URL when it is configured", async () => {
    vi.stubEnv("VITE_DEMO_CONTROL_BASE_URL", "http://127.0.0.1:8010");
    vi.resetModules();
    const { DEMO_CONTROL_BASE_URL } = await import("./demoControlUrl");
    expect(DEMO_CONTROL_BASE_URL).toBe("http://127.0.0.1:8010");
  });
});
