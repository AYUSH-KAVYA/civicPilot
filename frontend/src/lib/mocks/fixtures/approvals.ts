import { Approval, RiskTier } from "@/lib/api/types";

const ago = (minutes: number) => new Date(Date.now() - minutes * 60000).toISOString();

export const mockApprovals: Approval[] = [
  {
    id: "appr-001",
    case_id: "1042",
    step_id: "s1",
    risk_tier: RiskTier.critical,
    summary: "Emergency 100m perimeter evacuation & high-voltage grid isolate authorization",
    detail: {
      hazard: "Downed 12kV distribution line actively arcing",
      proximity: "50m from Sunset Elementary School playground",
      affected_population_est: 450,
      protocol: "POL-SCHOOL-SAFETY-003",
      required_action: "Authorize immediate police evacuation perimeter and PG&E substation breaker trip",
      recommended_decision: "APPROVE",
      agent_confidence: 0.98,
      agent_rationale: "Life safety hazard within school operational hours requires immediate officer sign-off per city charter rule 4.2.",
    },
    created_at: ago(20),
    status: "pending",
  },
  {
    id: "appr-002",
    case_id: "1002",
    step_id: "s2",
    risk_tier: RiskTier.sensitive,
    summary: "Emergency full lane closure on Mission St (Major Transit Arterial)",
    detail: {
      department: "Roads & Transit",
      traffic_impact: "Muni Bus Route 14 & 49 reroute required",
      duration_est_hours: 6,
      protocol: "POL-TRANSIT-CLOSURE-009",
      recommended_decision: "APPROVE",
      agent_confidence: 0.89,
    },
    created_at: ago(55),
    status: "pending",
  },
];
