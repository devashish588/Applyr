import { useQuery } from "@tanstack/react-query"
import { fetchRecruiters } from "@/api/recruiters"

export function useRecruiters() {
  return useQuery({ queryKey: ["recruiters"], queryFn: fetchRecruiters })
}
