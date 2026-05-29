import { useEffect, useRef } from "react";
import { useChat } from "@ai-sdk/react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Brain, Send, Loader2, Sparkles, Target, FileSearch,
  MessageSquare, Network, Bell, Zap, CheckCircle2,
  AlertCircle, Layers3,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const agentIcons: Record<string, React.ElementType> = {
  planner: Brain,
  internship: Target,
  job: Zap,
  research: FileSearch,
  resume: Sparkles,
  interview: MessageSquare,
  networking: Network,
  monitor: Bell,
  memory: Layers3,
};

const agentColors: Record<string, string> = {
  planner: "border-l-primary",
  internship: "border-l-blue-500",
  job: "border-l-amber-500",
  research: "border-l-purple-500",
  resume: "border-l-emerald-500",
  interview: "border-l-rose-500",
  networking: "border-l-cyan-500",
  monitor: "border-l-orange-500",
};

export default function AgentChat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading, data, error, stop } = useChat({
    api: `${API_BASE}/chat/stream`,
    onError: (err) => console.error("Chat error:", err),
  });

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Focus input when not loading
  useEffect(() => {
    if (!isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  // Extract live status from data stream
  const liveStatus = data?.slice(-1)?.[0] ?? null;

  return (
    <Card className="glass overflow-hidden flex flex-col h-[600px]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-primary flex items-center justify-center shadow-glow">
            <Brain className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <h2 className="font-display font-semibold text-sm">Planner Agent</h2>
            <p className="text-[11px] text-muted-foreground">
              {isLoading ? "Thinking..." : "Ready"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isLoading && (
            <Badge className="bg-primary/10 text-primary border-primary/20 gap-1.5 animate-fade-in">
              <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse-glow" />
              Streaming
            </Badge>
          )}
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-5" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 py-12">
            <div className="h-16 w-16 rounded-2xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center">
              <Brain className="h-8 w-8 text-primary" />
            </div>
            <div className="max-w-md">
              <h3 className="font-display text-xl font-bold">What's your career goal?</h3>
              <p className="text-sm text-muted-foreground mt-2">
                Describe what you're looking for and the planner will decompose it into tasks,
                dispatch specialist agents, and stream the results back in real-time.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 w-full max-w-md mt-2">
              {[
                "Find AI internships in Ahmedabad",
                "Research Stripe interviews",
                "Tailor resume for Google",
                "Network with Anthropic recruiters",
              ].map((suggestion) => (
                <Button
                  key={suggestion}
                  variant="outline"
                  size="sm"
                  className="glass text-[11px] h-auto py-2 leading-tight"
                  onClick={() => {
                    const nativeInput = inputRef.current;
                    if (nativeInput) {
                      const nativeSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype,
                        "value",
                      )?.set;
                      nativeSetter?.call(nativeInput, suggestion);
                      nativeInput.dispatchEvent(new Event("input", { bubbles: true }));
                    }
                  }}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            {messages.map((m, i) => (
              <div
                key={m.id || i}
                className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {m.role === "assistant" && (
                  <div className="h-8 w-8 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center shrink-0 mt-1">
                    <Brain className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-gradient-primary text-primary-foreground"
                      : "bg-muted/40 border border-border/40"
                  }`}
                >
                  {m.role === "assistant" ? (
                    <div className="prose prose-sm prose-invert max-w-none">
                      {m.content.split("\n").map((line, li) => {
                        // Bold headers
                        if (line.startsWith("## ")) {
                          return (
                            <h3 key={li} className="font-display font-bold text-base mt-3 mb-1">
                              {line.replace("## ", "")}
                            </h3>
                          );
                        }
                        // Bold inline
                        if (line.startsWith("**") && line.endsWith("**")) {
                          return (
                            <p key={li} className="font-semibold mb-1">
                              {line.replace(/\*\*/g, "")}
                            </p>
                          );
                        }
                        // Bullet point
                        if (line.trim().startsWith("- ")) {
                          return (
                            <div key={li} className="flex items-start gap-2 ml-2 mb-0.5">
                              <span className="text-primary mt-1.5">•</span>
                              <span>{line.trim().slice(2)}</span>
                            </div>
                          );
                        }
                        // Numbered list
                        if (/^\d+\. /.test(line.trim())) {
                          const match = line.trim().match(/^(\d+\.\s*\*\*.*)/);
                          if (match) {
                            return (
                              <div key={li} className="flex items-start gap-2 ml-2 mb-1">
                                <span className="text-primary font-bold mt-0.5 shrink-0">{line.trim().split(". ")[0]}.</span>
                                <span>{line.trim().slice(line.trim().indexOf(" ") + 1)}</span>
                              </div>
                            );
                          }
                        }
                        // Separator
                        if (line.trim() === "---") {
                          return <hr key={li} className="my-3 border-border/50" />;
                        }
                        // Regular paragraph
                        if (line.trim()) {
                          return (
                            <p key={li} className="mb-1">
                              {line}
                            </p>
                          );
                        }
                        return <br key={li} />;
                      })}
                    </div>
                  ) : (
                    <p className="text-sm">{m.content}</p>
                  )}
                </div>
                {m.role === "user" && (
                  <div className="h-8 w-8 rounded-xl bg-primary/20 border border-primary/30 flex items-center justify-center shrink-0 mt-1">
                    <span className="text-xs font-bold text-primary-foreground">U</span>
                  </div>
                )}
              </div>
            ))}

            {/* Active agent status indicator */}
            {isLoading && liveStatus && typeof liveStatus === "object" && "agent" in liveStatus && (
              <div className="flex items-center gap-3 p-3 rounded-xl bg-muted/40 border border-border/40 animate-fade-in">
                {(() => {
                  const agentName = (liveStatus as { agent?: string }).agent || "";
                  const Icon = agentIcons[agentName] || Brain;
                  return (
                    <>
                      <div className="h-8 w-8 rounded-lg bg-gradient-primary/10 border border-primary/20 flex items-center justify-center">
                        <Icon className="h-4 w-4 text-primary animate-pulse" />
                      </div>
                      <div>
                        <div className="text-sm font-medium">{agentName.charAt(0).toUpperCase() + agentName.slice(1)} Agent</div>
                        <div className="text-xs text-muted-foreground">
                          {(liveStatus as { message?: string }).message || "Processing..."}
                        </div>
                      </div>
                    </>
                  );
                })()}
              </div>
            )}

            {/* Error state */}
            {error && (
              <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-destructive">Connection Error</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {error.message || "Could not connect to the planner agent. Make sure the backend server is running."}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border/50 p-4">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <Textarea
            ref={inputRef}
            placeholder={isLoading ? "Waiting for response..." : "Describe your career goal..."}
            value={input}
            onChange={handleInputChange}
            className="flex-1 min-h-[44px] max-h-[120px] text-sm resize-none"
            disabled={isLoading}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
          <div className="flex flex-col gap-1.5">
            {isLoading ? (
              <Button type="button" variant="destructive" size="icon" className="h-11 w-11" onClick={stop}>
                <div className="h-4 w-4 rounded-sm bg-current" />
              </Button>
            ) : (
              <Button
                type="submit"
                className="h-11 w-11 bg-gradient-primary shadow-glow"
                disabled={!input.trim()}
              >
                <Send className="h-4 w-4" />
              </Button>
            )}
          </div>
        </form>
      </div>
    </Card>
  );
}
