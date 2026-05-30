import { useState, useRef } from "react";
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
import { Upload, Sparkles, FileText, Download, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useResumeTailor, useCoverLetter } from "@/api/hooks";
import { resume } from "@/api/client";
import { toast } from "sonner";

const keywordGap = [
  { keyword: "Distributed Systems", inJob: true, inResume: false, weight: "High" },
  { keyword: "Kubernetes", inJob: true, inResume: true, weight: "Medium" },
  { keyword: "Go", inJob: true, inResume: false, weight: "Medium" },
  { keyword: "React", inJob: true, inResume: true, weight: "High" },
  { keyword: "Postgres", inJob: true, inResume: true, weight: "Low" },
  { keyword: "GraphQL", inJob: true, inResume: false, weight: "Low" },
];

export default function ResumeStudio() {
  const [tailorDialogOpen, setTailorDialogOpen] = useState(false);
  const [tailorCompany, setTailorCompany] = useState("");
  const [tailorRole, setTailorRole] = useState("software_engineering");
  const [tailorResult, setTailorResult] = useState<Record<string, unknown> | null>(null);
  const [uploadResult, setUploadResult] = useState<{ filename: string; pages: number; characters: number; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [resumesList, setResumesList] = useState([
    { id: "r1", name: "Alex_Kim_SWE_v4.pdf", role: "Software Engineering", updated: "2d ago", ats: 92 },
    { id: "r2", name: "Alex_Kim_ML_Research.pdf", role: "ML Research", updated: "5d ago", ats: 88 },
    { id: "r3", name: "Alex_Kim_Frontend.pdf", role: "Frontend / Design Eng", updated: "1w ago", ats: 95 },
  ]);

  const [coverCompany, setCoverCompany] = useState("");
  const [coverRole, setCoverRole] = useState("");
  const [coverLetter, setCoverLetter] = useState(`Dear Stripe Recruiting Team,\n\nWhen I built a payments-style ledger for my CS370 final project, I obsessed over the same idempotency primitives that power Stripe's reliability. That curiosity is why I'm applying for the New Grad SWE role.\n\nAt Meta last summer, I shipped a TypeScript service that processed 2M events/day with p99 < 40ms. I want to bring that bias for instrumented, well-tested systems to Stripe…`);

  const resumeTailor = useResumeTailor();
  const coverLetterGen = useCoverLetter();

  const handleTailor = async () => {
    if (!tailorCompany) {
      toast.error("Please enter a target company");
      return;
    }
    try {
      const result = await resumeTailor.mutateAsync({
        role_type: tailorRole,
        target_company: tailorCompany,
      });
      setTailorResult(result);
      setTailorDialogOpen(false);
      toast.success("Resume tailored!");
    } catch {
      toast.error("Failed to tailor resume");
    }
  };

  const handleGenerateCover = async () => {
    if (!coverCompany || !coverRole) {
      toast.error("Please fill in company and role");
      return;
    }
    try {
      const result = await coverLetterGen.mutateAsync({ company: coverCompany, role: coverRole });
      setCoverLetter(result.cover_letter);
      toast.success("Cover letter generated!");
    } catch {
      toast.error("Failed to generate cover letter");
    }
  };

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">Resume Studio</h1>
          <p className="text-muted-foreground mt-1">ATS analysis, keyword gaps, and AI tailoring per role.</p>
        </div>
        <div className="flex gap-2">
          <input type="file" ref={fileInputRef} className="hidden" accept=".pdf" onChange={async (e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            try {
              const result = await resume.upload(file);
              setUploadResult(result);
              setResumesList(prev => [...prev, { id: result.filename, name: result.filename, role: "Uploaded", updated: "Just now", ats: Math.min(95, Math.floor(Math.random() * 20) + 75) }]);
              toast.success("Resume uploaded!");
            } catch (err) {
              toast.error(err instanceof Error ? err.message : "Upload failed");
            }
            e.target.value = "";
          }} />
          <Button variant="outline" className="gap-2" onClick={() => fileInputRef.current?.click()}>
            <Upload className="h-4 w-4" /> Upload
          </Button>
          <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => setTailorDialogOpen(true)}>
            <Sparkles className="h-4 w-4" /> Tailor with AI
          </Button>
        </div>
      </div>

      {tailorResult && (
        <Card className="glass p-5 border-primary/30">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-display font-semibold">AI Tailoring Suggestions</h3>
            <Badge variant="outline">AI Generated</Badge>
          </div>
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-muted/30 p-4 rounded-lg overflow-auto max-h-64">
            {JSON.stringify(tailorResult, null, 2)}
          </pre>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {resumesList.map((r) => (
          <Card key={r.id} className="glass p-5 hover:shadow-glow transition">
            <div className="flex items-start gap-3 mb-4">
              <div className="h-12 w-12 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{r.name}</div>
                <div className="text-xs text-muted-foreground">{r.role} · {r.updated}</div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">ATS Score</span>
                <span className="font-display font-semibold gradient-text">{r.ats}/100</span>
              </div>
              <Progress value={r.ats} className="h-1.5" />
            </div>
            <div className="flex gap-2 mt-4">
              <Button variant="outline" size="sm" className="flex-1">Edit</Button>
              <Button variant="outline" size="sm" className="gap-1"><Download className="h-3 w-3" /></Button>
            </div>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="ats" className="space-y-4">
        <TabsList className="glass">
          <TabsTrigger value="ats">ATS Analysis</TabsTrigger>
          <TabsTrigger value="gap">Keyword Gap</TabsTrigger>
          <TabsTrigger value="cover">Cover Letter</TabsTrigger>
        </TabsList>

        <TabsContent value="ats">
          <Card className="glass p-6">
            {!tailorResult ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">Upload a resume and run ATS analysis</p>
                <Button className="bg-gradient-primary shadow-glow gap-2" onClick={() => setTailorDialogOpen(true)}>
                  <Sparkles className="h-4 w-4" /> Analyze Resume
                </Button>
              </div>
            ) : (
              <>
                {(() => {
                  const keywords = (tailorResult.ats_keywords as string[]) || [];
                  const suggestions = (tailorResult.suggestions as string[]) || [];
                  const actionItems = (tailorResult.action_items as string[]) || [];
                  const kwScore = Math.min(100, 20 + keywords.length * 16);
                  const fmtScore = uploadResult ? 85 : 70;
                  const avScore = Math.min(100, 40 + actionItems.length * 20);
                  return (
                    <>
                      <div className="grid md:grid-cols-3 gap-4 mb-6">
                        {[
                          { label: "Format", score: fmtScore, status: uploadResult ? `Parsed ${uploadResult.pages} pages` : "Upload a resume first" },
                          { label: "Keywords", score: kwScore, status: `${keywords.length} keywords detected` },
                          { label: "Action verbs", score: avScore, status: `${actionItems.length} action items identified` },
                        ].map((s) => (
                          <div key={s.label} className="p-4 rounded-xl bg-muted/30">
                            <div className="text-xs text-muted-foreground">{s.label}</div>
                            <div className="text-3xl font-display font-bold mt-1 gradient-text">{s.score}</div>
                            <div className="text-xs text-muted-foreground mt-1">{s.status}</div>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-2">
                        {keywords.slice(0, 5).map((kw: string) => (
                          <div key={kw} className="flex items-center gap-2 p-3 rounded-lg bg-muted/30 text-sm">
                            <CheckCircle2 className="h-4 w-4 text-success" />
                            Keyword match: {kw}
                          </div>
                        ))}
                        {suggestions.slice(0, 6).map((s: string, i: number) => (
                          <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-muted/30 text-sm">
                            <AlertCircle className="h-4 w-4 text-warning" />
                            {s}
                          </div>
                        ))}
                      </div>
                    </>
                  );
                })()}
              </>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="gap">
          <Card className="glass p-6">
            <div className="text-sm text-muted-foreground mb-4">Comparing your resume vs <span className="text-foreground font-medium">Stripe — SWE New Grad</span></div>
            <div className="space-y-2">
              {keywordGap.map((k) => (
                <div key={k.keyword} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                  <span className="flex-1 font-medium text-sm">{k.keyword}</span>
                  <Badge variant="outline" className="text-[10px]">{k.weight}</Badge>
                  {k.inResume ? (
                    <Badge className="bg-success/10 text-success border-success/20">In resume</Badge>
                  ) : (
                    <Badge variant="destructive" className="bg-destructive/10 text-destructive border-destructive/20">Missing</Badge>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        <TabsContent value="cover">
          <Card className="glass p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display font-semibold">Cover Letter Generator</h3>
                <p className="text-xs text-muted-foreground">Powered by Resume Agent</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Company"
                value={coverCompany}
                onChange={(e) => setCoverCompany(e.target.value)}
                className="flex-1"
              />
              <Input
                placeholder="Role"
                value={coverRole}
                onChange={(e) => setCoverRole(e.target.value)}
                className="flex-1"
              />
              <Button
                className="bg-gradient-primary shadow-glow gap-2"
                onClick={handleGenerateCover}
                disabled={coverLetterGen.isPending}
              >
                {coverLetterGen.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                Generate
              </Button>
            </div>
            <Textarea
              rows={12}
              value={coverLetter}
              onChange={(e) => setCoverLetter(e.target.value)}
              className="font-mono text-xs leading-relaxed"
            />
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={tailorDialogOpen} onOpenChange={setTailorDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tailor Resume with AI</DialogTitle>
            <DialogDescription>
              Get AI-powered suggestions to tailor your resume for a specific role.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Target Company</Label>
              <Input
                placeholder="e.g. Stripe"
                value={tailorCompany}
                onChange={(e) => setTailorCompany(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Role Type</Label>
              <Select value={tailorRole} onValueChange={setTailorRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="software_engineering">Software Engineering</SelectItem>
                  <SelectItem value="ml_research">ML Research</SelectItem>
                  <SelectItem value="frontend">Frontend / Design Eng</SelectItem>
                  <SelectItem value="backend">Backend</SelectItem>
                  <SelectItem value="fullstack">Full Stack</SelectItem>
                  <SelectItem value="devops">DevOps / SRE</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTailorDialogOpen(false)}>Cancel</Button>
            <Button
              className="bg-gradient-primary shadow-glow gap-2"
              onClick={handleTailor}
              disabled={resumeTailor.isPending}
            >
              {resumeTailor.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Tailor
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
