import { useState, useEffect } from "react";
import InterviewLobby from "@/components/interview/InterviewLobby";
import InterviewRoom, { VitalsData } from "@/components/interview/InterviewRoom";
import AnalysisPage from "@/components/interview/AnalysisPage";
import { Heart, Wind, Loader2, Activity, Brain } from "lucide-react";

type InterviewState = "lobby" | "analyzing" | "interview" | "processing" | "ended";

// Vitals Processing Component
const VitalsProcessingPage = ({ 
  videoBlob, 
  onComplete, 
  onError 
}: { 
  videoBlob: Blob; 
  onComplete: (vitals: VitalsData) => void; 
  onError: () => void;
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const steps = [
    { icon: Activity, label: "Uploading interview recording", color: "text-blue-500" },
    { icon: Heart, label: "Analyzing heart rate patterns", color: "text-rose-500" },
    { icon: Wind, label: "Measuring breathing patterns", color: "text-cyan-500" },
    { icon: Brain, label: "Generating vitals report", color: "text-purple-500" },
  ];

  useEffect(() => {
    let isMounted = true;

    const processVitals = async () => {
      try {
        // Step 1: Upload
        setCurrentStep(0);
        const formData = new FormData();
        formData.append("file", videoBlob, "interview.mp4");
        
        const response = await fetch("http://localhost:8000/api/upload", { 
          method: "POST", 
          body: formData 
        });

        if (!isMounted) return;

        // Simulate step progression for better UX
        setCurrentStep(1);
        await new Promise(r => setTimeout(r, 800));
        if (!isMounted) return;
        
        setCurrentStep(2);
        await new Promise(r => setTimeout(r, 800));
        if (!isMounted) return;
        
        setCurrentStep(3);
        await new Promise(r => setTimeout(r, 600));
        if (!isMounted) return;

        if (!response.ok) {
          throw new Error("Failed to process video");
        }

        const vitalsData = await response.json();
        console.log("Vitals data received:", vitalsData);

        if (isMounted) {
          onComplete(vitalsData);
        }
      } catch (err) {
        console.error("Vitals processing error:", err);
        if (isMounted) {
          setError("Failed to analyze vitals. Please try again.");
          setTimeout(() => onError(), 2000);
        }
      }
    };

    processVitals();
    return () => { isMounted = false; };
  }, [videoBlob, onComplete, onError]);

  return (
    <div className="min-h-screen bg-[hsl(var(--interview-surface))] flex flex-col items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl animate-pulse" />
      </div>

      <div className="relative z-10 max-w-xl w-full space-y-8">
        <div className="text-center space-y-3">
          <div className="w-20 h-20 mx-auto rounded-full bg-primary/20 flex items-center justify-center">
            <Activity className="w-10 h-10 text-primary animate-pulse" />
          </div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Analyzing Your Vitals</h1>
          <p className="text-muted-foreground">Processing your interview recording to extract health metrics</p>
        </div>

        <div className="bg-[hsl(var(--interview-elevated))] rounded-xl p-6 border border-border">
          <ul className="space-y-4">
            {steps.map((step, index) => {
              const Icon = step.icon;
              const isComplete = index < currentStep;
              const isActive = index === currentStep;
              const isPending = index > currentStep;

              return (
                <li key={index} className="flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
                    isComplete ? "bg-[hsl(var(--interview-success))]/20" :
                    isActive ? "bg-primary/20" : "bg-muted/20"
                  }`}>
                    {isComplete ? (
                      <span className="text-[hsl(var(--interview-success))] text-lg">✓</span>
                    ) : isActive ? (
                      <Loader2 className={`w-5 h-5 ${step.color} animate-spin`} />
                    ) : (
                      <Icon className={`w-5 h-5 text-muted-foreground/40`} />
                    )}
                  </div>
                  <div className="flex-1">
                    <span className={`text-sm transition-colors ${
                      isComplete ? "text-[hsl(var(--interview-success))]" :
                      isActive ? "text-foreground font-medium" : "text-muted-foreground/60"
                    }`}>
                      {step.label}
                    </span>
                  </div>
                  <div className="w-24 h-2 bg-[hsl(var(--interview-surface))] rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-500 ${
                        isComplete ? "bg-[hsl(var(--interview-success))] w-full" :
                        isActive ? "bg-primary animate-pulse w-3/4" : "bg-muted/30 w-0"
                      }`} 
                    />
                  </div>
                </li>
              );
            })}
          </ul>

          {error && (
            <div className="mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>

        <p className="text-center text-xs text-muted-foreground">
          This may take a moment depending on video length
        </p>
      </div>
    </div>
  );
};

const Index = () => {
  const [interviewState, setInterviewState] = useState<InterviewState>("lobby");
  const [jobPayload, setJobPayload] = useState<{ companyName: string; jobUrl: string } | null>(null);
  const [debugMode, setDebugMode] = useState(false);
  const [initialResponse, setInitialResponse] = useState<string | null>(null);
  const [vitalsData, setVitalsData] = useState<VitalsData | null>(null);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);

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

  const handleEndInterview = (blob?: Blob) => {
    if (blob) {
      setVideoBlob(blob);
      setInterviewState("processing");
    } else {
      // No video recorded, skip to ended
      setInterviewState("ended");
    }
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

  if (interviewState === "processing" && videoBlob) {
    return (
      <VitalsProcessingPage
        videoBlob={videoBlob}
        onComplete={(vitals) => {
          setVitalsData(vitals);
          setVideoBlob(null);
          setInterviewState("ended");
        }}
        onError={() => {
          setVideoBlob(null);
          setInterviewState("ended");
        }}
      />
    );
  }

  // Calculate average vitals (excluding null values)
  const calculateAverage = (values: (number | null)[]): number | null => {
    const validValues = values.filter((v): v is number => v !== null);
    if (validValues.length === 0) return null;
    return validValues.reduce((sum, v) => sum + v, 0) / validValues.length;
  };

  const avgPulse = vitalsData ? calculateAverage(vitalsData.pulse) : null;
  const avgBreathing = vitalsData ? calculateAverage(vitalsData.breathing) : null;

  // Ended state - thank you screen with vitals
  return (
    <div className="min-h-screen bg-[hsl(var(--interview-surface))] flex flex-col items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 text-center space-y-8 max-w-2xl w-full">
        <div className="w-20 h-20 mx-auto rounded-full bg-[hsl(var(--interview-success))]/20 flex items-center justify-center">
          <span className="text-4xl">✓</span>
        </div>
        <h1 className="text-3xl font-bold text-foreground">Interview Complete!</h1>
        <p className="text-muted-foreground">
          Thank you for completing your AI technical interview. Your responses have been recorded.
        </p>

        {/* Vitals Display */}
        {vitalsData && (avgPulse !== null || avgBreathing !== null) && (
          <div className="mt-8">
            <h2 className="text-xl font-semibold text-foreground mb-4">Your Interview Vitals</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Pulse Card */}
              <div className="relative overflow-hidden bg-gradient-to-br from-rose-500/10 via-red-500/5 to-pink-500/10 rounded-2xl p-6 border border-rose-500/20 backdrop-blur-sm">
                <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full blur-2xl -mr-16 -mt-16" />
                <div className="relative">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-full bg-rose-500/20 flex items-center justify-center">
                      <Heart className="w-6 h-6 text-rose-500" />
                    </div>
                    <span className="text-sm font-medium text-rose-400 uppercase tracking-wide">Heart Rate</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold text-foreground">
                      {avgPulse !== null ? Math.round(avgPulse) : "--"}
                    </span>
                    <span className="text-lg text-muted-foreground">BPM</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {avgPulse !== null && avgPulse < 100 ? "Normal range" : avgPulse !== null ? "Slightly elevated" : "No data"}
                  </p>
                </div>
              </div>

              {/* Breathing Card */}
              <div className="relative overflow-hidden bg-gradient-to-br from-cyan-500/10 via-blue-500/5 to-teal-500/10 rounded-2xl p-6 border border-cyan-500/20 backdrop-blur-sm">
                <div className="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full blur-2xl -mr-16 -mt-16" />
                <div className="relative">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-12 h-12 rounded-full bg-cyan-500/20 flex items-center justify-center">
                      <Wind className="w-6 h-6 text-cyan-500" />
                    </div>
                    <span className="text-sm font-medium text-cyan-400 uppercase tracking-wide">Breathing Rate</span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold text-foreground">
                      {avgBreathing !== null ? Math.round(avgBreathing) : "--"}
                    </span>
                    <span className="text-lg text-muted-foreground">BrPM</span>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {avgBreathing !== null && avgBreathing >= 12 && avgBreathing <= 20 ? "Normal range" : avgBreathing !== null ? "Outside normal range" : "No data"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

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
