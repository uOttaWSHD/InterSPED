import { ChevronRight, ChevronLeft, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface Question {
  id: number;
  title: string;
  description: string;
  difficulty: "Easy" | "Medium" | "Hard";
  examples?: string[];
}

interface QuestionPanelProps {
  currentQuestion: Question;
  totalQuestions: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

const QuestionPanel = ({ 
  currentQuestion, 
  totalQuestions, 
  isCollapsed = false,
  onToggleCollapse 
}: QuestionPanelProps) => {
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case "Easy":
        return "text-[hsl(var(--interview-success))] bg-[hsl(var(--interview-success))]/10";
      case "Medium":
        return "text-[hsl(var(--interview-warning))] bg-[hsl(var(--interview-warning))]/10";
      case "Hard":
        return "text-destructive bg-destructive/10";
      default:
        return "text-muted-foreground bg-muted";
    }
  };

  if (isCollapsed) {
    return (
      <Button
        onClick={onToggleCollapse}
        variant="ghost"
        className="fixed right-0 top-1/2 -translate-y-1/2 h-24 w-8 rounded-l-lg rounded-r-none bg-[hsl(var(--interview-elevated))] border border-r-0 border-border hover:bg-[hsl(var(--interview-control))]"
      >
        <ChevronLeft className="w-4 h-4" />
      </Button>
    );
  }

  return (
    <div className="w-80 md:w-96 h-full bg-[hsl(var(--interview-elevated))] border-l border-border flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-primary" />
          <span className="font-semibold text-foreground">Question</span>
          <span className="text-sm text-muted-foreground">
            {currentQuestion.id} of {totalQuestions}
          </span>
        </div>
        <Button
          onClick={onToggleCollapse}
          variant="ghost"
          size="icon"
          className="w-8 h-8 hover:bg-muted"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>

      {/* Question Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Title and Difficulty */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className={`text-xs font-medium px-2 py-1 rounded-md ${getDifficultyColor(currentQuestion.difficulty)}`}>
              {currentQuestion.difficulty}
            </span>
          </div>
          <h3 className="text-lg font-bold text-foreground leading-tight">
            {currentQuestion.title}
          </h3>
        </div>

        {/* Description */}
        <div className="prose prose-invert prose-sm max-w-none">
          <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {currentQuestion.description}
          </p>
        </div>

        {/* Examples */}
        {currentQuestion.examples && currentQuestion.examples.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-foreground">Examples:</h4>
            {currentQuestion.examples.map((example, index) => (
              <div 
                key={index} 
                className="p-3 rounded-lg bg-[hsl(var(--interview-surface))] border border-border font-mono text-xs text-muted-foreground"
              >
                <pre className="whitespace-pre-wrap">{example}</pre>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Progress indicator */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-1">
          {Array.from({ length: totalQuestions }).map((_, i) => (
            <div
              key={i}
              className={`flex-1 h-1.5 rounded-full transition-colors ${
                i + 1 <= currentQuestion.id 
                  ? 'bg-primary' 
                  : 'bg-muted'
              }`}
            />
          ))}
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Progress: {Math.round((currentQuestion.id / totalQuestions) * 100)}%
        </p>
      </div>
    </div>
  );
};

export default QuestionPanel;
