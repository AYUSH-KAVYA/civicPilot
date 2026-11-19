import { test, expect } from "@playwright/test";

test.describe("CivicPilot Multi-Agent System - End-to-End Scenarios", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to base URL
    await page.goto("/");
  });

  test("Landing Page renders 6-step loop, architecture, and navigation", async ({ page }) => {
    await expect(page).toHaveTitle(/CivicPilot/);
    await expect(page.locator("h1")).toContainText("From Citizen Grievance to Verified Resolution");

    // The six loop steps are visible
    await expect(page.getByText("Perceive")).toBeVisible();
    await expect(page.getByText("Reason")).toBeVisible();
    await expect(page.getByText("Plan")).toBeVisible();
    await expect(page.getByText("Act")).toBeVisible();
    await expect(page.getByText("Evaluate")).toBeVisible();
    await expect(page.getByText("Adapt")).toBeVisible();

    // CTA buttons
    await expect(page.getByRole("link", { name: /Report an Issue/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Officer Live Dashboard/i })).toBeVisible();
  });

  test("Scenario 1: Happy Path - Citizen reports water leak & tracks live resolution", async ({ page }) => {
    // 1. Citizen navigates to /report
    await page.goto("/report");
    await expect(page.locator("h1")).toContainText("Citizen Grievance Portal");

    // 2. Fills in incident report
    const textarea = page.locator("textarea");
    await textarea.fill("Major water main burst near Oak St and 5th Ave. Water is flooding the pedestrian pathway.");

    // 3. Submits report
    await page.getByRole("button", { name: /Submit Grievance/i }).click();

    // 4. Verifies live status tracker appears
    await expect(page.getByText(/Grievance Filed • Case #/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Work Order Dispatched \/ In Progress/i)).toBeVisible();
    await expect(page.getByText(/Live Agent Loop Updates/i)).toBeVisible();

    // 5. Submit supplemental follow-up evidence
    const followUpInput = page.getByPlaceholder(/Type extra information/i);
    await followUpInput.fill("Water flow has started to recede.");
    await page.getByRole("button", { name: /Submit to Agent/i }).click();
    await expect(page.getByText(/Supplemental evidence received/i)).toBeVisible();
  });

  test("Scenario 2: Disruption - Ticket rejected by roads dept triggers Adaptation Rule (a)", async ({ page }) => {
    // 1. Officer opens Case 1002 (Road pothole)
    await page.goto("/officer/cases/1002");
    await expect(page.locator("h1")).toContainText("Mission St near 24th");

    // 2. Click sandbox 'Reject Ticket' button
    const rejectBtn = page.getByRole("button", { name: /Reject Ticket/i }).first();
    await rejectBtn.click();

    // 3. Verifies adaptation rule triggered in audit trail
    await expect(page.getByText(/Ticket rejected\. Adaptation Rule \(a\) triggered!/i)).toBeVisible();
    await expect(page.getByText(/ADAPTATION RULE ACTIVE/i)).toBeVisible();
  });

  test("Scenario 3: Ambiguity - Low confidence halted safely into NEEDS_HUMAN queue", async ({ page }) => {
    // 1. Officer opens Approvals & Needs-Human page
    await page.goto("/officer/approvals");
    await expect(page.locator("h1")).toContainText("Officer Authorization & Review Queue");

    // 2. Switch to Needs Human tab
    await page.getByRole("tab", { name: /Needs Human Queue/i }).click();

    // 3. Case 1003 should be listed with ambiguity reason
    await expect(page.getByText(/Case #1003/i)).toBeVisible();
    await expect(page.getByText(/Reason:/i)).toBeVisible();

    // 4. Officer enters resolution note and unblocks
    const resolveInput = page.locator("input[placeholder*='Officer resolution notes']").first();
    await resolveInput.fill("Clarified location as Richmond Park Playground. Dispatched grounds maintenance.");
    await page.getByRole("button", { name: /Resolve & Re-enter/i }).first().click();

    // 5. Success confirmation
    await expect(page.getByText(/resolved and unblocked/i)).toBeVisible();
  });

  test("Scenario 4: Case 1042 Benchmark - CRITICAL risk tier requires officer authorization", async ({ page }) => {
    // 1. Officer opens approvals page
    await page.goto("/officer/approvals");

    // 2. Pending critical approval for Case 1042 should be displayed
    await expect(page.getByText(/TIER: CRITICAL/i)).toBeVisible();
    await expect(page.getByText(/Emergency 100m perimeter evacuation/i)).toBeVisible();

    // 3. Officer approves action
    const approveBtn = page.getByRole("button", { name: /Approve & Dispatch/i }).first();
    await approveBtn.click();

    // 4. Verify approval success
    await expect(page.getByText(/APPROVED\. Authorized autonomous agent execution resumed!/i)).toBeVisible();

    // 5. Navigate to Case 1042 detail to verify audit trail
    await page.goto("/officer/cases/1042");
    await expect(page.getByText(/CASE 1042/i)).toBeVisible();
    await expect(page.getByText(/Executing authorized critical action/i)).toBeVisible();
  });

  test("Officer Cases Dashboard live queue, counters, and filters work", async ({ page }) => {
    await page.goto("/officer/cases");
    await expect(page.getByText("Autonomous Grievance Command Center")).toBeVisible();

    // Verify counters
    await expect(page.getByText("Open Grievances")).toBeVisible();
    await expect(page.getByText("At Risk (SLA Breach)")).toBeVisible();
    await expect(page.getByText("Needs Human Officer")).toBeVisible();
    await expect(page.getByText("Verified & Closed")).toBeVisible();

    // Verify search filter works
    const searchInput = page.getByPlaceholder(/Search by Case ID/i);
    await searchInput.fill("1042");
    await expect(page.getByText("Case #1042", { exact: false })).toBeVisible();
  });

  test("Slide 12 Metrics scorecard renders 6 core metrics & charts", async ({ page }) => {
    await page.goto("/officer/metrics");
    await expect(page.getByText("Evaluation & Slide 12 Benchmark Metrics")).toBeVisible();

    // Verify test-set size label
    await expect(page.getByText(/Test-Set Size: 60 Cases/i)).toBeVisible();

    // Verify all 6 Slide 12 metrics
    await expect(page.getByText("Completion Rate")).toBeVisible();
    await expect(page.getByText("Routing Accuracy")).toBeVisible();
    await expect(page.getByText("Time to First Action")).toBeVisible();
    await expect(page.getByText("Time to Resolution")).toBeVisible();
    await expect(page.getByText("Escalation Precision")).toBeVisible();
    await expect(page.getByText("Human Effort per Case")).toBeVisible();

    // Verify simulated baseline is explicitly labeled
    await expect(page.getByText(/Simulated Baseline\*/i).first()).toBeVisible();

    // Trigger evaluation benchmark run
    const evalBtn = page.getByRole("button", { name: /Run Evaluation Benchmark/i });
    await evalBtn.click();
    await expect(page.getByText(/Evaluation run #.* completed on 60 benchmark cases/i)).toBeVisible();
  });
});
