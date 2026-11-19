import { defineConfig, devices } from "@playwright/test";

const useMocks = process.env.E2E_USE_MOCKS !== "false";
const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const frontendEnv = `NEXT_PUBLIC_USE_MOCKS=${useMocks} NEXT_PUBLIC_API_URL=${apiUrl}`;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.PLAYWRIGHT_TEST_BASE_URL
    ? undefined
    : {
        command: `${frontendEnv} npm run build --prefix ../frontend && ${frontendEnv} npm run start --prefix ../frontend`,
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 180000,
      },
});
