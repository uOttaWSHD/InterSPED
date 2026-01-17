import { useState } from "react";
import { ChevronDown, Play, RotateCcw, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const languages = [
  { id: "javascript", name: "JavaScript", extension: ".js" },
  { id: "python", name: "Python", extension: ".py" },
  { id: "java", name: "Java", extension: ".java" },
  { id: "cpp", name: "C++", extension: ".cpp" },
  { id: "typescript", name: "TypeScript", extension: ".ts" },
];

const defaultCode: Record<string, string> = {
  javascript: `function solution(input) {
  // Write your solution here
  
  return result;
}

// Test your solution
console.log(solution([1, 2, 3]));`,
  python: `def solution(input):
    # Write your solution here
    
    return result

# Test your solution
print(solution([1, 2, 3]))`,
  java: `class Solution {
    public static void main(String[] args) {
        // Write your solution here
        
    }
    
    public static int solution(int[] input) {
        return 0;
    }
}`,
  cpp: `#include <iostream>
#include <vector>
using namespace std;

int solution(vector<int>& input) {
    // Write your solution here
    
    return 0;
}

int main() {
    vector<int> test = {1, 2, 3};
    cout << solution(test) << endl;
    return 0;
}`,
  typescript: `function solution(input: number[]): number {
  // Write your solution here
  
  return 0;
}

// Test your solution
console.log(solution([1, 2, 3]));`,
};

const CodeEditor = () => {
  const [selectedLanguage, setSelectedLanguage] = useState(languages[0]);
  const [code, setCode] = useState(defaultCode.javascript);
  const [copied, setCopied] = useState(false);
  const [output, setOutput] = useState<string | null>(null);

  const handleLanguageChange = (lang: typeof languages[0]) => {
    setSelectedLanguage(lang);
    setCode(defaultCode[lang.id]);
    setOutput(null);
  };

  const handleReset = () => {
    setCode(defaultCode[selectedLanguage.id]);
    setOutput(null);
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRun = () => {
    // Simulated output for demo
    setOutput("// Output will appear here\n> Running code...\n> Execution complete.");
  };

  const lineNumbers = code.split('\n').length;

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--interview-surface))] rounded-xl overflow-hidden border border-border">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[hsl(var(--interview-elevated))] border-b border-border">
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                className="h-8 px-3 text-sm bg-[hsl(var(--interview-control))] hover:bg-[hsl(var(--interview-control-hover))]"
              >
                {selectedLanguage.name}
                <ChevronDown className="w-4 h-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="bg-card border-border">
              {languages.map((lang) => (
                <DropdownMenuItem
                  key={lang.id}
                  onClick={() => handleLanguageChange(lang)}
                  className="cursor-pointer"
                >
                  {lang.name}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <span className="text-xs text-muted-foreground">
            main{selectedLanguage.extension}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-8 px-2 text-muted-foreground hover:text-foreground"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="h-8 px-2 text-muted-foreground hover:text-foreground"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button
            size="sm"
            onClick={handleRun}
            className="h-8 px-4 bg-[hsl(var(--interview-success))] hover:bg-[hsl(var(--interview-success))]/90 text-white"
          >
            <Play className="w-4 h-4 mr-1" />
            Run
          </Button>
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Line Numbers */}
        <div className="w-12 py-4 bg-[hsl(var(--interview-surface))] border-r border-border/50 select-none">
          <div className="flex flex-col items-end pr-3 font-mono text-xs text-muted-foreground/50">
            {Array.from({ length: lineNumbers }).map((_, i) => (
              <div key={i} className="leading-6">{i + 1}</div>
            ))}
          </div>
        </div>

        {/* Code Input */}
        <div className="flex-1 overflow-auto">
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full h-full p-4 font-mono text-sm leading-6 bg-transparent text-foreground resize-none focus:outline-none"
            spellCheck={false}
            placeholder="// Write your code here..."
          />
        </div>
      </div>

      {/* Output Panel */}
      {output && (
        <div className="h-32 border-t border-border bg-[hsl(var(--interview-elevated))]">
          <div className="flex items-center justify-between px-4 py-2 border-b border-border/50">
            <span className="text-xs font-medium text-muted-foreground">Output</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOutput(null)}
              className="h-6 px-2 text-xs text-muted-foreground"
            >
              Clear
            </Button>
          </div>
          <div className="p-4 font-mono text-xs text-muted-foreground overflow-auto h-[calc(100%-2.5rem)]">
            <pre>{output}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default CodeEditor;
