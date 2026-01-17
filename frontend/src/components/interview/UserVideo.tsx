import { User, VideoOff } from "lucide-react";

interface UserVideoProps {
  isVideoOn: boolean;
  size?: "small" | "medium";
}

const UserVideo = ({ isVideoOn, size = "small" }: UserVideoProps) => {
  const sizeClasses = size === "medium" 
    ? "w-48 h-36 md:w-64 md:h-48" 
    : "w-32 h-24 md:w-44 md:h-32";

  return (
    <div className={`relative ${sizeClasses} rounded-xl overflow-hidden bg-[hsl(var(--interview-elevated))] border border-border/50 shadow-2xl`}>
      {isVideoOn ? (
        <>
          {/* Simulated video feed with gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-secondary to-muted">
            {/* Fake video placeholder - would be actual webcam feed */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-br from-primary/30 to-accent/30 flex items-center justify-center">
                <User className="w-8 h-8 md:w-10 md:h-10 text-foreground/70" />
              </div>
            </div>
            {/* Video overlay gradient */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
          </div>
          {/* User name tag */}
          <div className="absolute bottom-2 left-2 px-2 py-1 rounded-md bg-black/50 backdrop-blur-sm">
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
        <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2 py-1 rounded-md bg-black/50 backdrop-blur-sm">
          <div className="w-2 h-2 rounded-full bg-[hsl(var(--interview-success))] animate-pulse" />
          <span className="text-[10px] text-white uppercase tracking-wider">Live</span>
        </div>
      )}
    </div>
  );
};

export default UserVideo;
