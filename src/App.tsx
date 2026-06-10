import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { AuthProvider } from "@/lib/auth-context";
import ProtectedRoute from "@/components/ProtectedRoute";
import AppLayout from "@/components/AppLayout";
const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Opportunities = lazy(() => import("./pages/Opportunities"));
const Applications = lazy(() => import("./pages/Applications"));
const ResumeStudio = lazy(() => import("./pages/ResumeStudio"));
const InterviewPrep = lazy(() => import("./pages/InterviewPrep"));
const ResearchCenter = lazy(() => import("./pages/ResearchCenter"));
const NetworkingHub = lazy(() => import("./pages/NetworkingHub"));
const OpportunityMonitor = lazy(() => import("./pages/OpportunityMonitor"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Settings = lazy(() => import("./pages/Settings"));
const AgentConsole = lazy(() => import("./pages/AgentConsole"));
const TaskQueue = lazy(() => import("./pages/TaskQueue"));
const MemoryViewer = lazy(() => import("./pages/MemoryViewer"));
const CareerCoach = lazy(() => import("./pages/CareerCoach"));
const NotFound = lazy(() => import("./pages/NotFound"));
import { HelmetProvider } from "react-helmet-async";
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
            <HelmetProvider>
            <ErrorBoundary>
              <Suspense fallback={<div className="flex items-center justify-center min-h-screen">Loading...</div>}>
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
                  <Route path="coach" element={<CareerCoach />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="agents" element={<AgentConsole />} />
                  <Route path="tasks" element={<TaskQueue />} />
                  <Route path="memory" element={<MemoryViewer />} />
                  <Route path="settings" element={<Settings />} />
                </Route>
                <Route path="/dashboard" element={<Navigate to="/app" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
              </Suspense>
            </ErrorBoundary>
            </HelmetProvider>
          </BrowserRouter>
        </TooltipProvider>
      </ThemeProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
