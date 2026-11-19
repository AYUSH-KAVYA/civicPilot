# CivicPilot Demo Script

- **Audience:** hackathon judges and civic-service stakeholders
- **Runtime:** about 8–10 minutes for the three core scenarios, plus the Case 1042 critical-approval showcase
- **Start at:** `/officer/demo`; keep `/report` available in a second tab. Follow the REST/SSE behavior in [CONTRACT.md](CONTRACT.md), and use the case IDs returned by the demo API rather than assuming fixed live IDs.

## Before the demo

- Start the frontend in mock mode or point `NEXT_PUBLIC_API_URL` at a running backend with `NEXT_PUBLIC_USE_MOCKS=false`.
- Log in at `/officer/login`. Mock mode offers a one-click demo login; live mode uses the configured officer password.
- Open `/officer/demo` and `/officer/cases` in separate tabs.
- For live deadlines, configure backend `SIM_TIME_SCALE` before startup. The UI shows that this scale is backend-configured because the contract exposes no simulated-clock read endpoint.
- In mock mode, preloaded cases 1001, 1002, 1003, and 1042 make the scenario dashboards immediately inspectable. Live scenario runs create fresh cases and show the returned ID/link.

## Scenario 1 — Happy Path: citizen report to verified closure

**Point:** a citizen can file, follow the agent activity, add evidence, and confirm the result.

| Time | Presenter action | What to highlight |
|---|---|---|
| 0:00 | In `/report`, describe a water leak, enter a phone/email for updates, choose a language, and adjust the address or map pin. Optionally attach a photo. Submit. | Intake fields, location and language are sent through `POST /api/cases`; the response creates a private tracking link with the case access token. |
| 0:45 | Keep the citizen page open while the case appears. | Status tracker, live event stream, and notification inbox. If SSE is unavailable, the UI reports polling fallback and continues refreshing events/state. |
| 1:30 | Open the officer queue and inspect the new case. | Department/status/urgency badges and the global queue counters. Filters only change the visible list. |
| 2:15 | Open the case detail. Expand a tool-call event and inspect the plan. | Phase-colored audit events, JSON detail, dependencies, step statuses, actual reported confidence and policy references. Missing backend fields are shown as unavailable. |
| 3:00 | Return to the citizen tab and send a short update or evidence photo. | The follow-up is authenticated with the case token; the audit trail records the citizen update. |
| 3:45 | On the officer detail page, use available sandbox actions for the selected ticket if desired. | The event timeline updates and adaptation reasons appear when the backend emits them. |
| 4:30 | Return to `/track/[id]?token=…`. Confirm or dispute only when the case is awaiting citizen confirmation. | Confirmation calls the contract endpoint; dispute/reopen state is shown when returned by the backend. |

**Narration:** “The citizen keeps a private tracking link. The officer sees the same case through an audited view, and each action stays visible instead of disappearing into an opaque handoff.”

## Scenario 2 — Disruption: rejected work ticket

**Point:** a field signal can trigger adaptation and a plan change.

| Time | Presenter action | What to highlight |
|---|---|---|
| 0:00 | In `/officer/demo`, click **Run Disruption**. | The response provides a case ID; use **Inspect Case** on that scenario card. |
| 0:30 | Inspect its current status, plan, tickets, and event timeline. | Establish the initial road case context and the work-order ID returned by the API. |
| 1:00 | Use **Reject Ticket** on the case detail, or choose that ticket in the demo sandbox selector and reject it. | `POST /api/sandbox/tickets/{id}/reject`; the timeline should show the signal and any adaptation/replan events emitted by the backend. |
| 2:00 | Refresh/observe the case detail. | Compare the returned plan version, ticket state, status, and adaptation reason. Do not narrate a successful re-route unless it appears in the live audit data. |
| 3:00 | If a replacement work order is available, use crew check-in or repair-photo sandbox action. | The tools are tied to the selected ticket; unavailable tickets leave the controls disabled. |

**Narration:** “The important behavior is not that every disruption disappears instantly; it is that the system records the failure, evaluates the new context, and exposes the decision for inspection.”

## Scenario 3 — Ambiguity: confidence guardrail and human review

**Point:** low-confidence cases pause for a human rather than silently making a risky guess.

| Time | Presenter action | What to highlight |
|---|---|---|
| 0:00 | Click **Run Ambiguity** in `/officer/demo`, then inspect its returned case. | The scenario is intentionally underspecified; use the live case ID shown by the UI. |
| 0:45 | Review the timeline and confidence panel. | If reported confidence is below the configured threshold, the guardrail and needs-human reason should be visible. The frontend shows “Not reported” rather than inventing a score. |
| 1:30 | Open `/officer/approvals`, then the **Needs Human Queue** tab. | Read the agent rationale and missing-information context; open the full case timeline if needed. |
| 2:15 | Add an officer note and choose **Resolve & Re-enter Autonomous Loop**. | `POST /api/cases/{id}/resolve` records officer resolution; the page refreshes the case from the API. |
| 3:00 | Return to the case detail. | Confirm the latest state/event emitted by the backend before describing resumed processing. |

**Narration:** “Escalation is a safety outcome, not a model failure. The system makes uncertainty and its reason inspectable, and leaves the decision with an officer.”

## Optional showcase — Case 1042 critical approval

1. Click **Run Case 1042** and open the returned case ID.
2. Inspect risk-tier details and the pending approval packet in `/officer/approvals`.
3. Read the actual rationale and policy references; do not imply an approval exists unless the API returns one.
4. Approve or reject with an officer note and verify the resulting case events.

This path demonstrates explicit human authorization for a critical action. It is separate from the three core scenario tests.

## Wrap-up

Open `/officer/metrics` last. The page labels manual baseline values as simulated and leaves unsupported results empty. The current backend contract does not provide all six requested metric values; do not present placeholders as measured outcomes. The run button uses `POST /api/eval/run` and reports the response status/test-set count only when the API returns it.
