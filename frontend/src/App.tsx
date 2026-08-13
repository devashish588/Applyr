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
