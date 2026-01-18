import { useState, useEffect, useRef } from "react";
import AIAvatar from "./AIAvatar";
import UserVideo from "./UserVideo";
import ControlBar from "./ControlBar";
import CodeEditor from "./CodeEditor";
import InterviewTimer from "./InterviewTimer";
import { Bot, RotateCcw, MessageSquare, Mic, MicOff } from "lucide-react";
import { useVoiceInterview } from "@/hooks/use-voice-interview";

interface InterviewRoomProps {
  onEndInterview: () => void;
  initialResponse?: string | null;
  sessionId?: string | null;
}

const sampleQuestions = [
  {
    id: 1,
    title: "Two Sum",
    difficulty: "Easy" as const,
    description: `Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

You can return the answer in any order.`,
    examples: [
      `Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: Because nums[0] + nums[1] == 9, we return [0, 1].`,
      `Input: nums = [3,2,4], target = 6
Output: [1,2]`,
    ],
  },
  {
    id: 2,
    title: "Valid Parentheses",
    difficulty: "Easy" as const,
    description: `Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

An input string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.
3. Every close bracket has a corresponding open bracket of the same type.`,
    examples: [
      `Input: s = "()"
Output: true`,
      `Input: s = "()[]{}"
Output: true`,
      `Input: s = "(]"
Output: false`,
    ],
  },
  {
    id: 3,
    title: "Merge Two Sorted Lists",
    difficulty: "Medium" as const,
    description: `You are given the heads of two sorted linked lists list1 and list2.

Merge the two lists into one sorted list. The list should be made by splicing together the nodes of the first two lists.

Return the head of the merged linked list.`,
    examples: [
      `Input: list1 = [1,2,4], list2 = [1,3,4]
Output: [1,1,2,3,4,4]`,
      `Input: list1 = [], list2 = []
Output: []`,
    ],
  },
];

