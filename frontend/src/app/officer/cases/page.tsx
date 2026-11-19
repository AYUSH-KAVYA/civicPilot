"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { listCases } from "@/lib/api/endpoints";
import { CaseState, CaseStatus, Urgency } from "@/lib/api/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Filter,
  Search,
  ArrowRight,
  RefreshCw,
  Truck,
  MapPin,
  ShieldAlert,
} from "lucide-react";

export default function OfficerCasesPage() {
  const [cases, setCases] = useState<CaseState[]>([]);
  const [allCases, setAllCases] = useState<CaseState[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [deptFilter, setDeptFilter] = useState("ALL");
  const [urgencyFilter, setUrgencyFilter] = useState("ALL");

  const fetchCases = useCallback(async () => {
    try {
      const [filteredResponse, allResponse] = await Promise.all([
        listCases({
          status: statusFilter,
          department: deptFilter,
          urgency: urgencyFilter,
          search: search.trim() || undefined,
        }),
        listCases(),
      ]);
      setCases(filteredResponse.data.cases);
      setAllCases(allResponse.data.cases);
    } catch (err) {
      console.error("Failed to load cases:", err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, deptFilter, urgencyFilter, search]);

  useEffect(() => {
    // Load external API state on mount and poll for new cases.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchCases();
    // Live update every 3 seconds
    const interval = setInterval(fetchCases, 3000);
    return () => clearInterval(interval);
  }, [fetchCases]);

  // Compute live counters
  const openCount = allCases.filter((c) => c.status !== CaseStatus.CLOSED).length;
  const atRiskCount = allCases.filter((c) => c.status === CaseStatus.AT_RISK).length;
  const needsHumanCount = allCases.filter((c) => c.flags.needs_human || c.status === CaseStatus.NEEDS_HUMAN).length;
  const closedCount = allCases.filter((c) => c.status === CaseStatus.CLOSED).length;

  const getUrgencyBadge = (urgency?: Urgency) => {
    switch (urgency) {
      case Urgency.critical:
        return <Badge className="bg-red-600 hover:bg-red-700 text-white font-bold text-[10px] animate-pulse">CRITICAL</Badge>;
      case Urgency.high:
        return <Badge className="bg-orange-500 hover:bg-orange-600 text-white font-semibold text-[10px]">HIGH</Badge>;
      case Urgency.medium:
        return <Badge className="bg-amber-500 hover:bg-amber-600 text-white font-semibold text-[10px]">MEDIUM</Badge>;
      case Urgency.low:
        return <Badge className="bg-blue-500 hover:bg-blue-600 text-white font-semibold text-[10px]">LOW</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">NORMAL</Badge>;
    }
  };

  const getStatusBadge = (status: CaseStatus) => {
    switch (status) {
      case CaseStatus.IN_PROGRESS:
        return <Badge className="bg-emerald-600 hover:bg-emerald-700 text-white text-[10px]">IN PROGRESS</Badge>;
      case CaseStatus.AT_RISK:
        return <Badge className="bg-amber-600 hover:bg-amber-700 text-white text-[10px]">AT RISK</Badge>;
      case CaseStatus.NEEDS_HUMAN:
        return <Badge className="bg-rose-600 hover:bg-rose-700 text-white text-[10px]">NEEDS HUMAN</Badge>;
      case CaseStatus.AWAITING_CONFIRMATION:
        return <Badge className="bg-teal-600 hover:bg-teal-700 text-white text-[10px]">AWAITING SIGN-OFF</Badge>;
      case CaseStatus.CLOSED:
        return <Badge className="bg-slate-600 hover:bg-slate-700 text-white text-[10px]">CLOSED</Badge>;
      case CaseStatus.REOPENED:
        return <Badge className="bg-red-700 hover:bg-red-800 text-white text-[10px]">REOPENED</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">{status}</Badge>;
    }
  };

  return (
    <div className="container mx-auto max-w-7xl px-4 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white flex items-center gap-2.5">
            <Activity className="h-7 w-7 text-blue-600" />
            <span>Autonomous Grievance Command Center</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Real-time feed of multi-agent execution across municipal departments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchCases()}
            className="text-xs gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5 text-blue-600" />
            <span>Refresh Now</span>
          </Button>

          <Link href="/officer/demo">
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700 text-white text-xs gap-1.5">
              <span>Run Scenarios</span>
              <ArrowRight className="h-3 w-3" />
            </Button>
          </Link>
        </div>
      </div>

      {/* Counters Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border shadow-xs border-blue-100 bg-blue-50/40 dark:bg-blue-950/20">
          <CardHeader className="pb-1 pt-4 px-4">
            <CardDescription className="text-xs font-semibold text-blue-800 dark:text-blue-300">
              Open Grievances
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-blue-950 dark:text-blue-100">
              {openCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 text-[11px] text-muted-foreground">
            Active under autonomous loop
          </CardContent>
        </Card>

        <Card className="border shadow-xs border-amber-200 bg-amber-50/40 dark:bg-amber-950/20">
          <CardHeader className="pb-1 pt-4 px-4">
            <CardDescription className="text-xs font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
              <span>At Risk (SLA Breach)</span>
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-amber-950 dark:text-amber-100">
              {atRiskCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 text-[11px] text-muted-foreground">
            Requires crew reprioritization
          </CardContent>
        </Card>

        <Card className="border shadow-xs border-rose-200 bg-rose-50/40 dark:bg-rose-950/20">
          <CardHeader className="pb-1 pt-4 px-4">
            <CardDescription className="text-xs font-semibold text-rose-800 dark:text-rose-300 flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5 text-rose-600" />
              <span>Needs Human Officer</span>
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-rose-950 dark:text-rose-100">
              {needsHumanCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 text-[11px] text-muted-foreground">
            Low confidence or citizen dispute
          </CardContent>
        </Card>

        <Card className="border shadow-xs border-emerald-100 bg-emerald-50/40 dark:bg-emerald-950/20">
          <CardHeader className="pb-1 pt-4 px-4">
            <CardDescription className="text-xs font-semibold text-emerald-800 dark:text-emerald-300 flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              <span>Verified &amp; Closed</span>
            </CardDescription>
            <CardTitle className="text-3xl font-extrabold text-emerald-950 dark:text-emerald-100">
              {closedCount}
            </CardTitle>
          </CardHeader>
          <CardContent className="px-4 pb-3 text-[11px] text-muted-foreground">
            Closed with vision / citizen proof
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search Bar */}
      <Card className="border shadow-xs">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-3">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by Case ID, address, damage keywords..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 text-xs"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs rounded-md border border-input bg-background px-3 py-2 font-medium"
            >
              <option value="ALL">All Statuses</option>
              <option value="IN_PROGRESS">IN_PROGRESS</option>
              <option value="AT_RISK">AT_RISK</option>
              <option value="NEEDS_HUMAN">NEEDS_HUMAN</option>
              <option value="AWAITING_CONFIRMATION">AWAITING_CONFIRMATION</option>
              <option value="CLOSED">CLOSED</option>
              <option value="REOPENED">REOPENED</option>
            </select>

            {/* Department Filter */}
            <select
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
              className="text-xs rounded-md border border-input bg-background px-3 py-2 font-medium"
            >
              <option value="ALL">All Departments</option>
              <option value="dept-water">Water &amp; Sewerage</option>
              <option value="dept-roads">Roads &amp; Transit</option>
              <option value="dept-sanitation">Sanitation &amp; Waste</option>
              <option value="dept-electricity">Electricity &amp; Power</option>
              <option value="dept-parks">Parks &amp; Rec</option>
              <option value="dept-public-safety">Public Safety / Health</option>
            </select>

            {/* Urgency Filter */}
            <select
              value={urgencyFilter}
              onChange={(e) => setUrgencyFilter(e.target.value)}
              className="text-xs rounded-md border border-input bg-background px-3 py-2 font-medium"
            >
              <option value="ALL">All Urgencies</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Case List Feed */}
      <div className="space-y-3">
        {loading && cases.length === 0 ? (
          <div className="text-center py-12 text-xs text-muted-foreground">
            Loading municipal cases...
          </div>
        ) : cases.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground border rounded-xl bg-white dark:bg-slate-900">
            No grievances match the selected filters.
          </div>
        ) : (
          cases.map((c) => (
            <div
              key={c.id}
              className={`p-4 rounded-xl border bg-white dark:bg-slate-900 shadow-xs hover:border-blue-300 dark:hover:border-blue-700 transition-all flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 ${
                c.id === "1042" ? "border-red-300 bg-red-50/20 dark:bg-red-950/10" : ""
              }`}
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">
                    #{c.id}
                  </span>
                  {getStatusBadge(c.status)}
                  {getUrgencyBadge(c.triage?.urgency)}
                  <Badge variant="outline" className="text-[10px] font-semibold border-slate-300">
                    {c.intake?.category || "General"}
                  </Badge>
                  {c.id === "1042" && (
                    <Badge variant="destructive" className="text-[10px] gap-1 font-mono">
                      <ShieldAlert className="h-3 w-3" />
                      CASE 1042 BENCHMARK
                    </Badge>
                  )}
                  {c.flags.needs_human && (
                    <Badge variant="outline" className="border-rose-300 text-rose-700 bg-rose-50 text-[10px] gap-1 font-semibold">
                      <AlertCircle className="h-3 w-3" />
                      Needs Human Officer
                    </Badge>
                  )}
                </div>

                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  {c.intake?.summary || c.raw.text}
                </div>

                <div className="flex flex-wrap items-center gap-4 text-[11px] text-muted-foreground font-medium">
                  <div className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5 text-blue-600" />
                    <span>{c.intake?.location.address || c.raw.address_text || "San Francisco"}</span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5 text-amber-600" />
                    <span>SLA: {c.triage?.deadline_hours || 4}h &bull; Ward: {c.triage?.ward_id || "ward-5"}</span>
                  </div>

                  {c.tickets && c.tickets.length > 0 && (
                    <div className="flex items-center gap-1 font-mono">
                      <Truck className="h-3.5 w-3.5 text-emerald-600" />
                      <span>{c.tickets[0].id} ({c.tickets[0].crew_id || "assigning"})</span>
                    </div>
                  )}

                  <div className="font-mono text-[10px]">
                    Citizen: {c.citizen.contact_masked} ({c.citizen.language.toUpperCase()})
                  </div>
                </div>
              </div>

              <div className="shrink-0">
                <Link href={`/officer/cases/${c.id}`}>
                  <Button size="sm" className="bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:text-slate-900 text-xs font-semibold gap-1.5 shadow-xs">
                    <span>Inspect Case</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
