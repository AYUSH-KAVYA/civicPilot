"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bell, Mail, MessageSquare, PhoneCall, CheckCheck } from "lucide-react";
import { CaseEvent, Phase } from "@/lib/api/types";

interface NotificationInboxProps {
  events: CaseEvent[];
}

export function NotificationInbox({ events }: NotificationInboxProps) {
  // Filter events where the notify tool was called or a message was emitted to citizen
  const notifications = events.filter(
    (e) =>
      (e.tool_name === "notify" && e.phase === Phase.tool_result) ||
      (e.phase === Phase.message && e.agent === "system") ||
      (e.phase === Phase.message && e.agent === "orchestrator")
  );

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold flex items-center gap-2">
            <Bell className="h-4 w-4 text-blue-600" />
            <span>Citizen Notification Inbox (Sandbox)</span>
          </CardTitle>
          <Badge variant="outline" className="text-[11px] font-mono">
            {notifications.length} Alerts Received
          </Badge>
        </div>
        <CardDescription className="text-xs">
          Simulated SMS and email dispatches delivered directly to citizen contact info via the <code className="text-[10px] font-mono text-blue-600">notify</code> tool.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        {notifications.length === 0 ? (
          <div className="text-center py-6 text-muted-foreground text-xs italic">
            No external notifications dispatched yet. As the agents run, automated alerts will appear here.
          </div>
        ) : (
          notifications.map((n, idx) => (
            <div
              key={n.id || idx}
              className="p-3 rounded-lg border bg-blue-50/40 dark:bg-blue-950/20 border-blue-100 dark:border-blue-900 flex items-start gap-3"
            >
              <div className="mt-0.5 rounded-full p-1.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300">
                <MessageSquare className="h-3.5 w-3.5" />
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                    City Municipal Alert &bull; SMS / Webhook
                  </span>
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {new Date(n.ts).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  {n.summary}
                </p>
                {n.detail && Object.keys(n.detail).length > 0 && (
                  <div className="text-[10px] font-mono bg-white/70 dark:bg-slate-900/70 p-1.5 rounded border border-blue-100 dark:border-blue-900 text-muted-foreground">
                    {JSON.stringify(n.detail)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
