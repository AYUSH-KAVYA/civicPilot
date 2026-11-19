"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Paperclip, Send, Camera, Image as ImageIcon, Sparkles, AlertCircle } from "lucide-react";
import { sendCitizenMessage } from "@/lib/api/endpoints";

interface EvidenceUploadProps {
  caseId: string;
  onSubmitted?: () => void;
}

export function EvidenceUpload({ caseId, onSubmitted }: EvidenceUploadProps) {
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() && !file) return;

    setSubmitting(true);
    try {
      await sendCitizenMessage(caseId, {
        text: text.trim() || "Uploaded supplemental verification photo",
        image: file || undefined,
      });
      setText("");
      setFile(null);
      setSuccessMsg("Supplemental evidence received! Adaptation Rule (c) triggered.");
      setTimeout(() => setSuccessMsg(""), 4000);
      onSubmitted?.();
    } catch (err: any) {
      alert("Failed to send message: " + (err.message || "Unknown error"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="border shadow-xs">
      <CardHeader className="pb-3 border-b bg-slate-50/50 dark:bg-slate-900/50">
        <CardTitle className="text-base font-bold flex items-center gap-2">
          <Paperclip className="h-4 w-4 text-blue-600" />
          <span>Add Supplemental Evidence / Message</span>
        </CardTitle>
        <CardDescription className="text-xs">
          Provide additional details, updated photos, or ask the assigned agent for status.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <form onSubmit={handleSubmit} className="space-y-3">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type extra information (e.g. 'Water is now reaching the driveway' or 'Repair crew arrived')..."
            rows={3}
            className="text-xs resize-none"
          />

          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="cursor-pointer flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors border px-2.5 py-1.5 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800">
              <Camera className="h-3.5 w-3.5 text-blue-600" />
              <span>{file ? file.name : "Attach Photo / Video"}</span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </label>

            <Button
              type="submit"
              size="sm"
              disabled={submitting || (!text.trim() && !file)}
              className="bg-blue-600 hover:bg-blue-700 text-white gap-1.5 text-xs font-semibold"
            >
              <Send className="h-3.5 w-3.5" />
              <span>{submitting ? "Sending..." : "Submit to Agent"}</span>
            </Button>
          </div>

          {successMsg && (
            <div className="p-2 rounded bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 text-emerald-800 dark:text-emerald-300 text-xs flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              <span>{successMsg}</span>
            </div>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
