"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LocationPicker } from "@/components/citizen/LocationPicker";
import { VoiceInput } from "@/components/citizen/VoiceInput";
import { StatusTracker } from "@/components/citizen/StatusTracker";
import { NotificationInbox } from "@/components/citizen/NotificationInbox";
import { EvidenceUpload } from "@/components/citizen/EvidenceUpload";
import { ConfirmClosure } from "@/components/citizen/ConfirmClosure";
import { createCase, getCase } from "@/lib/api/endpoints";
import { useSSE } from "@/lib/hooks/useSSE";
import { CaseState, Phase } from "@/lib/api/types";
import {
  FileText,
  Send,
  Camera,
  Languages,
  ShieldCheck,
  CheckCircle2,
  Sparkles,
  Link as LinkIcon,
  Copy,
  Radio,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

export default function ReportPage() {
  // Form inputs
  const [text, setText] = useState("");
  const [language, setLanguage] = useState("en");
  const [contact, setContact] = useState("");
  const [address, setAddress] = useState("Market St & 4th St, San Francisco");
  const [lat, setLat] = useState(37.7858);
  const [lng, setLng] = useState(-122.4065);
  const [photo, setPhoto] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Active submitted case
  const [activeCase, setActiveCase] = useState<CaseState | null>(null);
  const [accessToken, setAccessToken] = useState<string>("");
  const [copiedLink, setCopiedLink] = useState(false);

  // Live SSE stream for active case
  const { events, status: sseStatus, refetch } = useSSE(activeCase ? activeCase.id : null, accessToken);

  useEffect(() => {
    if (!activeCase?.id || !accessToken) return;
    const refreshCase = async () => {
      try {
        const response = await getCase(activeCase.id, accessToken);
        setActiveCase(response.data);
      } catch {
        // Keep the last known state visible while the stream retries.
      }
    };
    const interval = setInterval(refreshCase, 3000);
    return () => clearInterval(interval);
  }, [activeCase?.id, accessToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) {
      setSubmitError("Please enter a description of the issue.");
      return;
    }
    if (!contact.trim()) {
      setSubmitError("Add a phone number or email so the city can send case updates.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      const fd = new FormData();
      fd.append("text", text);
      fd.append("language", language);
      fd.append("contact", contact.trim());
      fd.append("address_text", address);
      fd.append("lat", lat.toString());
      fd.append("lng", lng.toString());
      fd.append("channel", "web");
      if (photo) fd.append("image", photo);

      const res = await createCase(fd);
      if (res.data) {
        setAccessToken(res.data.access_token);
        // Fetch created case details
        const caseRes = await getCase(res.data.case_id, res.data.access_token);
        setActiveCase(caseRes.data);
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Unable to submit your report. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyLink = () => {
    if (activeCase && typeof window !== "undefined") {
      const url = `${window.location.origin}/track/${activeCase.id}?token=${accessToken}`;
      navigator.clipboard.writeText(url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 3000);
    }
  };

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8 space-y-8">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <FileText className="h-7 w-7 text-blue-600" />
            <span>Citizen Grievance Portal</span>
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            File a public service issue with instant AI intake, automated routing, and real-time resolution updates.
          </p>
        </div>

        {activeCase && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setActiveCase(null)}
            className="text-xs gap-1.5"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>File Another Grievance</span>
          </Button>
        )}
      </div>

      {!activeCase ? (
        /* Report Filing Form */
        <form onSubmit={handleSubmit} className="space-y-6">
          <Card className="border shadow-xs">
            <CardHeader className="pb-4 border-b bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="text-lg font-bold">Describe the Incident</CardTitle>
                  <CardDescription className="text-xs">
                    Explain what happened, any visible danger, or who is impacted.
                  </CardDescription>
                </div>

                <div className="flex items-center gap-2">
                  <Languages className="h-4 w-4 text-muted-foreground" />
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="text-xs rounded-md border border-input bg-background px-2.5 py-1.5 font-medium"
                  >
                    <option value="en">English (US)</option>
                    <option value="es">Español</option>
                    <option value="zh">中文 (Chinese)</option>
                    <option value="vi">Tiếng Việt</option>
                    <option value="tl">Tagalog</option>
                  </select>
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-5 space-y-4">
              {submitError && (
                <div role="alert" className="rounded-lg border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">
                  {submitError}
                </div>
              )}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="incident-description" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Incident Description *
                  </label>
                  <VoiceInput
                    language={language}
                    onTranscript={(voiceText) => setText((prev) => (prev ? `${prev} ${voiceText}` : voiceText))}
                  />
                </div>
                <Textarea
                  id="incident-description"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="e.g. Major water main break near 5th and Market. Water is pouring into the street and flooding the sidewalk near the bus stop..."
                  rows={4}
                  className="text-sm resize-none"
                  required
                />
              </div>

              {/* Media upload + Contact */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <label htmlFor="citizen-contact" className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Attach Incident Photo / Evidence
                  </label>
                  <label className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-blue-500 rounded-xl p-4 flex flex-col items-center justify-center cursor-pointer transition-colors bg-slate-50/50 dark:bg-slate-900/30">
                    <Camera className="h-6 w-6 text-blue-600 mb-1" />
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      {photo ? photo.name : "Click to select a photo"}
                    </span>
                    <span className="text-[10px] text-muted-foreground mt-0.5">
                      JPG, PNG, WebP up to 10MB
                    </span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => setPhoto(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Your Contact (SMS / Email for Updates)
                  </label>
                  <Input
                    id="citizen-contact"
                    type="text"
                    value={contact}
                    onChange={(e) => setContact(e.target.value)}
                    placeholder="+1 (555) 019-2834 or citizen@sf.gov"
                    className="text-sm"
                    required
                    aria-label="Phone number or email for updates"
                  />
                  <div className="mt-2 text-[11px] text-muted-foreground flex items-center gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
                    <span>Protected by automated PII masking in public audit records.</span>
                  </div>
                </div>
              </div>

              {/* Location Picker with Leaflet Map */}
              <div className="pt-3">
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Pinpoint Incident Location (Draggable Pin &amp; Address)
                </label>
                <LocationPicker
                  lat={lat}
                  lng={lng}
                  address={address}
                  onChange={(newLat, newLng, newAddress) => {
                    setLat(newLat);
                    setLng(newLng);
                    setAddress(newAddress);
                  }}
                />
              </div>

              {/* Submit CTA */}
              <div className="pt-4 border-t flex items-center justify-between">
                <div className="text-xs text-muted-foreground font-mono hidden sm:inline">
                  Channel: Web Direct &bull; Contract Section 7
                </div>
                <Button
                  type="submit"
                  disabled={submitting}
                  size="lg"
                  className="bg-blue-600 hover:bg-blue-700 text-white gap-2 font-bold px-8 shadow-sm"
                >
                  <Send className="h-4 w-4" />
                  <span>{submitting ? "Initiating Autonomous Intake..." : "Submit Grievance"}</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </form>
      ) : (
        /* Case Submitted - Live Tracking View */
        <div className="space-y-6">
          {/* Access Token Share Card */}
          <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/70 dark:bg-blue-950/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs">
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <span className="font-bold text-sm text-blue-950 dark:text-blue-100">
                  Grievance Filed &bull; Case #{activeCase.id}
                </span>
                <Badge variant="outline" className="font-mono text-[10px] bg-white dark:bg-black/40">
                  Token: {accessToken.slice(0, 10)}...
                </Badge>
              </div>
              <p className="text-xs text-blue-800 dark:text-blue-300 mt-1">
                Bookmark or copy your secret tracking link to return anytime without logging in.
              </p>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleCopyLink}
              className="gap-1.5 text-xs bg-white dark:bg-slate-900 border-blue-300"
            >
              <Copy className="h-3.5 w-3.5 text-blue-600" />
              <span>{copiedLink ? "Link Copied!" : "Copy Tracking Link"}</span>
            </Button>
          </div>

          {/* Status Tracker */}
          <StatusTracker caseState={activeCase} />

          {/* Live Agent Activity Feed */}
          <Card className="border shadow-xs">
            <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-bold flex items-center gap-2">
                  <Radio className="h-4 w-4 text-emerald-600 animate-pulse" />
                  <span>Live Agent Loop Updates</span>
                </CardTitle>
                <Badge variant="outline" className="text-[10px] font-mono">
                  SSE Stream: {sseStatus.toUpperCase()}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-4 space-y-2.5 max-h-96 overflow-y-auto">
              {events.length === 0 ? (
                <div className="text-xs text-muted-foreground text-center py-6">
                  Listening for agent audit events...
                </div>
              ) : (
                events.map((evt) => (
                  <div
                    key={evt.id}
                    className="p-2.5 rounded-lg border bg-slate-50/60 dark:bg-slate-950/30 text-xs flex items-start justify-between gap-3"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold uppercase text-[10px] font-mono text-blue-600 dark:text-blue-400">
                          [{evt.agent}]
                        </span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {evt.summary}
                        </span>
                      </div>
                      {evt.tool_name && (
                        <div className="text-[10px] font-mono text-muted-foreground">
                          Tool executed: <code className="text-blue-600">{evt.tool_name}</code>
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                      {new Date(evt.ts).toLocaleTimeString()}
                    </span>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Notifications & Evidence in 2 cols */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <NotificationInbox events={events} />
            <EvidenceUpload caseId={activeCase.id} accessToken={accessToken} onSubmitted={refetch} />
          </div>

          {/* Confirm or Dispute Closure */}
          <ConfirmClosure
            caseState={activeCase}
            accessToken={accessToken}
            onUpdated={(updated) => setActiveCase(updated)}
          />
        </div>
      )}
    </div>
  );
}
