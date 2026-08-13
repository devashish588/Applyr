import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchResumeStatus, fetchParsedResume, fetchResumeSkills, fetchResumeRoles, fetchResumeExperience, fetchResumeEducation, fetchResumeHealth, uploadResume } from "@/api/resume"

export function useResumeStatus() {
  return useQuery({ queryKey: ["resumeStatus"], queryFn: fetchResumeStatus })
}

export function useParsedResume() {
  return useQuery({ queryKey: ["parsedResume"], queryFn: fetchParsedResume })
}

export function useResumeSkills() {
  return useQuery({ queryKey: ["resumeSkills"], queryFn: fetchResumeSkills })
}

export function useResumeRoles() {
  return useQuery({ queryKey: ["resumeRoles"], queryFn: fetchResumeRoles })
}

export function useResumeExperience() {
  return useQuery({ queryKey: ["resumeExperience"], queryFn: fetchResumeExperience })
}

export function useResumeEducation() {
  return useQuery({ queryKey: ["resumeEducation"], queryFn: fetchResumeEducation })
}

export function useResumeHealth() {
  return useQuery({ queryKey: ["resumeHealth"], queryFn: fetchResumeHealth })
}

export function useUploadResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadResume,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resumeStatus"] })
      queryClient.invalidateQueries({ queryKey: ["parsedResume"] })
      queryClient.invalidateQueries({ queryKey: ["resumeSkills"] })
      queryClient.invalidateQueries({ queryKey: ["resumeRoles"] })
      queryClient.invalidateQueries({ queryKey: ["analytics"] })
    },
  })
}
