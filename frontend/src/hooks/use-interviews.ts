import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  fetchInterviews,
  createInterview,
  completeInterview,
  cancelInterview,
  fetchInterviewPrep,
  fetchFollowUps,
  createFollowUp,
  reviewFollowUp,
  approveFollowUp,
  sendFollowUp,
} from "@/api/interviews"

export function useInterviews(appId: number | null) {
  return useQuery({
    queryKey: ["interviews", appId],
    queryFn: () => fetchInterviews(appId!),
    enabled: !!appId,
  })
}

export function useCreateInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ appId, payload }: { appId: number; payload: any }) => createInterview(appId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["interviews", vars.appId] })
      qc.invalidateQueries({ queryKey: ["application-timeline", vars.appId] })
    },
  })
}

export function useCompleteInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }: { id: number; notes?: string }) => completeInterview(id, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["interviews"] })
    },
  })
}

export function useCancelInterview() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelInterview(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["interviews"] }),
  })
}

export function useInterviewPrep(appId: number | null) {
  return useQuery({
    queryKey: ["interview-prep", appId],
    queryFn: () => fetchInterviewPrep(appId!),
    enabled: !!appId,
  })
}

export function useFollowUps(appId: number | null) {
  return useQuery({
    queryKey: ["followups", appId],
    queryFn: () => fetchFollowUps(appId!),
    enabled: !!appId,
  })
}

export function useCreateFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ appId, payload }: { appId: number; payload: any }) => createFollowUp(appId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["followups", vars.appId] })
      qc.invalidateQueries({ queryKey: ["application-timeline", vars.appId] })
    },
  })
}

export function useReviewFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => reviewFollowUp(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["followups"] }),
  })
}

export function useApproveFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => approveFollowUp(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["followups"] }),
  })
}

export function useSendFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => sendFollowUp(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["followups"] }),
  })
}
