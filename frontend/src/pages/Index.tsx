import { useState } from "react";
import InterviewLobby from "@/components/interview/InterviewLobby";
import InterviewRoom from "@/components/interview/InterviewRoom";
import AnalysisPage from "@/components/interview/AnalysisPage";

type InterviewState = "lobby" | "analyzing" | "interview" | "ended";

const Index = () => {
  const [interviewState, setInterviewState] = useState<InterviewState>("lobby");
  const [jobPayload, setJobPayload] = useState<{ companyName: string; jobUrl: string } | null>(null);
  const [debugMode, setDebugMode] = useState(false);
  const [initialResponse, setInitialResponse] = useState<string | null>(null);

  const handleStartInterview = (payload: { companyName: string; jobUrl: string; initialResponse?: string }) => {
    if (payload.companyName === "DEBUG") {
      setDebugMode(true);
      if (payload.initialResponse) setInitialResponse(payload.initialResponse);
      setInterviewState("interview");
    } else {
      setJobPayload(payload);
      setInterviewState("analyzing");
    }
  };

  const handleEndInterview = () => {
    setInterviewState("ended");
  };

  const handleRestartInterview = () => {
    setInterviewState("lobby");
  };

  if (interviewState === "lobby") {
    return <InterviewLobby onStartInterview={handleStartInterview} />;
  }

  if (interviewState === "analyzing" && jobPayload && !debugMode) {
    return (
      <AnalysisPage
        companyName={jobPayload.companyName}
        jobUrl={jobPayload.jobUrl}
        onComplete={(response) => {
          if (response) setInitialResponse(response);
          setInterviewState("interview");
        }}
        onFail={() => setInterviewState("lobby")}
      />
    );
  }

  if (interviewState === "interview") {
    return <InterviewRoom onEndInterview={handleEndInterview} initialResponse={initialResponse} />;
  }

  // Ended state - simple thank you screen
  return (
    <div className="min-h-screen bg-[hsl(var(--interview-surface))] flex flex-col items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 text-center space-y-6 max-w-md">
        <div className="w-20 h-20 mx-auto rounded-full bg-[hsl(var(--interview-success))]/20 flex items-center justify-center">
          <span className="text-4xl">✓</span>
        </div>
        <h1 className="text-3xl font-bold text-foreground">Interview Complete!</h1>
        <p className="text-muted-foreground">
          Thank you for completing your AI technical interview. Your responses have been recorded.
        </p>
        <button
          onClick={handleRestartInterview}
          className="px-8 py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg font-medium transition-colors"
        >
          Start New Interview
        </button>
      </div>
    </div>
  );
};

export default Index;
