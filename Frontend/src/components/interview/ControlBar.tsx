import { Mic, MicOff, Video, VideoOff, Code, PhoneOff, MonitorOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface ControlBarProps {
  isMuted: boolean;
  isVideoOn: boolean;
  isCodeSharing: boolean;
  onToggleMute: () => void;
  onToggleVideo: () => void;
  onToggleCodeShare: () => void;
  onEndInterview: () => void;
}

const ControlBar = ({
  isMuted,
  isVideoOn,
  isCodeSharing,
  onToggleMute,
  onToggleVideo,
  onToggleCodeShare,
  onEndInterview,
}: ControlBarProps) => {
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex items-center justify-center gap-2 md:gap-3 px-4 md:px-8 py-4 glass-control rounded-2xl">
        {/* Mute Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={onToggleMute}
              variant="ghost"
              size="icon"
              className={`w-12 h-12 md:w-14 md:h-14 rounded-full transition-all duration-200 ${
                isMuted 
                  ? 'bg-destructive/20 hover:bg-destructive/30 text-destructive' 
                  : 'bg-[hsl(var(--interview-control))] hover:bg-[hsl(var(--interview-control-hover))] text-foreground'
              }`}
            >
              {isMuted ? <MicOff className="w-5 h-5 md:w-6 md:h-6" /> : <Mic className="w-5 h-5 md:w-6 md:h-6" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="bg-card border-border">
            <p>{isMuted ? 'Unmute' : 'Mute'}</p>
          </TooltipContent>
        </Tooltip>

        {/* Video Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={onToggleVideo}
              variant="ghost"
              size="icon"
              className={`w-12 h-12 md:w-14 md:h-14 rounded-full transition-all duration-200 ${
                !isVideoOn 
                  ? 'bg-destructive/20 hover:bg-destructive/30 text-destructive' 
                  : 'bg-[hsl(var(--interview-control))] hover:bg-[hsl(var(--interview-control-hover))] text-foreground'
              }`}
            >
              {isVideoOn ? <Video className="w-5 h-5 md:w-6 md:h-6" /> : <VideoOff className="w-5 h-5 md:w-6 md:h-6" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="bg-card border-border">
            <p>{isVideoOn ? 'Turn off camera' : 'Turn on camera'}</p>
          </TooltipContent>
        </Tooltip>

        {/* Share Code Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={onToggleCodeShare}
              variant="ghost"
              size="icon"
              className={`w-12 h-12 md:w-14 md:h-14 rounded-full transition-all duration-200 ${
                isCodeSharing 
                  ? 'bg-primary glow-primary text-primary-foreground hover:bg-primary/90' 
                  : 'bg-primary/20 hover:bg-primary/30 text-primary'
              }`}
            >
              {isCodeSharing ? <MonitorOff className="w-5 h-5 md:w-6 md:h-6" /> : <Code className="w-5 h-5 md:w-6 md:h-6" />}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="bg-card border-border">
            <p>{isCodeSharing ? 'Stop sharing' : 'Share Code'}</p>
          </TooltipContent>
        </Tooltip>

        {/* Separator */}
        <div className="w-px h-8 bg-border/50 mx-2" />

        {/* End Interview Button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={onEndInterview}
              variant="ghost"
              size="icon"
              className="w-12 h-12 md:w-14 md:h-14 rounded-full bg-destructive hover:bg-destructive/90 text-destructive-foreground transition-all duration-200"
            >
              <PhoneOff className="w-5 h-5 md:w-6 md:h-6" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top" className="bg-card border-border">
            <p>End Interview</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
};

export default ControlBar;