const InterviewRoom = ({ onEndInterview, initialResponse, sessionId }: InterviewRoomProps) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isCodeSharing, setIsCodeSharing] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string>(initialResponse || "");
  const [showTranscript, setShowTranscript] = useState(true);
  const [audioStarted, setAudioStarted] = useState(false);
  const hasSpokenInitialRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const {
    isConnected,
    isListening,
    transcript: liveTranscript,
    partialTranscript,
    startInterview,
    stopInterview,
  } = useVoiceInterview({
    sessionId: sessionId || null,
    onTranscript: (text) => setTranscript(text),
    onAISpeaking: (speaking) => setIsAISpeaking(speaking),
    onAudioReceived: async (b64) => {
      console.log("[InterviewRoom] Audio received via WebSocket");
      try {
        const audioBlob = await fetch(`data:audio/mpeg;base64,${b64}`).then(r => r.blob());
        const url = URL.createObjectURL(audioBlob);
        setLastAudioUrl(url);
      } catch (err) {
        console.error("[InterviewRoom] Failed to process received audio", err);
      }
    },
    audioElement: audioRef.current,
  });

  const handleStartAudio = async () => {
    console.log("[InterviewRoom] User triggered audio start");
    
    // Unlock Audio on the page by playing a silent buffer
    if (audioRef.current) {
      audioRef.current.play().catch(() => {
        // Expected to fail if no src, but it registers the interaction
      });
    }

    setAudioStarted(true);
    if (sessionId) {
      startInterview();
    }
    if (initialResponse && !hasSpokenInitialRef.current) {
      hasSpokenInitialRef.current = true;
      speakWithElevenLabs(initialResponse);
    }
  };

  // Start voice interview when session is ready AND audio is started
  useEffect(() => {
    if (sessionId && !isConnected && audioStarted) {
      console.log("Starting voice interview with session:", sessionId);
      startInterview();
    }
  }, [sessionId, isConnected, startInterview, audioStarted]);

  // Function to replay the last audio
  const replayLastAudio = async () => {
    if (!lastAudioUrl || !audioRef.current) return;
    
    console.log("Replaying last audio");
    setIsAISpeaking(true);
    const audio = audioRef.current;
    audio.src = lastAudioUrl;
    audio.volume = 1.0;
    audio.muted = false;
    
    try {
      await audio.play();
    } catch (error) {
      console.error("Replay error:", error);
      setIsAISpeaking(false);
    }
  };

  // Function to speak text using ElevenLabs TTS proxy via backend
  const speakWithElevenLabs = async (text: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    console.log("[InterviewRoom] TTS Proxy: Starting with text:", text, "URL:", apiUrl);
    setTranscript(text);
    try {
      if (!audioRef.current) {
        console.error("[InterviewRoom] Audio element ref not available");
        return;
      }

      setIsAISpeaking(true);
      
      const response = await fetch(
        `${apiUrl}/api/voice/tts?text=${encodeURIComponent(text)}`,
        {
          method: "GET",
          headers: {
            "Accept": "audio/mpeg",
          },
        }
      );

      console.log("[InterviewRoom] TTS Proxy: Response status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("TTS Proxy error response:", errorText);
        throw new Error(`TTS Proxy error: ${response.status}`);
      }

      const audioBlob = await response.blob();
      console.log("TTS Proxy: Got audio blob, size:", audioBlob.size, "type:", audioBlob.type);
      
      const audioUrl = URL.createObjectURL(audioBlob);
      setLastAudioUrl(audioUrl);  // Store for replay
      const audio = audioRef.current;
      
      audio.src = audioUrl;
      audio.volume = 1.0;
      audio.muted = false;
      
      console.log("TTS Proxy: Audio element src set, volume:", audio.volume, "muted:", audio.muted);
      
      try {
        await audio.play();
        console.log("TTS Proxy: Audio play promise resolved");
      } catch (playError) {
        console.error("TTS Proxy: Play error:", playError);
        setIsAISpeaking(false);
      }
    } catch (error) {
      console.error("TTS Proxy Error:", error);
      setIsAISpeaking(false);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
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
      <audio
        ref={audioRef}
        crossOrigin="anonymous"
        muted={false}
        onEnded={() => {
          console.log("Audio ended via onEnded");
          setIsAISpeaking(false);
        }}
        onError={(e) => {
          console.error("Audio error event:", e);
          setIsAISpeaking(false);
        }}
        onPlaying={() => {
          console.log("Audio started playing");
        }}
        onLoadedMetadata={() => {
          console.log("Audio metadata loaded");
        }}
        onVolumeChange={() => {
          console.log("Volume changed:", audioRef.current?.volume, "Muted:", audioRef.current?.muted);
        }}
      />
      
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
              disabled={isAISpeaking}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 disabled:opacity-50 transition-colors"
              title="Replay last audio"
            >
              <RotateCcw className="w-4 h-4 text-blue-500" />
              <span className="text-xs font-medium text-blue-500">Replay</span>
            </button>
          )}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[hsl(var(--interview-success))]/10">
            <div className="w-2 h-2 rounded-full bg-[hsl(var(--interview-success))] animate-pulse" />
            <span className="text-xs font-medium text-[hsl(var(--interview-success))]">Recording</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Video/Code Area */}
        <div className="flex-1 flex flex-col relative">
          {isCodeSharing ? (
            /* Code Sharing Mode */
            <div className="flex-1 flex overflow-hidden">
              {/* Code Editor */}
              <div className="flex-1 p-4">
                <CodeEditor />
              </div>

              {/* Side panel with AI and question */}
              <div className="w-80 md:w-96 border-l border-border flex flex-col bg-[hsl(var(--interview-elevated))]">
                {/* Small AI Avatar */}
                <div className="p-4 flex flex-col items-center border-b border-border">
                  <AIAvatar isSpeaking={isAISpeaking} size="small" />
                  <p className="mt-2 text-xs text-muted-foreground">
                    {isAISpeaking ? "AI is speaking..." : "AI is listening"}
                  </p>
                </div>

                {/* User video in code mode */}
                <div className="p-4 flex justify-center border-b border-border">
                  <UserVideo isVideoOn={isVideoOn} isMuted={isMuted} size="small" />
                </div>

                {/* Question in code mode */}
                <div className="flex-1 overflow-y-auto p-4">
                  <h4 className="text-sm font-semibold text-foreground mb-2">
                    Q{sampleQuestions[currentQuestionIndex].id}: {sampleQuestions[currentQuestionIndex].title}
                  </h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {sampleQuestions[currentQuestionIndex].description.slice(0, 200)}...
                  </p>
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
                <AIAvatar isSpeaking={isAISpeaking} size="large" />
                <div className="mt-6 text-center max-w-md">
                  <h2 className="text-xl font-semibold text-foreground">AI Interviewer</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isAISpeaking ? "Speaking..." : "Listening to your response"}
                  </p>
                  
                  {/* Transcript Display */}
                  {showTranscript && (transcript || partialTranscript) && (
                    <div className="mt-6 p-4 rounded-xl bg-black/40 border border-white/10 backdrop-blur-md animate-in fade-in slide-in-from-bottom-2">
                      <p className="text-sm text-foreground/90 leading-relaxed italic">
                        "{transcript}"
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
