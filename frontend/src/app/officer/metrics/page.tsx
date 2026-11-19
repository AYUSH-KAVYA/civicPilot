"use client";

import { useCallback, useEffect, useState } from "react";
import { getMetricsSummary, runEval } from "@/lib/api/endpoints";
import type { MetricsSummary } from "@/lib/api/types";
import type { EvalRun } from "@/lib/api/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { BarChart3, CheckCircle2, CircleHelp, Play, RotateCw } from "lucide-react";

type MetricCard = {
  key: string;
  label: string;
  description: string;
  unit: "%" | "hours" | "minutes";
  civicpilot: number | null;
  baseline: number | null;
};

function formatValue(value: number | null, unit: MetricCard["unit"]): string {
  if (value === null || !Number.isFinite(value)) return "—";
  if (unit === "%") return `${(value * 100).toFixed(1)}%`;
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} ${unit}`;
}

function evaluationValue(results: EvalRun["results"], key: string): number | null {
  if (!Array.isArray(results)) return null;
  const result = results.find((item) => item.metric === key);
  return typeof result?.score === "number" ? result.score : null;
}

function buildMetrics(summary: MetricsSummary | null, results?: EvalRun["results"]): MetricCard[] {
  const closedCases = summary?.cases_by_status.CLOSED ?? 0;
  const completionRate = summary && summary.total_cases > 0 ? closedCases / summary.total_cases : null;
  return [
    {
      key: "completion_rate",
      label: "Completion Rate",
      description: "Share of cases resolved; derived from the summary resolution rate.",
      unit: "%",
      civicpilot: evaluationValue(results, "completion_rate") ?? completionRate,
      baseline: evaluationValue(results, "manual_baseline_completion_rate"),
    },
    {
      key: "routing_accuracy",
      label: "Routing Accuracy",
      description: "Correct department assignment. The contract summary does not report this value.",
      unit: "%",
      civicpilot: evaluationValue(results, "routing_accuracy"),
      baseline: evaluationValue(results, "manual_baseline_routing_accuracy"),
    },
    {
      key: "time_to_first_action",
      label: "Time to First Action",
      description: "Elapsed time from report receipt to the first dispatched action.",
      unit: "minutes",
      civicpilot: evaluationValue(results, "time_to_first_action") ?? (summary ? summary.avg_time_to_first_action_sec / 60 : null),
      baseline: evaluationValue(results, "manual_baseline_time_to_first_action"),
    },
    {
      key: "time_to_resolution",
      label: "Time to Resolution",
      description: "Average resolution duration reported by the metrics summary.",
      unit: "hours",
      civicpilot: evaluationValue(results, "time_to_resolution"),
      baseline: evaluationValue(results, "manual_baseline_time_to_resolution"),
    },
    {
      key: "escalation_precision",
      label: "Escalation Precision",
      description: "Precision of human escalations. An escalation rate is not a precision measure.",
      unit: "%",
      civicpilot: evaluationValue(results, "escalation_precision"),
      baseline: evaluationValue(results, "manual_baseline_escalation_precision"),
    },
    {
      key: "human_effort_per_case",
      label: "Human Effort per Case",
      description: "Hands-on officer time per case; not present in the contract summary response.",
      unit: "minutes",
      civicpilot: evaluationValue(results, "human_effort_per_case"),
      baseline: evaluationValue(results, "manual_baseline_human_effort_per_case"),
    },
  ];
}

export default function MetricsPage() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [evalRunning, setEvalRunning] = useState(false);
  const [evalResults, setEvalResults] = useState<EvalRun["results"]>();
  const [testSetSize, setTestSetSize] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setError("");
    try {
      const response = await getMetricsSummary();
      setSummary(response.data);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load evaluation metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load backend-reported metrics on mount.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadData();
  }, [loadData]);

  const metrics = buildMetrics(summary, evalResults);
  const chartData = metrics
    .filter((metric) => metric.civicpilot !== null || metric.baseline !== null)
    .map((metric) => ({
      name: metric.label,
      CivicPilot: metric.civicpilot === null ? undefined : metric.unit === "%" ? metric.civicpilot * 100 : metric.civicpilot,
      "Simulated Manual Baseline": metric.baseline === null ? undefined : metric.unit === "%" ? metric.baseline * 100 : metric.baseline,
    }));

  const handleRunEval = async () => {
    setEvalRunning(true);
    setMessage("");
    setError("");
    try {
      const response = await runEval();
      setEvalResults(response.data.results);
      if (Array.isArray(response.data.results)) {
        const sizes = response.data.results.flatMap((item) => {
          const tested = item.details?.tested ?? item.details?.total;
          return typeof tested === "number" ? [tested] : [];
        });
        if (sizes.length) setTestSetSize(Math.max(...sizes));
      }
      setMessage(`Evaluation run ${response.data.id} finished with status: ${response.data.status}.`);
      await loadData();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Unable to run the evaluation.");
    } finally {
      setEvalRunning(false);
    }
  };

  return (
    <div className="container mx-auto max-w-6xl space-y-6 px-4 py-8">
      <header className="flex flex-col items-start justify-between gap-4 border-b pb-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="flex items-center gap-2.5 text-2xl font-black tracking-tight sm:text-3xl">
            <BarChart3 className="h-7 w-7 text-blue-600" /> Evaluation &amp; Metrics
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Reported metrics only. Manual baseline values are simulated and clearly identified.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className="font-mono">
            Test-set size: {testSetSize ? `${testSetSize} cases` : "Not reported"}
          </Badge>
          <Button onClick={handleRunEval} disabled={evalRunning}>
            {evalRunning ? <RotateCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
            {evalRunning ? "Running evaluation…" : "Run evaluation"}
          </Button>
        </div>
      </header>

      {error && <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      {message && <div role="status" className="flex items-center gap-2 rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 className="h-4 w-4" />{message}</div>}

      <section aria-labelledby="metrics-heading" className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="metrics-heading" className="text-lg font-bold">Six measurable outcomes</h2>
          <span className="text-xs text-muted-foreground">Baseline: simulated manual process</span>
        </div>
        {loading ? (
          <div className="py-12 text-center text-sm text-muted-foreground" role="status">Loading metrics…</div>
        ) : (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {metrics.map((metric) => {
              const hasData = metric.civicpilot !== null || metric.baseline !== null;
              return (
                <Card key={metric.key}>
                  <CardHeader className="border-b bg-slate-50/60 pb-3 dark:bg-slate-900/50">
                    <CardTitle className="text-sm">{metric.label}</CardTitle>
                    <CardDescription className="text-xs">{metric.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-3 pt-4 text-center">
                    <div className="rounded-lg border border-blue-100 bg-blue-50 p-3 dark:bg-blue-950/30">
                      <span className="block text-xs font-semibold text-blue-700 dark:text-blue-300">CivicPilot</span>
                      <span className="mt-1 block text-lg font-bold">{formatValue(metric.civicpilot, metric.unit)}</span>
                    </div>
                    <div className="rounded-lg border bg-slate-100 p-3 dark:bg-slate-800">
                      <span className="block text-xs font-semibold text-muted-foreground">Simulated baseline</span>
                      <span className="mt-1 block text-lg font-bold">{formatValue(metric.baseline, metric.unit)}</span>
                    </div>
                    {!hasData && <p className="col-span-2 flex items-center justify-center gap-1 text-xs text-muted-foreground"><CircleHelp className="h-3.5 w-3.5" />No evaluation data available yet.</p>}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </section>

      <Card>
        <CardHeader className="border-b bg-slate-50/60 dark:bg-slate-900/50">
          <CardTitle className="text-sm">Available comparison data</CardTitle>
          <CardDescription className="text-xs">Values are read from GET /api/metrics/summary and evaluation results; unsupported measures are intentionally left empty.</CardDescription>
        </CardHeader>
        <CardContent className="h-72 pt-5">
          {chartData.length ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 12, left: 4, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="CivicPilot" fill="#2563eb" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Simulated Manual Baseline" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
              <CircleHelp className="h-6 w-6" />
              <p>No metrics have been reported. Run an evaluation after the backend has a test set.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
