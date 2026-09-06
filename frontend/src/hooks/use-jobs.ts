import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchJobs, fetchJobDetail, updateJobCompany } from "@/api/jobs"

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: fetchJobs,
  })
}

export function useJobDetail(jobId: number | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => fetchJobDetail(jobId!),
    enabled: !!jobId,
  })
}

export function useUpdateJobCompany() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ jobId, company }: { jobId: number; company: string }) =>
      updateJobCompany(jobId, company),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

export function usePrioritizedJobs(enabled: boolean) {
  return useQuery({
    queryKey: ["jobs-prioritized"],
    queryFn: async () => {
      const { fetchPrioritizedJobs } = await import("@/api/jobs")
      return fetchPrioritizedJobs()
    },
    enabled,
  })
}
