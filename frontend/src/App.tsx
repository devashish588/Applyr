import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AppLayout } from "@/components/layout/app-layout"
import DashboardPage from "@/pages/dashboard"
import DiscoverJobsPage from "@/pages/discover-jobs"
import OpportunitiesPage from "@/pages/opportunities"
import PipelinePage from "@/pages/pipeline"
import ResumeStudioPage from "@/pages/resume-studio"
import NetworkingPage from "@/pages/networking"
import InboxPage from "@/pages/inbox"
import AnalyticsPage from "@/pages/analytics"
import SettingsPage from "@/pages/settings"
import CopilotPage from "@/pages/copilot"
import InterviewPage from "@/pages/interview"
import StudioPage from "@/pages/studio"
import JobDetailPage from "@/pages/job-detail"
import ApplicationDetailPage from "@/pages/application-detail"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/discover" element={<DiscoverJobsPage />} />
            <Route path="/opportunities" element={<OpportunitiesPage />} />
            <Route path="/pipeline" element={<PipelinePage />} />
            <Route path="/resume" element={<ResumeStudioPage />} />
            <Route path="/copilot" element={<CopilotPage />} />
            <Route path="/interview" element={<InterviewPage />} />
            <Route path="/studio/:jobId" element={<StudioPage />} />
            <Route path="/jobs/:jobId" element={<JobDetailPage />} />
            <Route path="/applications/:appId" element={<ApplicationDetailPage />} />
            <Route path="/network" element={<NetworkingPage />} />
            <Route path="/inbox" element={<InboxPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

