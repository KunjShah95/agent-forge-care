import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Play, Mic, Trophy, Clock, BookOpen, Loader2, MessageSquare, Send, Sparkles } from "lucide-react";
import { useInterviewPrep, useInterviewSessions, useCreateInterviewSession, useInterviewFeedback } from "@/api/hooks";
import { toast } from "sonner";

export default function InterviewPrep() {
  const navigate = useNavigate();
  const [category, setCategory] = useState<string>("Behavioral");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [type, setType] = useState("behavioral");
  const [generatedQuestions, setGeneratedQuestions] = useState<{ skill: string; question: string; type: string; tips: string }[]>([]);
  const [generatedTips, setGeneratedTips] = useState<string[]>([]);
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);
  const [userAnswer, setUserAnswer] = useState("");
  const [feedback, setFeedback] = useState<{ feedback: string; score?: number; strengths?: string[]; improvements?: string[] } | null>(null);
  const [isGettingFeedback, setIsGettingFeedback] = useState(false);

  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      toast.success("Recording started... Speak now.");
    } catch (error) {
      console.error("Error accessing microphone:", error);
      toast.error("Could not access microphone. Please check permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      toast.success("Recording saved locally!");
    }
  };

  const handleQuestionClick = (q: string) => {
    if (isRecording) {
      stopRecording();
    }
    setAudioUrl(null);

    if (selectedQuestion === q) {
      setSelectedQuestion(null);
      setUserAnswer("");
      setFeedback(null);
    } else {
      setSelectedQuestion(q);
      setUserAnswer("");
      setFeedback(null);
    }
  };

  const interviewPrep = useInterviewPrep();
  const { data: sessionsData } = useInterviewSessions();
  const createSession = useCreateInterviewSession();
  const interviewFeedback = useInterviewFeedback();
  const sessions = sessionsData?.items ?? [];
  const [showAllSessions, setShowAllSessions] = useState(false);
  const SESSION_PREVIEW_COUNT = 5;
  const displaySessions = showAllSessions ? sessions : sessions.slice(0, SESSION_PREVIEW_COUNT);

  const handleGenerate = async () => {
    if (!company || !role) {
      toast.error("Please fill in company and role");
      return;
    }
    try {
      const result = await interviewPrep.mutateAsync({ company, role, type });
      setGeneratedQuestions(result.questions);
      setGeneratedTips(result.prep_tips);
      setCategory("Generated");
      setDialogOpen(false);
      toast.success("Questions generated!");
    } catch {
      toast.error("Failed to generate questions");
    }
  };

  // handleQuestionClick has been moved above

  const handleGetFeedback = async () => {
    if (!userAnswer.trim()) {
      toast.error("Please write an answer first");
      return;
    }
    setIsGettingFeedback(true);
    try {
      const result = await interviewFeedback.mutateAsync({
        question: selectedQuestion || "",
        answer: userAnswer,
        company,
        role,
      });
      setFeedback(result);
    } catch {
      toast.error("Failed to get feedback");
    } finally {
      setIsGettingFeedback(false);
    }
  };

  const statsByCategory = (() => {
    const catMap: Record<string, { done: number; total: number; score: number }> = {
      Behavioral: { done: 0, total: 12, score: 0 },
      Technical: { done: 0, total: 8, score: 0 },
      "System Design": { done: 0, total: 4, score: 0 },
      "ML/AI": { done: 0, total: 6, score: 0 },
    };
    for (const s of sessions) {
      const cat = s.type === "behavioral" ? "Behavioral" : s.type === "technical" ? "Technical" : s.type === "system_design" ? "System Design" : "ML/AI";
      if (catMap[cat]) {
        catMap[cat].done++;
        catMap[cat].score = s.score || catMap[cat].score;
      }
    }
    return Object.entries(catMap).map(([name, v]) => ({ name, ...v }));
  })();

  const displayQuestions = generatedQuestions.length > 0
    ? { Generated: generatedQuestions.map(q => q.question) }
    : {};

  return (
    <div className="space-y-6 max-w-[1400px] relative">
      {/* Animated grid background */}
      <div className="fixed inset-0 animated-grid opacity-40 pointer-events-none" />
      <div className="fixed inset-0 bg-beams opacity-20 pointer-events-none" />
      <div className="fixed top-1/4 right-1/4 w-72 h-72 rounded-full bg-gradient-1 opacity-[0.03] blur-3xl animate-float-slow pointer-events-none" />
      <div className="fixed bottom-1/3 left-1/4 w-56 h-56 rounded-full bg-gradient-3 opacity-[0.03] blur-3xl animate-float pointer-events-none" />

      <div className="relative flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Interview Prep</h1>
          <p className="text-muted-foreground mt-1">Mock interviews, question banks, and skill tracking.</p>
        </div>
        <Button className="bg-gradient-1 shadow-glow gap-2" onClick={() => setDialogOpen(true)}>
          <Mic className="h-4 w-4" /> Start mock interview
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statsByCategory.map((c) => (
            <Card key={c.name} className="bento-card p-5">
              <div className="text-xs text-muted-foreground">{c.name}</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-display font-bold">{c.done}</span>
                <span className="text-xs text-muted-foreground">/ {c.total}</span>
              </div>
              <Progress value={c.total > 0 ? (c.done / c.total) * 100 : 0} className="h-1.5 mt-3" />
              <div className="flex items-center justify-between mt-2 text-xs">
                <span className="text-muted-foreground">Avg score</span>
                <span className="font-display font-semibold gradient-text">{c.score}%</span>
              </div>
            </Card>
          ))}
      </div>

      {generatedTips.length > 0 && (
        <Card className="bento-card p-5 border-primary/30">
          <h3 className="font-display font-semibold mb-2">AI Tips for {company} — {role}</h3>
          <ul className="space-y-1">
            {generatedTips.map((tip, i) => (
              <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                <span className="text-primary mt-0.5">•</span> {tip}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="bento-card p-6 lg:col-span-2">
          <h2 className="font-display font-semibold mb-4">Question Bank</h2>
          {Object.keys(displayQuestions).length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Generate interview questions to get started.
            </div>
          ) : (
          <Tabs value={category} onValueChange={setCategory}>
            <TabsList className="glass">
              {Object.keys(displayQuestions).map((c) => (
                <TabsTrigger key={c} value={c}>{c}</TabsTrigger>
              ))}
            </TabsList>
            {Object.entries(displayQuestions).map(([cat, qs]) => (
              <TabsContent key={cat} value={cat} className="mt-4 space-y-2">
                {qs.map((q, i) => (
                  <div key={i}>
                    <div
                      className={`flex items-center gap-3 p-4 rounded-lg transition cursor-pointer ${
                        selectedQuestion === q ? "bg-primary/10 border border-primary/30" : "bg-muted/30 hover:bg-muted/50"
                      }`}
                      onClick={() => handleQuestionClick(q)}
                    >
                      <div className="h-8 w-8 rounded-lg bg-gradient-1/10 border border-primary/20 flex items-center justify-center text-xs font-display font-bold text-primary">
                        Q{i + 1}
                      </div>
                      <div className="flex-1 text-sm">{q}</div>
                      <div className="flex items-center gap-1">
                        {selectedQuestion === q && <MessageSquare className="h-3 w-3 text-primary" />}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="gap-1"
                          onClick={(e) => { e.stopPropagation(); navigate("/app/agents"); }}
                        >
                          <Play className="h-3 w-3" /> Practice
                        </Button>
                      </div>
                    </div>
                    {selectedQuestion === q && (
                      <div className="ml-12 mt-2 space-y-3 p-4 rounded-lg bg-muted/20 border border-muted/40">
                        <div className="flex flex-col gap-3 p-4 rounded-lg bg-background/40 border border-muted/30">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                              <Mic className="h-3.5 w-3.5 text-primary animate-pulse" /> Audio Practice
                            </span>
                            {isRecording && (
                              <span className="flex items-center gap-1 text-xs text-red-500 animate-pulse font-medium">
                                <span className="h-2 w-2 rounded-full bg-red-500" />
                                Recording...
                              </span>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-3">
                            {!isRecording ? (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="gap-2 border-red-500/20 hover:bg-red-500/10 hover:text-red-400 text-xs transition-all duration-200"
                                onClick={startRecording}
                              >
                                <Play className="h-3 w-3 fill-red-500 text-red-500" />
                                Record Answer
                              </Button>
                            ) : (
                              <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                className="gap-2 animate-pulse text-xs"
                                onClick={stopRecording}
                              >
                                <span className="h-2.5 w-2.5 rounded-full bg-white animate-ping" />
                                Stop Recording
                              </Button>
                            )}

                            {audioUrl && (
                              <div className="flex-1 flex items-center gap-3">
                                <audio src={audioUrl} controls className="h-8 max-w-[240px] rounded-md" />
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="text-xs text-muted-foreground hover:text-destructive h-8 px-2"
                                  onClick={() => setAudioUrl(null)}
                                >
                                  Clear
                                </Button>
                              </div>
                            )}
                          </div>
                        </div>

                        <Textarea
                          placeholder="Type your answer here..."
                          value={userAnswer}
                          onChange={(e) => setUserAnswer(e.target.value)}
                          rows={5}
                          className="text-sm bg-background/30"
                        />
                        <div className="flex items-center gap-3">
                          <Button
                            size="sm"
                            className="gap-2 bg-gradient-1 shadow-glow"
                            onClick={handleGetFeedback}
                            disabled={isGettingFeedback || !userAnswer.trim()}
                          >
                            {isGettingFeedback ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Send className="h-3 w-3" />
                            )}
                            Get Feedback
                          </Button>
                          {feedback && (
                            <span className="text-xs text-muted-foreground">
                              <Sparkles className="h-3 w-3 inline mr-1 text-primary" />
                              AI feedback generated
                            </span>
                          )}
                        </div>
                        {feedback && (
                          <div className="flex items-start gap-3 p-4 rounded-lg bg-primary/5 border border-primary/10">
                            <Sparkles className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold text-primary">AI Feedback</span>
                                {feedback.score != null && (
                                  <span className={`text-xs font-bold ${feedback.score >= 70 ? "text-success" : feedback.score >= 40 ? "text-warning" : "text-destructive"}`}>
                                    Score: {feedback.score}/100
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground">{feedback.feedback}</p>
                              {feedback.strengths && feedback.strengths.length > 0 && (
                                <div className="text-xs"><span className="text-success font-medium">Strengths:</span> {feedback.strengths.join(", ")}</div>
                              )}
                              {feedback.improvements && feedback.improvements.length > 0 && (
                                <div className="text-xs"><span className="text-warning font-medium">Improve:</span> {feedback.improvements.join(", ")}</div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </TabsContent>
            ))}
          </Tabs>
          )}
        </Card>

        <Card className="bento-card p-6">
          <h2 className="font-display font-semibold mb-4">Recent Sessions</h2>
          <div className="space-y-3">
            {sessions.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">No sessions yet. Start a mock interview to build your history.</div>
            ) : displaySessions.map((s) => (
              <div key={s.id} className="p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition cursor-pointer">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{s.company}</span>
                  <Badge variant="outline" className="text-[10px]">{s.type}</Badge>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {s.duration}</span>
                  <span className="flex items-center gap-1"><Trophy className="h-3 w-3" /> {s.score}%</span>
                  <span className="ml-auto">{s.date}</span>
                </div>
              </div>
            ))}
          </div>
          {!showAllSessions && sessions.length > SESSION_PREVIEW_COUNT && (
            <Button variant="outline" size="sm" className="w-full mt-4 gap-2" onClick={() => setShowAllSessions(true)}>
              <BookOpen className="h-3 w-3" /> View all {sessions.length} sessions
            </Button>
          )}
        </Card>
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Interview Questions</DialogTitle>
            <DialogDescription>
              AI will generate tailored questions based on your target company and role.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Company</Label>
              <Input placeholder="e.g. Stripe" value={company} onChange={(e) => setCompany(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Input placeholder="e.g. Senior Software Engineer" value={role} onChange={(e) => setRole(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Interview Type</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="behavioral">Behavioral</SelectItem>
                  <SelectItem value="technical">Technical</SelectItem>
                  <SelectItem value="system_design">System Design</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button className="bg-gradient-1 shadow-glow gap-2" onClick={handleGenerate} disabled={interviewPrep.isPending}>
              {interviewPrep.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Generate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
