import { useEffect, useRef, useState } from "react";
import { VideoOff } from "lucide-react";

interface UserVideoProps {
  isVideoOn: boolean;
  isMuted?: boolean;
  size?: "small" | "medium";
}

const UserVideo = ({ isVideoOn, isMuted = false, size = "small" }: UserVideoProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const [micLevel, setMicLevel] = useState(0);

  const sizeClasses = size === "medium" 
    ? "w-48 h-36 md:w-64 md:h-48" 
    : "w-32 h-24 md:w-44 md:h-32";

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
            analyserRef.current.getByteFrequencyData(dataArrayRef.current as any);
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

  // Calculate glow intensity based on mic level
  const glowIntensity = Math.min(micLevel * 1.5, 1);
  const glowColor = glowIntensity > 0.5 ? 'rgba(34, 197, 94, 0.6)' : 'rgba(34, 197, 94, 0.3)'; // Green when speaking

  return (
    <div 
      className={`relative ${sizeClasses} rounded-xl overflow-hidden bg-[hsl(var(--interview-elevated))] border border-border/50 shadow-2xl transition-all duration-100`}
      style={{
        boxShadow: glowIntensity > 0.2 
          ? `0 0 ${20 + glowIntensity * 30}px ${glowColor}, 0 0 ${10 + glowIntensity * 15}px ${glowColor}, 0 0 1px rgba(34, 197, 94, 0.5)`
          : '0 0 0 1px rgba(34, 197, 94, 0.2)'
      }}
    >
      {isVideoOn ? (
        <>
          {/* Real video feed */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="absolute inset-0 w-full h-full object-cover"
          />
          {/* Video overlay gradient */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent pointer-events-none" />
          {/* User name tag */}
          <div className="absolute bottom-2 left-2 px-2 py-1 rounded-md bg-black/50 backdrop-blur-sm z-10">
            <span className="text-xs text-white font-medium">You</span>
          </div>
        </>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[hsl(var(--interview-surface))]">
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
            <VideoOff className="w-5 h-5 text-muted-foreground" />
          </div>
          <span className="text-xs text-muted-foreground">Camera off</span>
        </div>
      )}

      {/* Live indicator */}
      {isVideoOn && (
        <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-black/50 backdrop-blur-sm z-10">
          <div className="w-2 h-2 rounded-full bg-[hsl(var(--interview-success))] animate-pulse" />
          <span className="text-[10px] text-white uppercase tracking-wider">Live</span>
        </div>
      )}
    </div>

  );
};

export default UserVideo;

