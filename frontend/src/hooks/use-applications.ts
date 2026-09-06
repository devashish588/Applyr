import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  fetchApplications,
  fetchApplication,
  createApplication,
  updateApplicationState,
  applyApplication,
  postOutcome,
  fetchApplicationTimeline,
} from "@/api/applications"

export function useApplications() {
  return useQuery({
    queryKey: ["applications"],
    queryFn: fetchApplications,
  })
}

export function useApplication(appId: number | null) {
  return useQuery({
    queryKey: ["application", appId],
    queryFn: () => fetchApplication(appId!),
    enabled: !!appId,
  })
}

export function useApplicationTimeline(appId: number | null) {
  return useQuery({
    queryKey: ["application-timeline", appId],
    queryFn: () => fetchApplicationTimeline(appId!),
    enabled: !!appId,
  })
}

export function useCreateApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => createApplication(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] })
      qc.invalidateQueries({ queryKey: ["jobs"] })
    },
  })
}

export function useUpdateApplicationState() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ appId, state }: { appId: number; state: string }) => updateApplicationState(appId, state),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["applications"] })
      qc.invalidateQueries({ queryKey: ["application", vars.appId] })
      qc.invalidateQueries({ queryKey: ["application-timeline", vars.appId] })
    },
  })
}

export function useApplyApplication() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (appId: number) => applyApplication(appId),
    onSuccess: (_data, appId) => {
      qc.invalidateQueries({ queryKey: ["applications"] })
      qc.invalidateQueries({ queryKey: ["application", appId] })
      qc.invalidateQueries({ queryKey: ["application-timeline", appId] })
    },
  })
}

export function usePostOutcome() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ appId, outcome, reason }: { appId: number; outcome: string; reason?: string }) =>
      postOutcome(appId, outcome, reason),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["applications"] })
      qc.invalidateQueries({ queryKey: ["application", vars.appId] })
      qc.invalidateQueries({ queryKey: ["application-timeline", vars.appId] })
      qc.invalidateQueries({ queryKey: ["outcome"] })
    },
  })
}
