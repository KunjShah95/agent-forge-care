import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/lib/auth-context";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Opportunities from "./pages/Opportunities";
import Applications from "./pages/Applications";
import ResumeStudio from "./pages/ResumeStudio";
import InterviewPrep from "./pages/InterviewPrep";
import ResearchCenter from "./pages/ResearchCenter";
import NetworkingHub from "./pages/NetworkingHub";
import OpportunityMonitor from "./pages/OpportunityMonitor";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import AgentConsole from "./pages/AgentConsole";
import TaskQueue from "./pages/TaskQueue";
import MemoryViewer from "./pages/MemoryViewer";
import NotFound from "./pages/NotFound";
import ErrorBoundary from "@/components/ErrorBoundary";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <ThemeProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/onboarding" element={<Onboarding />} />
                <Route
                  path="/app"
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route index element={<Dashboard />} />
                  <Route path="opportunities" element={<Opportunities />} />
                  <Route path="applications" element={<Applications />} />
                  <Route path="resume" element={<ResumeStudio />} />
                  <Route path="interview" element={<InterviewPrep />} />
                  <Route path="research" element={<ResearchCenter />} />
                  <Route path="networking" element={<NetworkingHub />} />
                  <Route path="monitor" element={<OpportunityMonitor />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="agents" element={<AgentConsole />} />
                  <Route path="tasks" element={<TaskQueue />} />
                  <Route path="memory" element={<MemoryViewer />} />
                  <Route path="settings" element={<Settings />} />
                </Route>
                <Route path="/dashboard" element={<Navigate to="/app" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </ErrorBoundary>
          </BrowserRouter>
        </TooltipProvider>
      </ThemeProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
