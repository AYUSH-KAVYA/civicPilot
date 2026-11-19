"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { CaseEvent } from "@/lib/api/types";
import { getCaseEvents, isMockMode } from "@/lib/api/endpoints";
import { mockStore } from "@/lib/mocks/mockService";

type SSEStatus = "connecting" | "connected" | "polling" | "mock_stream" | "error" | "closed";

export function useSSE(caseId: string | null, accessToken?: string | null) {
  const [events, setEvents] = useState<CaseEvent[]>([]);
  const [status, setStatus] = useState<SSEStatus>("closed");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const visibleEvents = caseId ? events.filter((event) => event.case_id === caseId) : [];

  const fetchEvents = useCallback(async () => {
    if (!caseId) return;
    try {
      const res = await getCaseEvents(caseId, accessToken || undefined);
      if (res.data) {
        setEvents(res.data);
      }
    } catch {
      // silent
    }
  }, [accessToken, caseId]);

  useEffect(() => {
    if (!caseId) {
      return;
    }

    // Load initial audit events asynchronously while establishing the subscription.
    queueMicrotask(() => void fetchEvents());

    // If Mock Mode is active, subscribe to mockStore event updates + mild interval check
    if (isMockMode()) {
      queueMicrotask(() => setStatus("mock_stream"));
      const unsubscribe = mockStore.subscribe(caseId, (newEvent) => {
        setEvents((prev) => {
          if (prev.find((e) => e.id === newEvent.id)) return prev;
          return [...prev, newEvent];
        });
      });

      const interval = setInterval(fetchEvents, 2000);

      return () => {
        unsubscribe();
        clearInterval(interval);
      };
    }

    // Fetch-based SSE supports the contract's Authorization header; EventSource cannot set headers.
    const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
    const token = accessToken || localStorage.getItem("officer_token");
    const controller = new AbortController();
    queueMicrotask(() => setStatus("connecting"));

    const startPolling = () => {
      if (controller.signal.aborted) return;
      setStatus("polling");
      void fetchEvents();
      if (!pollRef.current) pollRef.current = setInterval(fetchEvents, 3000);
    };

    const connect = async () => {
      try {
        const response = await fetch(`${apiBase}/api/cases/${encodeURIComponent(caseId)}/stream`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          signal: controller.signal,
        });
        if (!response.ok || !response.body) throw new Error("Event stream unavailable");

        setStatus("connected");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = "";

        while (!controller.signal.aborted) {
          const { value, done } = await reader.read();
          if (done) break;
          pending += decoder.decode(value, { stream: true });
          const frames = pending.split(/\r?\n\r?\n/);
          pending = frames.pop() || "";
          for (const frame of frames) {
            const data = frame.split(/\r?\n/)
              .filter((line) => line.startsWith("data:"))
              .map((line) => line.slice(5).trim())
              .join("\n");
            if (!data) continue;
            try {
              const event = JSON.parse(data) as CaseEvent;
              setEvents((previous) => previous.some((item) => item.id === event.id) ? previous : [...previous, event]);
            } catch {
              // Ignore keep-alives and malformed SSE frames.
            }
          }
        }
        startPolling();
      } catch {
        startPolling();
      }
    };

    void connect();
    return () => {
      controller.abort();
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [accessToken, caseId, fetchEvents]);

  return { events: visibleEvents, status, refetch: fetchEvents };
}
