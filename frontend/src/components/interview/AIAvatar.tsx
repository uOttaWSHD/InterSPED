import { useRef, useEffect } from "react";

interface AIAvatarProps {
  isSpeaking?: boolean;
  size?: "small" | "large";
}

const AIAvatar = ({ isSpeaking = false, size = "large" }: AIAvatarProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Set up the video element to loop
    video.loop = true;
    video.muted = true;
    video.autoplay = true;
    
    // Play the video
    video.play().catch(error => {
      console.error("Error playing video:", error);
    });
  }, []);

  const sizeClasses = size === "large" 
    ? "w-64 h-64 md:w-80 md:h-80" 
    : "w-24 h-24 md:w-32 md:h-32";

  return (
    <div className={`relative ${sizeClasses} flex items-center justify-center`}>
      {/* Outer glow ring */}
      <div 
        className={`absolute inset-0 rounded-full bg-gradient-to-r from-primary/30 to-accent/30 blur-xl transition-all duration-300 ${isSpeaking ? 'opacity-80 scale-110' : 'opacity-40'}`}
        style={{ transform: isSpeaking ? `scale(1.1)` : 'scale(1)' }}
      />
      
      {/* Secondary ring */}
      <div 
        className={`absolute inset-4 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 blur-lg transition-all duration-200 ${isSpeaking ? 'opacity-70' : 'opacity-30'}`}
      />

      {/* Main avatar container */}
      <div className={`relative rounded-full overflow-hidden border-2 border-primary/30 ${size === 'large' ? 'w-56 h-56 md:w-72 md:h-72' : 'w-20 h-20 md:w-28 md:h-28'} ${isSpeaking ? 'avatar-pulse' : ''}`}>
        {/* Video background with theme color */}
        <div className="absolute inset-0 bg-[hsl(var(--interview-elevated))]">
          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            src="/face.mp4"
          />
        </div>
      </div>

      {/* Status indicator */}
      <div className={`absolute ${size === 'large' ? 'bottom-4 right-4' : 'bottom-1 right-1'} flex items-center gap-2`}>
        <div className={`${size === 'large' ? 'w-4 h-4' : 'w-2 h-2'} rounded-full ${isSpeaking ? 'bg-[hsl(var(--interview-success))]' : 'bg-primary'} animate-pulse`} />
        {size === 'large' && (
          <span className="text-xs text-muted-foreground">{isSpeaking ? 'Speaking' : 'Listening'}</span>
        )}
      </div>
    </div>
  );
};

export default AIAvatar;
