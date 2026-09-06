import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchStudio, generateStudio } from "@/api/studio"

export function useStudio(jobId: number | null) {
  return useQuery({
    queryKey: ["studio", jobId],
    queryFn: () => fetchStudio(jobId!),
    enabled: !!jobId,
    staleTime: 60_000,
  })
}

export function useGenerateStudio() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (jobId: number) => generateStudio(jobId),
    onSuccess: (_data, jobId) => {
      qc.invalidateQueries({ queryKey: ["studio", jobId] })
    },
  })
}
