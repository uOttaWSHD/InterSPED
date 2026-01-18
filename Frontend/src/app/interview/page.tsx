"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import InterviewLobby from "@/components/interview/InterviewLobby";
import AnalysisPage from "@/components/interview/AnalysisPage";
import InterviewRoom from "@/components/interview/InterviewRoom";

type ViewState = "lobby" | "analyzing" | "interview";

export default function InterviewPage() {
  const router = useRouter();
  const [view, setView] = useState<ViewState>("lobby");
  const [sessionData, setSessionData] = useState<{
    companyName: string;
    jobUrl: string;
    initialResponse?: string;
    sessionId?: string;
  } | null>(null);

  const handleStartAnalysis = useCallback((data: { companyName: string; jobUrl: string; initialResponse?: string; sessionId?: string }) => {
    setSessionData(data);
    if (data.initialResponse) {
      // Debug mode or pre-loaded response
      setView("interview");
    } else {
      setView("analyzing");
    }
  }, []);

  const handleAnalysisComplete = useCallback((initialResponse?: string, sessionId?: string) => {
    console.log("[InterviewPage] Analysis complete", { initialResponse, sessionId });
    setSessionData((prev) => {
        if (!prev) {
            console.error("[InterviewPage] Session data missing during complete");
            return null;
        }
        return { ...prev, initialResponse, sessionId };
    });
    setView("interview");
  }, []);

  const handleAnalysisFail = useCallback(() => {
    console.warn("[InterviewPage] Analysis failed");
    // Go back to lobby on failure
    setView("lobby");
  }, []);

  const handleEndInterview = useCallback(() => {
    router.push("/dashboard");
  }, [router]);

  if (view === "analyzing" && sessionData) {
    return (
      <AnalysisPage
        companyName={sessionData.companyName}
        jobUrl={sessionData.jobUrl}
        onComplete={handleAnalysisComplete}
        onFail={handleAnalysisFail}
      />
    );
  }

  if (view === "interview") {
    return (
      <InterviewRoom
        onEndInterview={handleEndInterview}
        initialResponse={sessionData?.initialResponse}
        sessionId={sessionData?.sessionId}
      />
    );
  }

  return <InterviewLobby onStartInterview={handleStartAnalysis} />;
}
