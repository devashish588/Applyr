import { useQuery } from "@tanstack/react-query"
import { fetchAnalytics, fetchSystemStatus, fetchEmailStatus, fetchOutcomeOverview, fetchOutcomeInsights } from "@/api/dashboard"
import { fetchResumeStatus } from "@/api/resume"

export function useAnalytics() {
  return useQuery({
    queryKey: ["analytics"],
    queryFn: fetchAnalytics,
    refetchInterval: 30000,
  })
}

export function useSystemStatus() {
  return useQuery({
    queryKey: ["systemStatus"],
    queryFn: fetchSystemStatus,
    refetchInterval: 30000,
  })
}

export function useEmailStatus() {
  return useQuery({
    queryKey: ["emailStatus"],
    queryFn: fetchEmailStatus,
  })
}

export function useOutcomeOverview() {
  return useQuery({
    queryKey: ["outcomeOverview"],
    queryFn: fetchOutcomeOverview,
    refetchInterval: 30000,
  })
}

export function useOutcomeInsights() {
  return useQuery({
    queryKey: ["outcomeInsights"],
    queryFn: fetchOutcomeInsights,
    refetchInterval: 30000,
  })
}

export function useDashboard() {
  const analytics = useAnalytics()
  const status = useSystemStatus()
  const resume = useQuery({
    queryKey: ["resumeStatus"],
    queryFn: fetchResumeStatus,
  })
  const email = useEmailStatus()

  return {
    analytics: analytics.data,
    status: status.data,
    resume: resume.data,
    email: email.data,
    isLoading: analytics.isLoading || status.isLoading || resume.isLoading,
    error: analytics.error || status.error,
  }
}
