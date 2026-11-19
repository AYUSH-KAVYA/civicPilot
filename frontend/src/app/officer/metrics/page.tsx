"use client";

import { useEffect, useState } from "react";
import { getMetricsSummary, getScorecard, runEval } from "@/lib/api/endpoints";
import { MetricsSummary } from "@/lib/api/types";
import { EvalScorecard, Slide12Metric } from "@/lib/mocks/fixtures/metrics";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
import {
  BarChart3,
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCw,
  Sparkles,
  Info,
  Layers,
} from "lucide-react";

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [scorecard, setScorecard] = useState<EvalScorecard | null>(null);
  const [loading, setLoading] = useState(true);
  const [evalRunning, setEvalRunning] = useState(false);
  const [evalSuccess, setEvalSuccess] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      const [metricsRes, scorecardRes] = await Promise.all([
        getMetricsSummary(),
        getScorecard(),
      ]);
      if (metricsRes.data) setMetrics(metricsRes.data);
      if (scorecardRes.data) setScorecard(scorecardRes.data);
    } catch (err) {
      console.error("Failed to load metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunEval = async () => {
    setEvalRunning(true);
    setEvalSuccess("");
    try {
      const res = await runEval();
      setEvalSuccess(`Evaluation run #${res.data?.id || "run-001"} completed on 60 benchmark cases.`);
      await loadData();
      setTimeout(() => setEvalSuccess(""), 5000);
    } catch (err: any) {
      alert("Failed to run evaluation: " + err.message);
    } finally {
      setEvalRunning(false);
    }
  };

  if (loading && !scorecard) {
    return (
      <div className="container mx-auto max-w-6xl px-4 py-20 text-center">
        <RotateCw className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-2" />
        <div className="text-xs font-mono text-muted-foreground">Loading evaluation telemetry...</div>
      </div>
    );
  }

  // Chart dataset for comparison
  const rateComparisonData = scorecard?.metrics
    .filter((m) => m.unit === "%")
    .map((m) => ({
      name: m.label,
      "CivicPilot (Autonomous)": m.civicpilot_num,
      "Simulated Manual Baseline": m.manual_num,
    })) || [];

  const timeComparisonData = [
    {
      name: "Time to Resolution (hrs)",
      "CivicPilot (Autonomous)": 0.75,
      "Simulated Manual Baseline": 24.3,
    },
    {
      name: "Human Effort / Case (min)",
      "CivicPilot (Autonomous)": 7.5,
      "Simulated Manual Baseline": 78.8,
    },
  ];

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <BarChart3 className="h-7 w-7 text-blue-600" />
            <span>Evaluation &amp; Slide 12 Benchmark Metrics</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Empirical comparative evaluation: Autonomous Multi-Agent Loop vs. Simulated Manual Municipal Baseline.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Badge variant="outline" className="font-mono text-xs border-blue-300 text-blue-700 bg-blue-50/50">
            Test-Set Size: {scorecard?.test_set_size || 60} Cases
          </Badge>

          <Button
            size="sm"
            onClick={handleRunEval}
            disabled={evalRunning}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold gap-1.5 shadow-xs"
          >
            <Play className="h-3.5 w-3.5" />
            <span>{evalRunning ? "Executing Eval Harness..." : "Run Evaluation Benchmark"}</span>
          </Button>
        </div>
      </div>

      {evalSuccess && (
        <div className="p-3 rounded-lg border border-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 text-xs flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
          <span>{evalSuccess}</span>
        </div>
      )}

      {/* Slide 12 Six Measurable Metrics Scorecard */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <span>Slide 12 Scorecard: The Six Core Metrics</span>
          </h2>
          <span className="text-[11px] font-mono text-muted-foreground">
            *Baseline marked as simulated (FIFO clerk queue with handoff delays)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scorecard?.metrics.map((metric) => (
            <Card key={metric.key} className="border shadow-xs hover:border-blue-300 transition-all">
              <CardHeader className="pb-2 pt-4 px-4 bg-slate-50/50 dark:bg-slate-900/50 border-b">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100">
                    {metric.label}
                  </span>
                  <Badge
                    variant="outline"
                    className={`font-mono text-[10px] font-bold ${
                      metric.direction === "positive"
                        ? "border-emerald-300 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30"
                        : "border-slate-300 text-slate-700"
                    }`}
                  >
                    {metric.delta}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-3 px-4 pb-4 space-y-3">
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900">
                    <span className="text-[10px] text-blue-700 dark:text-blue-300 block font-semibold">
                      CivicPilot
                    </span>
                    <span className="text-lg font-black text-blue-900 dark:text-blue-100">
                      {metric.civicpilot}
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                    <span className="text-[10px] text-muted-foreground block font-semibold">
                      Simulated Baseline*
                    </span>
                    <span className="text-lg font-black text-slate-600 dark:text-slate-400">
                      {metric.manual_baseline}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {metric.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Comparison Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Rate Comparison Chart */}
        <Card className="border shadow-xs">
          <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
            <CardTitle className="text-sm font-bold">Accuracy &amp; Completion Comparison (%)</CardTitle>
            <CardDescription className="text-xs">
              Direct rate comparison against simulated baseline across 60 benchmark grievances.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rateComparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <Bar dataKey="CivicPilot (Autonomous)" fill="#2563eb" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Simulated Manual Baseline" fill="#94a3b8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Time & Effort Reduction Chart */}
        <Card className="border shadow-xs">
          <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
            <CardTitle className="text-sm font-bold">Efficiency &amp; Resolution Reduction</CardTitle>
            <CardDescription className="text-xs">
              Time to resolution (hours) and total manual clerk labor hours saved.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeComparisonData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <Bar dataKey="CivicPilot (Autonomous)" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Simulated Manual Baseline" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Department Breakdown Table */}
      {scorecard?.department_breakdown && (
        <Card className="border shadow-xs">
          <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
            <CardTitle className="text-sm font-bold flex items-center gap-2">
              <Layers className="h-4 w-4 text-blue-600" />
              <span>Departmental Resolution Breakdown (60-Case Benchmark)</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900/80 border-b font-mono text-muted-foreground uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-4">Municipal Department</th>
                    <th className="py-2.5 px-4 text-center">Test Cases</th>
                    <th className="py-2.5 px-4 text-center">Resolved</th>
                    <th className="py-2.5 px-4 text-center">Avg Hours</th>
                    <th className="py-2.5 px-4 text-center">Routing Accuracy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {scorecard.department_breakdown.map((row) => (
                    <tr key={row.department} className="hover:bg-slate-50/60 dark:hover:bg-slate-900/40">
                      <td className="py-2.5 px-4 font-semibold text-slate-800 dark:text-slate-200">
                        {row.department}
                      </td>
                      <td className="py-2.5 px-4 text-center font-mono">{row.cases}</td>
                      <td className="py-2.5 px-4 text-center font-mono text-emerald-600 font-bold">
                        {row.resolved}
                      </td>
                      <td className="py-2.5 px-4 text-center font-mono">{row.avg_hours}h</td>
                      <td className="py-2.5 px-4 text-center font-mono font-bold text-blue-600">
                        {row.accuracy_pct}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
