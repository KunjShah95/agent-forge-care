import { useState, useRef, useEffect } from "react";
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
import { Upload, Sparkles, FileText, CheckCircle2, AlertCircle, Loader2, Trash2 } from "lucide-react";
import { useResumeTailor, useCoverLetter, useResumes, useDeleteResume, useResumeAnalysis } from "@/api/hooks";
import { resume } from "@/api/client";
import { toast } from "sonner";
export default function ResumeStudio() {
  const [tailorDialogOpen, setTailorDialogOpen] = useState(false);
  const [tailorCompany, setTailorCompany] = useState("");
  const [tailorRole, setTailorRole] = useState("software_engineering");
  const [tailorResult, setTailorResult] = useState<{ suggestions: string[]; action_items: string[]; ats_keywords: string[]; summary: string; message: string } | null>(null);
  const [uploadResult, setUploadResult] = useState<{ filename: string; pages: number; characters: number; text: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: resumesData } = useResumes();
  const deleteResume = useDeleteResume();
  const resumesList = resumesData?.items ?? [];

  const [activeTab, setActiveTab] = useState("ats");
  const { data: atsData } = useResumeAnalysis(activeTab === "ats" && uploadResult !== null);

  const [coverCompany, setCoverCompany] = useState("");
  const [coverRole, setCoverRole] = useState("");
  const [coverLetter, setCoverLetter] = useState("");

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
          {tailorResult.summary && (
            <div className="p-4 rounded-lg bg-primary/5 border border-primary/10 mb-4">
              <p className="text-sm text-muted-foreground">{tailorResult.summary}</p>
            </div>
          )}
          <div className="grid md:grid-cols-2 gap-4">
            {tailorResult.suggestions && tailorResult.suggestions.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-primary mb-2">Suggestions</h4>
                <ul className="space-y-2">
                  {tailorResult.suggestions.slice(0, 5).map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="text-primary mt-1.5 h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {tailorResult.action_items && tailorResult.action_items.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-warning mb-2">Action Items</h4>
                <ul className="space-y-2">
                  {tailorResult.action_items.slice(0, 5).map((a, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                      <span className="text-warning mt-1.5 h-1.5 w-1.5 rounded-full bg-warning flex-shrink-0" />
                      {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </Card>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {resumesList.map((r) => (
          <Card key={r.filename} className="glass p-5 hover:shadow-glow transition group">
            <div className="flex items-start gap-3 mb-4">
              <div className="h-12 w-12 rounded-xl bg-gradient-primary/10 border border-primary/20 flex items-center justify-center">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{r.filename}</div>
                <div className="text-xs text-muted-foreground">{r.pages} pages · {r.characters.toLocaleString()} chars</div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Parsed</span>
                <span className="font-display font-semibold gradient-text">{r.characters > 0 ? "Ready" : "Empty"}</span>
              </div>
              <Progress value={r.characters > 0 ? 100 : 0} className="h-1.5" />
            </div>
            <div className="flex gap-2 mt-4">
              <Button variant="outline" size="sm" className="flex-1" onClick={() => deleteResume.mutate(r.filename, {
                onSuccess: () => toast.success("Resume deleted"),
                onError: () => toast.error("Failed to delete resume"),
              })} disabled={deleteResume.isPending}>
                <Trash2 className="h-3 w-3 mr-1" /> Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="glass">
          <TabsTrigger value="ats">ATS Analysis</TabsTrigger>
          <TabsTrigger value="gap">Keyword Gap</TabsTrigger>
          <TabsTrigger value="cover">Cover Letter</TabsTrigger>
        </TabsList>

        <TabsContent value="ats">
          <Card className="glass p-6">
            {!uploadResult ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">Upload a resume to see ATS analysis</p>
                <Button variant="outline" className="gap-2" onClick={() => fileInputRef.current?.click()}>
                  <Upload className="h-4 w-4" /> Upload Resume
                </Button>
              </div>
            ) : !atsData ? (
              <div className="text-center py-12">
                <Loader2 className="h-8 w-8 mx-auto text-muted-foreground animate-spin mb-4" />
                <p className="text-muted-foreground">Analyzing resume...</p>
              </div>
            ) : (
              <>
                <div className="grid md:grid-cols-3 gap-4 mb-6">
                  {[
                    { label: "Format", score: atsData.format_score, status: `Structure score` },
                    { label: "Keywords", score: atsData.keyword_score, status: `${atsData.present_keywords.length} of ${atsData.present_keywords.length + atsData.missing_keywords.length} skills matched` },
                    { label: "Action verbs", score: atsData.action_verb_score, status: `Verb usage score` },
                  ].map((s) => (
                    <div key={s.label} className="p-4 rounded-xl bg-muted/30">
                      <div className="text-xs text-muted-foreground">{s.label}</div>
                      <div className="text-3xl font-display font-bold mt-1 gradient-text">{s.score}</div>
                      <div className="text-xs text-muted-foreground mt-1">{s.status}</div>
                    </div>
                  ))}
                </div>
                {atsData.summary && (
                  <div className="p-4 rounded-lg bg-primary/5 border border-primary/10 mb-4">
                    <p className="text-sm text-muted-foreground">{atsData.summary}</p>
                  </div>
                )}
                <div className="space-y-2">
                  {atsData.present_keywords.slice(0, 5).map((kw: string) => (
                    <div key={kw} className="flex items-center gap-2 p-3 rounded-lg bg-muted/30 text-sm">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      {kw}
                    </div>
                  ))}
                  {atsData.suggestions.map((s: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 p-3 rounded-lg bg-muted/30 text-sm">
                      <AlertCircle className="h-4 w-4 text-warning" />
                      {s}
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </TabsContent>

        <TabsContent value="gap">
          <Card className="glass p-6">
            {!atsData ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">Upload a resume and view ATS analysis to see keyword gaps</p>
              </div>
            ) : (
              <>
                <div className="text-sm text-muted-foreground mb-4">
                  {atsData.missing_keywords.length > 0
                    ? `${atsData.missing_keywords.length} skills missing from your resume`
                    : `All profile skills found in resume`}
                </div>
                <div className="space-y-2">
                  {atsData.present_keywords.map((kw) => (
                    <div key={kw} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      <span className="flex-1 font-medium text-sm">{kw}</span>
                      <Badge className="bg-success/10 text-success border-success/20">Present</Badge>
                    </div>
                  ))}
                  {atsData.missing_keywords.map((kw) => (
                    <div key={kw} className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
                      <AlertCircle className="h-4 w-4 text-destructive" />
                      <span className="flex-1 font-medium text-sm">{kw}</span>
                      <Badge variant="destructive">Missing</Badge>
                    </div>
                  ))}
                </div>
              </>
            )}
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
