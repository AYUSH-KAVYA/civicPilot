"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Eye,
  Brain,
  ListOrdered,
  Zap,
  CheckCircle2,
  RefreshCw,
  Cpu,
  ArrowRight,
  ShieldCheck,
  MapPin,
  Clock,
  Database,
  Layers,
  Sparkles,
  Bot,
  UserCheck,
  AlertTriangle,
  PlayCircle,
  FileCheck,
  BarChart3,
} from "lucide-react";

export default function LandingPage() {
  const loopSteps = [
    {
      phase: "Perceive",
      agent: "Intake Agent",
      icon: Eye,
      color: "border-purple-200 bg-purple-50/70 text-purple-700 dark:bg-purple-950/30 dark:border-purple-800 dark:text-purple-300",
      pill: "bg-purple-600 text-white",
      desc: "Ingests raw citizen reports across Web, Voice, and Chat. Calls parse_media and geo_lookup to extract damage severity, coordinates, and nearby sensitive sites (e.g., schools, hospitals).",
      tool: "parse_media, geo_lookup",
    },
    {
      phase: "Reason",
      agent: "Triage Agent",
      icon: Brain,
      color: "border-blue-200 bg-blue-50/70 text-blue-700 dark:bg-blue-950/30 dark:border-blue-800 dark:text-blue-300",
      pill: "bg-blue-600 text-white",
      desc: "Queries the Municipal Policy Knowledge Base (pgvector) to fetch department SLAs and escalation rules. Computes urgency (Low, Medium, High, Critical) and department routing.",
      tool: "policy_search, similar_cases",
    },
    {
      phase: "Plan",
      agent: "Planner Agent",
      icon: ListOrdered,
      color: "border-indigo-200 bg-indigo-50/70 text-indigo-700 dark:bg-indigo-950/30 dark:border-indigo-800 dark:text-indigo-300",
      pill: "bg-indigo-600 text-white",
      desc: "Synthesizes an executable DAG of plan steps with inter-step dependencies, fallbacks, deadlines, and risk tiers (routine, sensitive, critical).",
      tool: "replan DAG generator",
    },
    {
      phase: "Act",
      agent: "Action Agent",
      icon: Zap,
      color: "border-emerald-200 bg-emerald-50/70 text-emerald-700 dark:bg-emerald-950/30 dark:border-emerald-800 dark:text-emerald-300",
      pill: "bg-emerald-600 text-white",
      desc: "Executes tool calls in topological order. Creates municipal work orders, dispatches the nearest crew via Haversine distance, and broadcasts citizen SMS/email alerts.",
      tool: "ticketing, notify, scheduler",
    },
    {
      phase: "Evaluate",
      agent: "Evaluator Agent",
      icon: CheckCircle2,
      color: "border-amber-200 bg-amber-50/70 text-amber-700 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-300",
      pill: "bg-amber-600 text-white",
      desc: "Continuously tracks live SLA deadlines against SIM_TIME_SCALE. Uses Gemini Vision to inspect uploaded repair photos and asks the citizen to verify resolution.",
      tool: "vision verification, SLA timers",
    },
    {
      phase: "Adapt",
      agent: "Adaptation Engine",
      icon: RefreshCw,
      color: "border-rose-200 bg-rose-50/70 text-rose-700 dark:bg-rose-950/30 dark:border-rose-800 dark:text-rose-300",
      pill: "bg-rose-600 text-white",
      desc: "Applies 5 autonomous recovery rules: ticket rejection re-routing, crew no-show escalation, supplemental evidence integration, spatial duplicate clustering, and citizen dispute reopening.",
      tool: "5 deck adaptation rules",
    },
  ];

  const agents = [
    { name: "Orchestrator", role: "State Persistence & Loop Breaker", desc: "Maintains async execution locks, persists state after each node, emits PII-masked audit events, breaks loops >25 iterations." },
    { name: "Intake Agent", role: "Perception & Geo Extraction", desc: "Extracts damage items, geocodes point-in-polygon ward boundaries, detects language, flags missing data." },
    { name: "Triage Agent", role: "Policy Retrieval & Scoring", desc: "Embeds queries, searches municipal SLA documents, assigns urgency, checks confidence guardrail (threshold >= 0.65)." },
    { name: "Planner Agent", role: "DAG Resolution & Fallbacks", desc: "Constructs dependency-aware execution steps with designated fallbacks and risk classification." },
    { name: "Action Agent", role: "Operational Tool Execution", desc: "Dispatches nearest crews, creates work tickets, sends citizen SMS notifications, triggers scheduled checks." },
    { name: "Evaluator Agent", role: "SLA Monitor & Photo Auditor", desc: "Verifies repairs using vision models, evaluates SLA timeliness, requests citizen confirmation." },
  ];

  return (
    <div className="flex flex-col gap-16 pb-20">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/80 via-white to-background dark:from-slate-900/60 dark:via-slate-950 dark:to-background border-b py-20 px-4 sm:px-6">
        <div className="container mx-auto max-w-5xl text-center flex flex-col items-center">
          <Badge className="mb-4 bg-blue-100 text-blue-800 hover:bg-blue-200 dark:bg-blue-900/50 dark:text-blue-300 px-3 py-1 text-xs uppercase tracking-wider font-semibold border-blue-200">
            CivicPilot Multi-Agent Architecture &bull; Part 4 Scope
          </Badge>

          <h1 className="text-4xl sm:text-6xl font-black tracking-tight text-slate-900 dark:text-white max-w-4xl leading-tight">
            From Citizen Grievance to Verified Resolution.
            <span className="block text-blue-600 dark:text-blue-400 mt-2">
              Autonomous. Audited. Adaptive.
            </span>
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-3xl leading-relaxed">
            CivicPilot replaces slow municipal bureaucracy with an autonomous multi-agent cognitive loop. 
            From intake, geocoding, and policy retrieval to crew dispatch, vision verification, and real-time adaptation.
          </p>

          {/* Action CTAs */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/report">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700 text-white gap-2 shadow-md h-12 px-6 text-base font-semibold">
                <FileCheck className="h-5 w-5" />
                Report an Issue (Citizen)
              </Button>
            </Link>

            <Link href="/officer/cases">
              <Button size="lg" variant="outline" className="gap-2 h-12 px-6 text-base font-semibold border-slate-300 dark:border-slate-700">
                <UserCheck className="h-5 w-5 text-blue-600" />
                Officer Live Dashboard
              </Button>
            </Link>

            <Link href="/officer/demo">
              <Button size="lg" variant="secondary" className="gap-2 h-12 px-6 text-base font-semibold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300">
                <PlayCircle className="h-5 w-5 text-emerald-600" />
                Run Scenarios & Case 1042
              </Button>
            </Link>
          </div>

          {/* Highlights bar */}
          <div className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 w-full max-w-4xl text-left">
            <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border shadow-xs">
              <div className="text-2xl font-bold text-blue-600">0.01 sec</div>
              <div className="text-xs text-muted-foreground mt-1 font-medium">Time to First Action (vs 234 min manual)</div>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border shadow-xs">
              <div className="text-2xl font-bold text-emerald-600">95.0%</div>
              <div className="text-xs text-muted-foreground mt-1 font-medium">Completion Rate (+25% gain)</div>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border shadow-xs">
              <div className="text-2xl font-bold text-purple-600">0.75 hrs</div>
              <div className="text-xs text-muted-foreground mt-1 font-medium">Resolution Time (-96.9% reduction)</div>
            </div>
            <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border shadow-xs">
              <div className="text-2xl font-bold text-amber-600">-90.5%</div>
              <div className="text-xs text-muted-foreground mt-1 font-medium">Human Effort per Case (7.5 min total)</div>
            </div>
          </div>
        </div>
      </section>

      {/* The Six-Step Loop */}
      <section className="container mx-auto px-4 sm:px-6 max-w-6xl">
        <div className="text-center mb-12">
          <Badge variant="outline" className="text-xs font-mono mb-2 uppercase tracking-wider text-blue-700 bg-blue-50 border-blue-200">
            Core Operating System
          </Badge>
          <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            The Six-Step Multi-Agent Cognitive Loop
          </h2>
          <p className="text-muted-foreground mt-2 max-w-2xl mx-auto">
            Every grievance progresses through a rigorous closed-loop lifecycle ensuring complete auditability, guardrail compliance, and adaptive recovery.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loopSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <Card key={step.phase} className={`border-2 transition-all hover:shadow-md ${step.color}`}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full ${step.pill}`}>
                      STEP 0{idx + 1}
                    </span>
                    <Badge variant="outline" className="text-[11px] font-mono bg-white/60 dark:bg-black/30">
                      {step.agent}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl font-bold flex items-center gap-2">
                    <Icon className="h-5 w-5" />
                    <span>{step.phase}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {step.desc}
                  </p>
                  <div className="pt-2 border-t border-current/15 flex items-center justify-between text-xs font-mono">
                    <span className="opacity-75">Tools & Subsystems:</span>
                    <span className="font-semibold">{step.tool}</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Architecture System Overview */}
      <section className="container mx-auto px-4 sm:px-6 max-w-6xl">
        <div className="rounded-2xl border bg-white dark:bg-slate-900 p-8 shadow-sm">
          <div className="flex flex-col lg:flex-row gap-8 items-center justify-between border-b pb-8">
            <div className="max-w-2xl">
              <Badge variant="secondary" className="mb-2 text-xs font-mono uppercase tracking-wider">
                Full-Stack Architecture
              </Badge>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
                One Orchestrator, Five Specialized Agents, Six Tools
              </h3>
              <p className="mt-2 text-muted-foreground">
                Engineered with strict separation of concerns, non-blocking asynchronous DAG execution, and safety guardrails.
              </p>
            </div>
            <div className="flex gap-3">
              <Link href="/officer/metrics">
                <Button variant="outline" className="gap-2">
                  <BarChart3 className="h-4 w-4 text-blue-600" />
                  <span>Slide 12 Scorecard</span>
                </Button>
              </Link>
              <Link href="/officer/cases/1042">
                <Button className="bg-blue-600 hover:bg-blue-700 text-white gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-300" />
                  <span>Inspect Case 1042</span>
                </Button>
              </Link>
            </div>
          </div>

          {/* Subsystems Breakdown */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <div key={agent.name} className="p-4 rounded-xl border bg-slate-50/50 dark:bg-slate-950/40">
                <div className="flex items-center gap-2 font-bold text-slate-900 dark:text-slate-100">
                  <Cpu className="h-4 w-4 text-blue-600" />
                  <span>{agent.name}</span>
                </div>
                <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 mt-1 mb-2">
                  {agent.role}
                </div>
                <p className="text-xs text-muted-foreground leading-normal">
                  {agent.desc}
                </p>
              </div>
            ))}
          </div>

          {/* Tools & Guardrails strip */}
          <div className="mt-8 pt-8 border-t grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <Layers className="h-4 w-4 text-indigo-600" />
                <span>6 Operational Tools</span>
              </div>
              <p className="text-xs text-muted-foreground">
                <code className="text-xs font-mono text-blue-600">parse_media</code>, <code className="text-xs font-mono text-blue-600">geo_lookup</code>, <code className="text-xs font-mono text-blue-600">policy_search</code>, <code className="text-xs font-mono text-blue-600">ticketing</code>, <code className="text-xs font-mono text-blue-600">notify</code>, <code className="text-xs font-mono text-blue-600">scheduler</code>.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                <span>Guardrails & Safety</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Confidence threshold (&ge;0.65), 3 risk tiers (routine, sensitive, critical), prompt injection defense, and automated regex PII masking.
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <Clock className="h-4 w-4 text-amber-600" />
                <span>Simulation Time Scale</span>
              </div>
              <p className="text-xs text-muted-foreground">
                <code className="text-xs font-mono text-blue-600">SIM_TIME_SCALE</code> accelerates multi-hour SLAs into live, observable 2-minute demo cycles.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Launch Scenarios Banner */}
      <section className="container mx-auto px-4 sm:px-6 max-w-6xl">
        <div className="rounded-2xl bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-8 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2 text-xs font-mono text-blue-200 uppercase tracking-widest">
              <Sparkles className="h-4 w-4 text-amber-300" />
              Live Evaluation Ready
            </div>
            <h3 className="text-2xl sm:text-3xl font-black">
              Try the Interactive Demo Scenarios
            </h3>
            <p className="text-sm text-blue-100 max-w-xl">
              Execute Happy Path, Road Disruption, Ambiguity Gate, or the Critical Case 1042 evacuation approval right now in your browser.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link href="/officer/demo">
              <Button size="lg" className="bg-white text-blue-900 hover:bg-blue-50 font-bold gap-2">
                <span>Open Demo Console</span>
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/report">
              <Button size="lg" variant="outline" className="border-white/40 text-white hover:bg-white/10 font-medium">
                Submit Test Report
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
