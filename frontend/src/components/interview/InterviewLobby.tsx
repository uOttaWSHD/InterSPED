import { useState } from "react";
import { Video, VideoOff, Mic, MicOff, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface InterviewLobbyProps {
  onStartInterview: () => void;
}

const InterviewLobby = ({ onStartInterview }: InterviewLobbyProps) => {
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isMuted, setIsMuted] = useState(false);

  return (
    <div className="min-h-screen bg-[hsl(var(--interview-surface))] flex flex-col items-center justify-center p-6">
      {/* Background gradient effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-2xl w-full space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium">
            <Sparkles className="w-4 h-4" />
            AI Technical Interview
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-foreground">
            Ready to begin your interview?
          </h1>
          <p className="text-muted-foreground text-lg">
            Check your camera and microphone before starting
          </p>
        </div>

        {/* Video Preview */}
        <div className="flex flex-col items-center space-y-6">
          <div className="relative">
            <div className="w-72 h-52 md:w-96 md:h-72 rounded-2xl overflow-hidden bg-[hsl(var(--interview-elevated))] border border-border shadow-2xl">
              {isVideoOn ? (
                <div className="absolute inset-0 bg-gradient-to-br from-secondary to-muted flex items-center justify-center">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center">
                    <span className="text-4xl">👤</span>
                  </div>
                </div>
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-3">
                    <Video className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground">Camera is off</p>
                </div>
              )}
            </div>
          </div>

          {/* Device Controls */}
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              onClick={() => setIsMuted(!isMuted)}
              className={`h-12 w-12 rounded-full ${
                isMuted 
                  ? 'bg-destructive/20 text-destructive hover:bg-destructive/30' 
                  : 'bg-[hsl(var(--interview-control))] hover:bg-[hsl(var(--interview-control-hover))]'
              }`}
            >
              {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </Button>
            <Button
              variant="ghost"
              onClick={() => setIsVideoOn(!isVideoOn)}
              className={`h-12 w-12 rounded-full ${
                !isVideoOn 
                  ? 'bg-destructive/20 text-destructive hover:bg-destructive/30' 
                  : 'bg-[hsl(var(--interview-control))] hover:bg-[hsl(var(--interview-control-hover))]'
              }`}
            >
              {!isVideoOn ? <VideoOff className="w-5 h-5" /> : <Video className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Interview Info */}
        <div className="bg-[hsl(var(--interview-elevated))] rounded-xl p-6 border border-border space-y-4">
          <h3 className="font-semibold text-foreground">Interview Details</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Type</p>
              <p className="text-foreground font-medium">Technical Coding</p>
            </div>
            <div>
              <p className="text-muted-foreground">Duration</p>
              <p className="text-foreground font-medium">45 minutes</p>
            </div>
            <div>
              <p className="text-muted-foreground">Questions</p>
              <p className="text-foreground font-medium">3 coding problems</p>
            </div>
            <div>
              <p className="text-muted-foreground">Difficulty</p>
              <p className="text-foreground font-medium">Medium</p>
            </div>
          </div>
        </div>

        {/* Start Button */}
        <Button
          onClick={onStartInterview}
          className="w-full h-14 text-lg font-semibold bg-primary hover:bg-primary/90 glow-primary transition-all duration-300"
        >
          Start Interview
          <ChevronRight className="w-5 h-5 ml-2" />
        </Button>

        <p className="text-center text-xs text-muted-foreground">
          By starting, you agree to our terms of service and privacy policy
        </p>
      </div>
    </div>
  );
};

export default InterviewLobby;
