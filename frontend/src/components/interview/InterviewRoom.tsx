import { useState, useEffect } from "react";
import AIAvatar from "./AIAvatar";
import UserVideo from "./UserVideo";
import ControlBar from "./ControlBar";
import QuestionPanel from "./QuestionPanel";
import CodeEditor from "./CodeEditor";
import InterviewTimer from "./InterviewTimer";
import { Bot } from "lucide-react";

interface InterviewRoomProps {
  onEndInterview: () => void;
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

const InterviewRoom = ({ onEndInterview }: InterviewRoomProps) => {
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [isCodeSharing, setIsCodeSharing] = useState(false);
  const [isQuestionPanelCollapsed, setIsQuestionPanelCollapsed] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);

  // Simulate AI speaking periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setIsAISpeaking(true);
      setTimeout(() => setIsAISpeaking(false), 3000 + Math.random() * 2000);
    }, 8000 + Math.random() * 4000);

    // Initial greeting
    setIsAISpeaking(true);
    setTimeout(() => setIsAISpeaking(false), 4000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-[hsl(var(--interview-surface))] overflow-hidden">
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
                  <UserVideo isVideoOn={isVideoOn} size="small" />
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
                <UserVideo isVideoOn={isVideoOn} size="medium" />
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

        {/* Question Panel - Only visible in normal mode */}
        {!isCodeSharing && (
          <QuestionPanel
            currentQuestion={sampleQuestions[currentQuestionIndex]}
            totalQuestions={sampleQuestions.length}
            isCollapsed={isQuestionPanelCollapsed}
            onToggleCollapse={() => setIsQuestionPanelCollapsed(!isQuestionPanelCollapsed)}
          />
        )}
      </div>
    </div>
  );
};

export default InterviewRoom;
