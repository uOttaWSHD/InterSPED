import { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

interface AnalysisPageProps {
  companyName: string;
  jobUrl: string;
  onComplete: (initialResponse?: string) => void;
  onFail: () => void;
}

const stepsTemplate = [
  { key: "scrape", label: "Scraping job posting" },
  { key: "extract", label: "Extracting requirements" },
  { key: "summarize", label: "Summarizing role & responsibilities" },
  { key: "questions", label: "Generating interview questions" },
];

const AnalysisPage = ({ companyName, jobUrl, onComplete, onFail }: AnalysisPageProps) => {
  const [steps, setSteps] = useState<{ key: string; label: string; status: "pending" | "loading" | "done" }[]>(
    stepsTemplate.map((s, i) => ({ ...s, status: i === 0 ? "loading" : "pending" }))
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    const run = async () => {
      try {
        // Start API call immediately
        const res = await fetch("https://hammerhead-app-yfrzd.ondigitalocean.app/api/v1/scrape", {
          method: "POST",
          headers: { 
            "accept": "application/json",
            "Content-Type": "application/json" 
          },
          body: JSON.stringify({ company_name: companyName, job_posting_url: jobUrl }),
        });

        // Progress UI while waiting
        const advanceStep = (index: number) => {
          setSteps(prev => prev.map((s, i) => {
            if (i < index) return { ...s, status: "done" };
            if (i === index) return { ...s, status: "loading" };
            return { ...s, status: "pending" };
          }));
        };

        // Simulate step progression over time during network call
        advanceStep(1);
        await new Promise(r => setTimeout(r, 700));
        advanceStep(2);
        await new Promise(r => setTimeout(r, 700));
        advanceStep(3);

        const data = await res.json().catch(() => ({}));
        console.log("Analysis response:", data);

        // Check if scrape was successful before proceeding
        if (data.success === false) {
          setError("Failed to analyze job posting. Please check the URL and try again.");
          setTimeout(() => {
            if (isMounted) onFail();
          }, 2000);
          return;
        }

        // Filter only relevant keys for interview start
        const filtered = {
          company_overview: data.company_overview,
          interview_insights: data.interview_insights,
          session_id: data.session_id,
          metadata: data.metadata,
        };

        const interviewRes = await fetch("http://localhost:5000/api/interview/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(filtered),
        });

        const interviewData = await interviewRes.json().catch(() => ({}));
        console.log("Interview start response:", interviewData);

        // Check if interview start was successful
        if (interviewData.success === false) {
          setError("Failed to start interview. Please try again.");
          setTimeout(() => {
            if (isMounted) onFail();
          }, 2000);
          return;
        }

        // Finish all steps
        setSteps(prev => prev.map(s => ({ ...s, status: "done" })));

        // Small pause then continue with initial response
        setTimeout(() => {
          if (isMounted) onComplete(interviewData.response);
        }, 600);
      } catch (e: any) {
        console.error("Analysis failed:", e);
        setError("Failed to analyze job posting. Please try again.");
      }
    };

    run();
    return () => { isMounted = false; };
  }, [companyName, jobUrl, onComplete]);

  return (
    <div className="min-h-screen bg-[hsl(var(--interview-surface))] flex flex-col items-center justify-center p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-xl w-full space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Preparing Your AI Interview</h1>
          <p className="text-muted-foreground">Analyzing {companyName} job posting</p>
        </div>

        <div className="bg-[hsl(var(--interview-elevated))] rounded-xl p-6 border border-border">
          <ul className="space-y-4">
            {steps.map((s) => (
              <li key={s.key} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {s.status === "done" ? (
                    <CheckCircle2 className="w-5 h-5 text-[hsl(var(--interview-success))]" />
                  ) : (
                    <Loader2 className={`w-5 h-5 text-muted-foreground ${s.status === "loading" ? "animate-spin" : "opacity-40"}`} />
                  )}
                  <span className="text-sm text-foreground">{s.label}</span>
                </div>
                <div className="w-40 h-2 bg-[hsl(var(--interview-surface))] rounded-full overflow-hidden">
                  <div className={`h-full ${s.status === "done" ? "bg-[hsl(var(--interview-success))]" : s.status === "loading" ? "bg-primary animate-pulse" : "bg-muted"}`} style={{ width: s.status === "done" ? "100%" : s.status === "loading" ? "60%" : "20%" }} />
                </div>
              </li>
            ))}
          </ul>

          {error && (
            <div className="mt-4 text-sm text-destructive">{error}</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnalysisPage;
