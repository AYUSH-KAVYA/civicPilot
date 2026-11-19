"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Mic, MicOff } from "lucide-react";

interface SpeechAlternative {
  transcript: string;
}

interface SpeechResult {
  0: SpeechAlternative;
  length: number;
  isFinal: boolean;
}

interface SpeechResultEvent {
  resultIndex: number;
  results: ArrayLike<SpeechResult>;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechResultEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;
type SpeechWindow = Window & {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
};

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  language?: string;
}

export function VoiceInput({ onTranscript, language = "en" }: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const transcriptCallbackRef = useRef(onTranscript);

  useEffect(() => {
    transcriptCallbackRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    const speechWindow = window as SpeechWindow;
    const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
    if (!Recognition) return;

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language === "es" ? "es-ES" : language === "zh" ? "zh-CN" : language === "vi" ? "vi-VN" : language === "tl" ? "fil-PH" : "en-US";
    recognition.onresult = (event) => {
      let transcript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        if (event.results[index].isFinal) transcript += event.results[index][0].transcript;
      }
      if (transcript.trim()) transcriptCallbackRef.current(transcript.trim());
    };
    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;

    return () => {
      recognition.stop();
      recognitionRef.current = null;
    };
  }, [language]);

  const toggleListening = () => {
    const recognition = recognitionRef.current;
    if (!recognition) {
      window.alert("Web Speech API is not supported in this browser. Please type your message.");
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
      return;
    }

    try {
      recognition.start();
      setIsListening(true);
    } catch (error) {
      console.error("Failed to start speech recognition:", error);
      setIsListening(false);
    }
  };

  return (
    <Button
      type="button"
      variant={isListening ? "destructive" : "outline"}
      size="sm"
      onClick={toggleListening}
      className={`gap-1.5 text-xs transition-all ${isListening ? "animate-pulse shadow-md" : ""}`}
      title={isListening ? "Stop voice recording" : "Dictate report via speech"}
      aria-pressed={isListening}
    >
      {isListening ? <><MicOff className="h-3.5 w-3.5" /><span>Listening…</span></> : <><Mic className="h-3.5 w-3.5 text-blue-600" /><span>Voice Input</span></>}
    </Button>
  );
}
