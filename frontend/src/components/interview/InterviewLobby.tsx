import { useState, useEffect, useRef } from "react";
import { Video, VideoOff, Mic, MicOff, ChevronRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface InterviewLobbyProps {
  onStartInterview: (payload: { companyName: string; jobUrl: string }) => void;
}

const InterviewLobby = ({ onStartInterview }: InterviewLobbyProps) => {
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [jobUrl, setJobUrl] = useState("");
  const [companyName, setCompanyName] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [micLevel, setMicLevel] = useState(0);

  useEffect(() => {
    const setupMedia = async () => {
      try {
        // Stop previous stream if it exists
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }

        // Cancel previous animation frame
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }

        // Request camera and microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
          video: isVideoOn ? { width: { ideal: 1280 }, height: { ideal: 720 } } : false,
          audio: true,
        });

        streamRef.current = stream;

        // Setup video if enabled
        if (isVideoOn && videoRef.current) {
          const videoTrack = stream.getVideoTracks()[0];
          if (videoTrack) {
            videoRef.current.srcObject = new MediaStream([videoTrack, ...stream.getAudioTracks()]);
          }
        } else if (videoRef.current) {
          // Clear video element when camera is off
          videoRef.current.srcObject = null;
        }

        // Setup audio analysis
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioContextRef.current = audioContext;

        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        dataArrayRef.current = dataArray;

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        // Animation loop for mic level
        const animationLoop = () => {
          if (analyserRef.current && dataArrayRef.current && !isMuted) {
            analyserRef.current.getByteFrequencyData(dataArrayRef.current);
            const average = 
              dataArrayRef.current.reduce((a, b) => a + b) / 
              dataArrayRef.current.length;
            setMicLevel(average / 256); // Normalize to 0-1
          } else {
            setMicLevel(0);
          }
          animationFrameRef.current = requestAnimationFrame(animationLoop);
        };
        animationFrameRef.current = requestAnimationFrame(animationLoop);
      } catch (error) {
        console.error("Error accessing media devices:", error);
      }
    };

    setupMedia();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isVideoOn, isMuted]);

  const isValidUrl = (url: string): boolean => {
    try {
      new URL(url);
      return /^https?:\/\/.+/i.test(url);
    } catch {
      return false;
    }
  };

  const handleStartInterview = () => {
    if (!isValidUrl(jobUrl)) return;
    if (!companyName.trim()) return;

    onStartInterview({ companyName: companyName.trim(), jobUrl });
  };

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
            <div className="w-72 h-52 md:w-96 md:h-72 rounded-2xl overflow-hidden bg-[hsl(var(--interview-elevated))] border border-border shadow-2xl relative flex items-center justify-center">
              {isVideoOn ? (
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-secondary to-muted">
                  <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-3">
                    <Video className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <p className="text-muted-foreground">Camera is off</p>
                </div>
              )}
              
              {/* Mic Level Indicator - Vertical Bar */}
              <div className="absolute bottom-4 right-4 flex items-end gap-1 h-16">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className={`w-1 rounded-full transition-all duration-100 ${
                      isMuted 
                        ? 'bg-destructive/30' 
                        : i / 8 < micLevel 
                        ? 'bg-primary' 
                        : 'bg-muted'
                    }`}
                    style={{
                      height: `${12 + i * 6}px`,
                      opacity: isMuted ? 0.5 : i / 8 < micLevel ? 1 : 0.3,
                    }}
                  />
                ))}
              </div>
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

        {/* Job Input & Company Select */}
        <div className="bg-[hsl(var(--interview-elevated))] rounded-xl p-6 border border-border space-y-4">
          <h3 className="font-semibold text-foreground">Job Posting</h3>
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="jobUrl" className="text-sm text-muted-foreground">
                Paste the job posting URL
              </label>
              <Input
                id="jobUrl"
                type="url"
                placeholder="https://example.com/job-posting"
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
                className="bg-[hsl(var(--interview-surface))] border-border text-foreground placeholder:text-muted-foreground/50"
              />
              {jobUrl && !isValidUrl(jobUrl) && (
                <p className="text-xs text-destructive">Please enter a valid URL (e.g., https://example.com/job)</p>
              )}
              {jobUrl && isValidUrl(jobUrl) && (
                <p className="text-xs text-[hsl(var(--interview-success))]">✓ Valid URL</p>
              )}
            </div>

            <div className="space-y-2">
              <label htmlFor="companyName" className="text-sm text-muted-foreground">Company Name</label>
              <Input
                id="companyName"
                type="text"
                placeholder="e.g. Google, Amazon, Meta"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="bg-[hsl(var(--interview-surface))] border-border text-foreground placeholder:text-muted-foreground/50"
              />
            </div>
          </div>
        </div>

        {/* Start Button */}
        <Button
          onClick={handleStartInterview}
          disabled={!isValidUrl(jobUrl) || companyName.trim().length === 0}
          className="w-full h-14 text-lg font-semibold bg-primary hover:bg-primary/90 glow-primary transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Start Interview
          <ChevronRight className="w-5 h-5 ml-2" />
        </Button>


      </div>
    </div>
  );
};

export default InterviewLobby;
