import { useState, useEffect } from "react";
import { Clock } from "lucide-react";

interface InterviewTimerProps {
  isRunning: boolean;
  onTimeUpdate?: (seconds: number) => void;
}

const InterviewTimer = ({ isRunning, onTimeUpdate }: InterviewTimerProps) => {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    
    if (isRunning) {
      interval = setInterval(() => {
        setSeconds((prev) => {
          const newSeconds = prev + 1;
          onTimeUpdate?.(newSeconds);
          return newSeconds;
        });
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRunning, onTimeUpdate]);

  const formatTime = (totalSeconds: number) => {
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;

    if (hrs > 0) {
      return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex items-center gap-2 px-4 py-2 rounded-full glass-control">
      <Clock className="w-4 h-4 text-primary" />
      <span className="font-mono text-sm font-medium text-foreground tracking-wider">
        {formatTime(seconds)}
      </span>
      {isRunning && (
        <div className="w-2 h-2 rounded-full bg-[hsl(var(--interview-success))] animate-pulse" />
      )}
    </div>
  );
};

export default InterviewTimer;
