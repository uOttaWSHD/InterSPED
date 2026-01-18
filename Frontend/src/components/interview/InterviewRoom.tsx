import { useState, useEffect, useRef } from "react";
import AIAvatar from "./AIAvatar";
import UserVideo from "./UserVideo";
import ControlBar from "./ControlBar";
import CodeEditor from "./CodeEditor";
import InterviewTimer from "./InterviewTimer";
import { Bot, RotateCcw, MessageSquare, Bug, Wifi, WifiOff } from "lucide-react";
import { useVoiceInterview } from "@/hooks/use-voice-interview";

interface InterviewRoomProps {
  onEndInterview: () => void;
  initialResponse?: string | null;
  sessionId?: string | null;
}

const InterviewRoom = ({ onEndInterview, initialResponse, sessionId }: InterviewRoomProps) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isCodeSharing, setIsCodeSharing] = useState(false);
  // REMOVED: isAISpeaking state. Use isMuted as the single source of truth.
  // isMuted = true => User Muted / AI Speaking
  // isMuted = false => User Speaking / AI Silent
  
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string>(initialResponse || "");
  const [showTranscript, setShowTranscript] = useState(true);
    const [showDebug, setShowDebug] = useState(true); // Debug panel visible by default
    const [audioStarted, setAudioStarted] = useState(false);
    const [conversationHistory, setConversationHistory] = useState<Array<{role: 'user' | 'ai', text: string, timestamp: Date}>>([]);
    const hasSpokenInitialRef = useRef(false);
    const hasStartedInterviewRef = useRef(false); // Guard against multiple connection attempts
    const audioRef = useRef<HTMLAudioElement>(null);
    const debugPanelRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll debug panel
  useEffect(() => {
    if (debugPanelRef.current) {
      debugPanelRef.current.scrollTop = debugPanelRef.current.scrollHeight;
    }
  }, [conversationHistory, transcript]);

  // Add initial AI response to history
  useEffect(() => {
    if (initialResponse && conversationHistory.length === 0) {
      setConversationHistory([{ role: 'ai', text: initialResponse, timestamp: new Date() }]);
    }
  }, [initialResponse, conversationHistory.length]);

  // Auto-mute/unmute based on AI speaking state is now handled by onAISpeaking callback directly modifying isMuted
  // No separate useEffect needed for syncing isAISpeaking -> isMuted

  const {
    isConnected,
    isListening,
    partialTranscript,
    startInterview,
    enqueueAudio,
  } = useVoiceInterview({
    sessionId: sessionId || null,
    onTranscript: (text) => {
      console.log("[InterviewRoom] New transcript:", text);
      setTranscript(text);
      // Add user message to conversation history
      setConversationHistory(prev => [...prev, { role: 'user', text, timestamp: new Date() }]);
    },
    onAISpeaking: (speaking) => {
        // Strict Protocol:
        // AI Starts Speaking -> Mute User (speaking = true)
        // AI Stops Speaking -> Unmute User (speaking = false)
        setIsMuted(speaking);
    },
    onAudioReceived: async (b64, aiText) => {
      console.log("[InterviewRoom] Audio received via WebSocket");
      // Add AI response to conversation history
      if (aiText) {
        setConversationHistory(prev => [...prev, { role: 'ai', text: aiText, timestamp: new Date() }]);
      }
      if (b64) {
        try {
          const audioBlob = await fetch(`data:audio/mpeg;base64,${b64}`).then(r => r.blob());
          const url = URL.createObjectURL(audioBlob);
          setLastAudioUrl(url);
        } catch (err) {
          console.error("[InterviewRoom] Failed to process received audio", err);
        }
      }
    },
    audioElement: audioRef.current,
    isMuted,
  });

  const handleStartAudio = async () => {
    console.log("[InterviewRoom] User triggered audio start");
    setAudioStarted(true);
    
    if (initialResponse && !hasSpokenInitialRef.current) {
      hasSpokenInitialRef.current = true;
      speakWithElevenLabs(initialResponse);
    }
  };

  // Start voice interview when session is ready AND audio is started
  // Use ref guard to prevent multiple connection attempts
  useEffect(() => {
    if (sessionId && !isConnected && audioStarted && !hasStartedInterviewRef.current) {
      hasStartedInterviewRef.current = true;
      console.log("Starting voice interview with session:", sessionId);
      startInterview();
    }
  }, [sessionId, isConnected, audioStarted, startInterview]);

  // Function to speak text using ElevenLabs TTS proxy via backend
  const speakWithElevenLabs = async (text: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setTranscript(text);
    try {
      const response = await fetch(`${apiUrl}/api/voice/tts?text=${encodeURIComponent(text)}`);
      if (!response.ok) throw new Error(`TTS Proxy error: ${response.status}`);
      enqueueAudio(await response.blob());
    } catch (error) {
      console.error("TTS Proxy Error:", error);
    }
  };

  // Function to replay the last audio
  const replayLastAudio = async () => {
    if (lastAudioUrl) enqueueAudio(lastAudioUrl);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause();
    };
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[hsl(var(--interview-surface))] overflow-hidden relative">
      {!audioStarted && (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-md">
          <div className="text-center space-y-6 p-8 bg-[hsl(var(--interview-elevated))] rounded-2xl border border-border max-w-md animate-in fade-in zoom-in-95">
            <Bot className="w-16 h-16 text-primary mx-auto mb-4" />
            <h1 className="text-2xl font-bold text-foreground">Ready to Start?</h1>
            <p className="text-muted-foreground">
              Please click the button below to join the interview and enable audio.
            </p>
            <button
              onClick={handleStartAudio}
              className="w-full py-4 px-6 bg-primary text-primary-foreground rounded-xl font-semibold text-lg hover:bg-primary/90 transition-all shadow-lg glow-primary"
            >
              Join Interview
            </button>
          </div>
        </div>
      )}
      {/* Hidden audio element for TTS */}
      <audio ref={audioRef} />
      
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 md:px-6 py-3 bg-[hsl(var(--interview-elevated))] border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10">
            <Bot className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-foreground">AI Interview</span>
          </div>
          <div className="hidden md:block h-4 w-px bg-border" />
          <span className="hidden md:block text-sm text-muted-foreground">
            Technical Coding Round
          </span>
        </div>

        <InterviewTimer isRunning={true} />

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDebug(!showDebug)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${showDebug ? 'bg-orange-500/20 text-orange-400' : 'bg-white/5 text-muted-foreground'}`}
            title="Toggle Debug Panel"
          >
            <Bug className="w-4 h-4" />
            <span className="text-xs font-medium">Debug</span>
          </button>
          <button
            onClick={() => setShowTranscript(!showTranscript)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${showTranscript ? 'bg-primary/20 text-primary' : 'bg-white/5 text-muted-foreground'}`}
            title="Toggle Transcript"
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-xs font-medium">Transcript</span>
          </button>
          {lastAudioUrl && (
            <button
              onClick={replayLastAudio}
              disabled={isMuted} // Disable replay if AI is already speaking (which means isMuted=true)
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 disabled:opacity-50 transition-colors"
              title="Replay last audio"
            >
              <RotateCcw className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-medium text-blue-500">Replay</span>
            </button>
          )}
          {/* Connection Status */}
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${isConnected ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
            {isConnected ? <Wifi className="w-4 h-4 text-green-500" /> : <WifiOff className="w-4 h-4 text-red-500" />}
            <span className={`text-xs font-medium ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--interview-success))]/10">
            <div className={`w-2 h-2 rounded-full ${isListening ? 'bg-[hsl(var(--interview-success))] animate-pulse' : 'bg-gray-500'}`} />
            <span className="text-xs font-medium text-[hsl(var(--interview-success))]">
              {isListening ? 'Listening' : 'Paused'}
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Debug Panel - Left Side */}
        {showDebug && (
          <div className="w-80 border-r border-border bg-[hsl(var(--interview-elevated))] flex flex-col">
            <div className="p-3 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <Bug className="w-4 h-4 text-orange-400" />
                Debug Console
              </h3>
              <div className="mt-2 flex gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded ${isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  WS: {isConnected ? 'OK' : 'DISC'}
                </span>
                <span className={`px-2 py-0.5 rounded ${isListening ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-500/20 text-gray-400'}`}>
                  Mic: {isListening ? 'ON' : 'OFF'}
                </span>
                <span className={`px-2 py-0.5 rounded ${isMuted ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-500/20 text-gray-400'}`}>
                  AI: {isMuted ? 'Speaking' : 'Idle'}
                </span>
              </div>
            </div>
            
            {/* Live Partial Transcript */}
            <div className="p-3 border-b border-border">
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Live Input (partial):</h4>
              <div className="p-2 rounded bg-black/30 min-h-[40px]">
                <p className="text-xs text-yellow-400 font-mono">
                  {partialTranscript || <span className="text-gray-500 italic">Waiting for speech...</span>}
                </p>
              </div>
            </div>
            
            {/* Conversation History */}
            <div className="flex-1 overflow-hidden flex flex-col">
              <div className="p-3 border-b border-border">
                <h4 className="text-xs font-medium text-muted-foreground">Conversation History:</h4>
              </div>
              <div 
                ref={debugPanelRef}
                className="flex-1 overflow-y-auto p-3 space-y-3"
              >
                {conversationHistory.length === 0 ? (
                  <p className="text-xs text-gray-500 italic">No messages yet...</p>
                ) : (
                  conversationHistory.map((msg, i) => (
                    <div key={i} className={`p-2 rounded text-xs ${msg.role === 'user' ? 'bg-blue-500/10 border-l-2 border-blue-500' : 'bg-purple-500/10 border-l-2 border-purple-500'}`}>
                      <div className="flex justify-between items-center mb-1">
                        <span className={`font-semibold ${msg.role === 'user' ? 'text-blue-400' : 'text-purple-400'}`}>
                          {msg.role === 'user' ? 'You' : 'AI'}
                        </span>
                        <span className="text-gray-500 text-[10px]">
                          {msg.timestamp.toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-foreground/80 whitespace-pre-wrap">{msg.text}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Video/Code Area */}
        <div className="flex-1 flex flex-col relative">
          {isCodeSharing ? (
            /* Code Sharing Mode */
            <div className="flex-1 flex overflow-hidden">
              {/* Code Editor */}
              <div className="flex-1 p-4">
              <CodeEditor />
              </div>

              {/* Side panel with AI and user video */}
              <div className="w-80 md:w-96 border-l border-border flex flex-col bg-[hsl(var(--interview-elevated))]">
              {/* Small AI Avatar */}
              <div className="p-4 flex flex-col items-center border-b border-border">
                <AIAvatar isSpeaking={isMuted} size="small" />
                <p className="mt-2 text-xs text-muted-foreground">
                {isMuted ? "AI is speaking..." : "AI is listening"}
                </p>
              </div>

              {/* User video in code mode */}
              <div className="p-4 flex justify-center border-b border-border">
                <UserVideo isVideoOn={isVideoOn} isMuted={isMuted} size="small" />
              </div>
              </div>
            </div>
          ) : (
            /* Normal Interview Mode */
            <div className="flex-1 flex items-center justify-center relative p-6">
              {/* Background gradient effects */}
              <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl" />
              </div>

              {/* AI Avatar - Center */}
              <div className="relative z-10 flex flex-col items-center">
                <AIAvatar isSpeaking={isMuted} size="large" />
                <div className="mt-6 text-center max-w-md">
                  <h2 className="text-xl font-semibold text-foreground">AI Interviewer</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isMuted ? "Speaking..." : "Listening to your response"}
                  </p>
                  
                  {/* Transcript Display */}
                  {showTranscript && (transcript || partialTranscript) && (
                    <div className="mt-6 p-4 rounded-xl bg-black/40 border border-white/10 backdrop-blur-md animate-in fade-in slide-in-from-bottom-2">
                      <p className="text-sm text-foreground/90 leading-relaxed italic">
                        &quot;{transcript}&quot;
                        {partialTranscript && (
                          <span className="text-muted-foreground ml-1">
                            {partialTranscript}...
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* User Video - Picture in Picture */}
              <div className="absolute bottom-6 right-6 z-20">
                <UserVideo isVideoOn={isVideoOn} isMuted={isMuted} size="medium" />
              </div>
            </div>
          )}

          {/* Control Bar - Fixed at bottom */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30">
            <ControlBar
              isMuted={isMuted}
              isVideoOn={isVideoOn}
              isCodeSharing={isCodeSharing}
              onToggleMute={() => setIsMuted(!isMuted)}
              onToggleVideo={() => setIsVideoOn(!isVideoOn)}
              onToggleCodeShare={() => setIsCodeSharing(!isCodeSharing)}
              onEndInterview={onEndInterview}
            />
          </div>
        </div>

      </div>
    </div>
  );
};

export default InterviewRoom;
