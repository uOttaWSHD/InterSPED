"use client";

import { useState } from "react";
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

  const handleStartAnalysis = (data: { companyName: string; jobUrl: string; initialResponse?: string; sessionId?: string }) => {
    setSessionData(data);
    if (data.initialResponse) {
      // Debug mode or pre-loaded response
      setView("interview");
    } else {
      setView("analyzing");
    }
  };

  const handleAnalysisComplete = (initialResponse?: string, sessionId?: string) => {
    setSessionData((prev) => prev ? { ...prev, initialResponse, sessionId } : null);
    setView("interview");
  };

  const handleAnalysisFail = () => {
    // Go back to lobby on failure
    setView("lobby");
  };

  const handleEndInterview = () => {
    router.push("/dashboard");
  };

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
