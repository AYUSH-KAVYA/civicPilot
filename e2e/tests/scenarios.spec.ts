import { test, expect, type Page } from "@playwright/test";

const useMocks = process.env.E2E_USE_MOCKS !== "false";

async function openOfficer(page: Page, path: string) {
  await page.goto(path);
  if (useMocks) return;

  const password = process.env.E2E_OFFICER_PASSWORD;
  if (!password) throw new Error("Set E2E_OFFICER_PASSWORD to run officer flows against a live API.");
  await page.goto("/officer/login");
  await page.getByPlaceholder(/Enter officer password/i).fill(password);
  await page.getByRole("button", { name: /Sign In to Officer Console/i }).click();
  await expect(page).toHaveURL(/\/officer\/cases/);
  if (path !== "/officer/cases") await page.goto(path);
}

async function getScenarioCaseId(page: Page, index: number): Promise<string> {
  const href = await page.getByRole("link", { name: /Inspect Case #/ }).nth(index).getAttribute("href");
  const caseId = href?.match(/\/officer\/cases\/([^/?]+)/)?.[1];
  if (!caseId) throw new Error("Scenario case link was not returned by the demo page.");
  return caseId;
}

test.describe("CivicPilot Part 4 user journeys", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((mockMode) => {
      if (!mockMode) return;
      const token = "mock_jwt_officer_token_civicpilot_2026";
      localStorage.setItem("civicpilot_use_mocks", "true");
      localStorage.setItem("officer_token", token);
      localStorage.setItem("auth-storage", JSON.stringify({ state: { token, isAuthenticated: true }, version: 0 }));
    }, useMocks);
  });

  test("landing page explains the six-step loop and points to citizen/officer flows", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/CivicPilot/);
    await expect(page.locator("h1")).toContainText("From Citizen Grievance to Verified Resolution");
    for (const phase of ["Perceive", "Reason", "Plan", "Act", "Evaluate", "Adapt"]) {
      await expect(page.getByText(phase, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByRole("link", { name: /Report an Issue/i }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /Officer Live Dashboard/i }).first()).toBeVisible();
  });

  test("Happy Path: citizen submits a report, follows status, and adds evidence", async ({ page }) => {
    await page.goto("/report");
    await page.locator("#incident-description").fill("Water is gushing from a broken pipe near Oak Street and flooding the sidewalk.");
    await page.locator("#citizen-contact").fill("citizen@example.test");
    await page.getByRole("button", { name: /Submit Grievance/i }).click();

    await expect(page.getByText(/Grievance Filed.*Case #/i)).toBeVisible();
    await expect(page.getByText("Live Agent Loop Updates")).toBeVisible();
    await expect(page.getByText(/SSE Stream: MOCK_STREAM/i)).toBeVisible();

    await page.getByPlaceholder(/Type extra information/i).fill("The water is now reaching the curb ramp.");
    await page.getByRole("button", { name: /Submit to Agent/i }).click();
    await expect(page.getByText(/Supplemental evidence received/i)).toBeVisible();

    await page.getByRole("button", { name: /Copy Tracking Link/i }).click();
    await expect(page.getByText(/Link Copied/i)).toBeVisible();
  });

  test("Disruption: rejecting a work ticket appears in the adaptation audit trail", async ({ page }) => {
    await openOfficer(page, "/officer/demo");
    await page.getByRole("button", { name: /Run Disruption/i }).click();
    await expect(page.getByText(/Scenario \[DISRUPTION\] launched successfully/i)).toBeVisible();

    const caseId = await getScenarioCaseId(page, 1);
    const inspectLink = page.getByRole("link", { name: new RegExp(`Inspect Case #${caseId}`) });
    await expect(inspectLink).toHaveAttribute("href", new RegExp(`/officer/cases/${caseId}$`));
    await page.goto(`/officer/cases/${caseId}`);
    await expect(page.getByText("Sandbox In-Flight Disruptions (Live Demo)")).toBeVisible();
    await page.getByRole("button", { name: "Reject Ticket" }).click();
    await expect(page.getByText(/Ticket rejected\. Adaptation Rule \(a\) triggered!/i)).toBeVisible();
    await expect(page.getByText(/ADAPTATION RULE ACTIVE/i).first()).toBeVisible();
  });

  test("Ambiguity: low-confidence case can be reviewed and resolved by an officer", async ({ page }) => {
    await openOfficer(page, "/officer/demo");
    await page.getByRole("button", { name: /Run Ambiguity/i }).click();
    await expect(page.getByText(/Scenario \[AMBIGUITY\] launched successfully/i)).toBeVisible();
    const caseId = await getScenarioCaseId(page, 2);

    await page.goto("/officer/approvals");
    await page.getByRole("tab", { name: /Needs Human Queue/i }).click();
    await expect(page.getByText(`Case #${caseId}`, { exact: false }).first()).toBeVisible();
    await expect(page.getByText(/Reason:/i).first()).toBeVisible();

    await page.getByPlaceholder(/Officer resolution notes/i).fill("Confirmed the location with the citizen and routed the issue to the correct team.");
    await page.getByRole("button", { name: /Resolve & Re-enter Autonomous Loop/i }).click();
    await expect(page.getByText(/resolved and unblocked/i)).toBeVisible();
  });

  test("Case 1042: critical authorization can be inspected and approved", async ({ page }) => {
    await openOfficer(page, "/officer/demo");
    await page.getByRole("button", { name: /Run Case 1042/i }).click();
    await expect(page.getByText(/Scenario \[CASE1042\] launched successfully/i)).toBeVisible();
    const caseId = await getScenarioCaseId(page, 3);

    await page.goto("/officer/approvals");
    await expect(page.getByText(/TIER: CRITICAL/i).first()).toBeVisible();
    await expect(page.getByText(`Case #${caseId}`, { exact: false }).first()).toBeVisible();
    await page.getByRole("button", { name: /Approve & Dispatch/i }).first().click();
    await expect(page.getByText(/APPROVED\. Authorized autonomous agent execution resumed!/i)).toBeVisible();
  });

  test("officer queue has global counters, filters, and case inspection links", async ({ page }) => {
    let query = "1042";
    if (useMocks) {
      await openOfficer(page, "/officer/cases");
    } else {
      await openOfficer(page, "/officer/demo");
      await page.getByRole("button", { name: /Run Case 1042/i }).click();
      await expect(page.getByText(/Scenario \[CASE1042\] launched successfully/i)).toBeVisible();
      query = await getScenarioCaseId(page, 3);
      await page.goto("/officer/cases");
    }
    await expect(page.getByText("Autonomous Grievance Command Center")).toBeVisible();
    for (const counter of ["Open Grievances", "At Risk (SLA Breach)", "Needs Human Officer", "Verified & Closed"]) {
      await expect(page.getByText(counter).first()).toBeVisible();
    }
    await page.getByPlaceholder(/Search by Case ID/i).fill(query);
    await expect(page.getByText(`#${query}`, { exact: true })).toBeVisible();
  });

  test("metrics show six outcomes without fabricated values when data is absent", async ({ page }) => {
    await openOfficer(page, "/officer/metrics");
    await expect(page.getByText("Evaluation & Metrics")).toBeVisible();
    for (const metric of ["Completion Rate", "Routing Accuracy", "Time to First Action", "Time to Resolution", "Escalation Precision", "Human Effort per Case"]) {
      await expect(page.getByText(metric, { exact: true })).toBeVisible();
    }
    await expect(page.getByText(/Test-set size: Not reported/i)).toBeVisible();
    if (useMocks) await expect(page.getByText("No evaluation data available yet.").first()).toBeVisible();
    await page.getByRole("button", { name: /Run evaluation/i }).click();
    await expect(page.getByRole("status").getByText(/Evaluation run .* finished with status/i)).toBeVisible();
  });
});
