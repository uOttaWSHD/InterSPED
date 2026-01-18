import { useState, useEffect, useRef } from "react";
import AIAvatar from "./AIAvatar";
import UserVideo from "./UserVideo";
import ControlBar from "./ControlBar";
import QuestionPanel from "./QuestionPanel";
import CodeEditor from "./CodeEditor";
import InterviewTimer from "./InterviewTimer";
import { Bot, RotateCcw } from "lucide-react";

// ElevenLabs API configuration
const ELEVENLABS_API_KEY = "sk_e49c018a8789bb8fbeb2161c9aca48a5fd667cabaf3dd9e0";
const ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"; // Rachel voice

interface InterviewRoomProps {
  onEndInterview: () => void;
  initialResponse?: string | null;
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

const InterviewRoom = ({ onEndInterview, initialResponse }: InterviewRoomProps) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isCodeSharing, setIsCodeSharing] = useState(false);
  const [isQuestionPanelCollapsed, setIsQuestionPanelCollapsed] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [lastAudioUrl, setLastAudioUrl] = useState<string | null>(null);
  const hasSpokenInitialRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Test function to check if audio works
  const testAudio = () => {
    if (!audioRef.current) return;
    
    const audio = audioRef.current;
    // Use a data URL for a simple beep tone
    audio.src = "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIGGi785eeSwgMUrDj07xsIQQ4";
    audio.volume = 1.0;
    audio.muted = false;
    audio.play().then(() => {
      console.log("Test audio played successfully");
      alert("Test audio played - did you hear it?");
    }).catch(e => {
      console.error("Test audio failed:", e);
      alert("Test audio failed: " + e.message);
    });
  };

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

  // Function to speak text using ElevenLabs TTS
  const speakWithElevenLabs = async (text: string) => {
    console.log("ElevenLabs TTS: Starting with text:", text);
    try {
      if (!audioRef.current) {
        console.error("Audio element ref not available");
        return;
      }

      setIsAISpeaking(true);
      
      const response = await fetch(
        `https://api.elevenlabs.io/v1/text-to-speech/${ELEVENLABS_VOICE_ID}`,
        {
          method: "POST",
          headers: {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY,
          },
          body: JSON.stringify({
            text: text,
            model_id: "eleven_flash_v2_5",
            voice_settings: {
              stability: 0.5,
              similarity_boost: 0.75,
            },
          }),
        }
      );

      console.log("ElevenLabs TTS: Response status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("ElevenLabs API error response:", errorText);
        throw new Error(`ElevenLabs API error: ${response.status}`);
      }

      const audioBlob = await response.blob();
      console.log("ElevenLabs TTS: Got audio blob, size:", audioBlob.size, "type:", audioBlob.type);
      
      const audioUrl = URL.createObjectURL(audioBlob);
      setLastAudioUrl(audioUrl);  // Store for replay
      const audio = audioRef.current;
      
      audio.src = audioUrl;
      audio.volume = 1.0;
      audio.muted = false;
      
      console.log("ElevenLabs TTS: Audio element src set, volume:", audio.volume, "muted:", audio.muted);
      
      try {
        await audio.play();
        console.log("ElevenLabs TTS: Audio play promise resolved");
      } catch (playError) {
        console.error("ElevenLabs TTS: Play error:", playError);
        setIsAISpeaking(false);
      }
    } catch (error) {
      console.error("ElevenLabs TTS Error:", error);
      setIsAISpeaking(false);
    }
  };

  // Speak the initial response from /start using ElevenLabs TTS
  useEffect(() => {
    console.log("ElevenLabs TTS: useEffect triggered, initialResponse:", initialResponse);
    if (initialResponse && !hasSpokenInitialRef.current && audioRef.current) {
      hasSpokenInitialRef.current = true;
      speakWithElevenLabs(initialResponse);
    }
  }, [initialResponse]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
    };
  }, []);

  // Simulate AI speaking periodically (only if no real TTS from initialResponse)
  useEffect(() => {
    // Skip simulation if we have real TTS
    if (initialResponse) return;

    const interval = setInterval(() => {
      setIsAISpeaking(true);
      setTimeout(() => setIsAISpeaking(false), 3000 + Math.random() * 2000);
    }, 8000 + Math.random() * 4000);

    // Initial greeting (simulated)
    setIsAISpeaking(true);
    setTimeout(() => setIsAISpeaking(false), 4000);

    return () => clearInterval(interval);
  }, [initialResponse]);

  return (
    <div className="h-screen flex flex-col bg-[hsl(var(--interview-surface))] overflow-hidden">
      {/* Hidden audio element for TTS */}
      <audio
        ref={audioRef}
        crossOrigin="anonymous"
        volume={1.0}
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
            onClick={testAudio}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-yellow-500/10 hover:bg-yellow-500/20 transition-colors"
            title="Test audio output"
          >
            <span className="text-xs font-medium text-yellow-600">🔊 Test Audio</span>
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
                <div className="mt-6 text-center">
                  <h2 className="text-xl font-semibold text-foreground">AI Interviewer</h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    {isAISpeaking ? "Speaking..." : "Listening to your response"}
                  </p>
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
