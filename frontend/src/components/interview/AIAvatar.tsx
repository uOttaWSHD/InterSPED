import { useState, useEffect } from "react";

interface AIAvatarProps {
  isSpeaking?: boolean;
  size?: "small" | "large";
}

const AIAvatar = ({ isSpeaking = false, size = "large" }: AIAvatarProps) => {
  const [pulseIntensity, setPulseIntensity] = useState(0);

  useEffect(() => {
    if (isSpeaking) {
      const interval = setInterval(() => {
        setPulseIntensity(Math.random());
      }, 150);
      return () => clearInterval(interval);
    }
    setPulseIntensity(0);
  }, [isSpeaking]);

  const sizeClasses = size === "large" 
    ? "w-64 h-64 md:w-80 md:h-80" 
    : "w-24 h-24 md:w-32 md:h-32";

  return (
    <div className={`relative ${sizeClasses} flex items-center justify-center`}>
      {/* Outer glow ring */}
      <div 
        className={`absolute inset-0 rounded-full bg-gradient-to-r from-primary/30 to-accent/30 blur-xl transition-all duration-300 ${isSpeaking ? 'opacity-80 scale-110' : 'opacity-40'}`}
        style={{ transform: isSpeaking ? `scale(${1.1 + pulseIntensity * 0.1})` : 'scale(1)' }}
      />
      
      {/* Secondary ring */}
      <div 
        className={`absolute inset-4 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 blur-lg transition-all duration-200 ${isSpeaking ? 'opacity-70' : 'opacity-30'}`}
      />

      {/* Main avatar container */}
      <div className={`relative rounded-full bg-gradient-to-br from-[hsl(var(--interview-elevated))] to-[hsl(var(--interview-surface))] border-2 border-primary/30 overflow-hidden ${size === 'large' ? 'w-56 h-56 md:w-72 md:h-72' : 'w-20 h-20 md:w-28 md:h-28'} ${isSpeaking ? 'avatar-pulse' : ''}`}>
        {/* Avatar face */}
        <div className="absolute inset-0 flex items-center justify-center">
          {/* Face background */}
          <div className="relative w-full h-full bg-gradient-to-b from-primary/5 to-accent/5">
            {/* Eyes container */}
            <div className={`absolute ${size === 'large' ? 'top-[35%]' : 'top-[32%]'} left-1/2 -translate-x-1/2 flex gap-${size === 'large' ? '8' : '4'}`}>
              {/* Left eye */}
              <div className={`${size === 'large' ? 'w-8 h-8 md:w-10 md:h-10' : 'w-3 h-3'} rounded-full bg-primary/80 relative`}>
                <div className={`absolute ${size === 'large' ? 'w-3 h-3 md:w-4 md:h-4' : 'w-1.5 h-1.5'} rounded-full bg-white/90 top-1 left-1`} />
                <div className={`absolute inset-0 rounded-full ${isSpeaking ? 'animate-pulse' : ''}`} style={{ boxShadow: '0 0 15px hsl(var(--primary))' }} />
              </div>
              {/* Right eye */}
              <div className={`${size === 'large' ? 'w-8 h-8 md:w-10 md:h-10' : 'w-3 h-3'} rounded-full bg-primary/80 relative`}>
                <div className={`absolute ${size === 'large' ? 'w-3 h-3 md:w-4 md:h-4' : 'w-1.5 h-1.5'} rounded-full bg-white/90 top-1 left-1`} />
                <div className={`absolute inset-0 rounded-full ${isSpeaking ? 'animate-pulse' : ''}`} style={{ boxShadow: '0 0 15px hsl(var(--primary))' }} />
              </div>
            </div>

            {/* Mouth / Speaking indicator */}
            <div className={`absolute ${size === 'large' ? 'bottom-[28%]' : 'bottom-[25%]'} left-1/2 -translate-x-1/2 flex items-end justify-center gap-1`}>
              {isSpeaking ? (
                <>
                  {[0.3, 0.6, 1, 0.6, 0.3].map((delay, i) => (
                    <div
                      key={i}
                      className={`${size === 'large' ? 'w-2 h-6' : 'w-1 h-3'} bg-primary rounded-full speaking-indicator`}
                      style={{ animationDelay: `${delay * 0.1}s` }}
                    />
                  ))}
                </>
              ) : (
                <div className={`${size === 'large' ? 'w-12 h-2' : 'w-6 h-1'} bg-primary/50 rounded-full`} />
              )}
            </div>

            {/* Circuit pattern decoration */}
            <svg className="absolute inset-0 w-full h-full opacity-10" viewBox="0 0 100 100">
              <circle cx="20" cy="20" r="2" fill="currentColor" className="text-primary" />
              <circle cx="80" cy="20" r="2" fill="currentColor" className="text-primary" />
              <circle cx="20" cy="80" r="2" fill="currentColor" className="text-primary" />
              <circle cx="80" cy="80" r="2" fill="currentColor" className="text-primary" />
              <path d="M20 20 L35 35 M80 20 L65 35 M20 80 L35 65 M80 80 L65 65" stroke="currentColor" className="text-primary" strokeWidth="0.5" />
            </svg>
          </div>
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
