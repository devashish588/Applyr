import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { fetchEmailDrafts, sendEmails, sendTestEmail } from "@/api/emails"

export function useEmailDrafts() {
  return useQuery({ queryKey: ["emailDrafts"], queryFn: fetchEmailDrafts })
}

export function useSendEmails() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: sendEmails,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["emailDrafts"] })
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      queryClient.invalidateQueries({ queryKey: ["analytics"] })
    },
  })
}

export function useSendTestEmail() {
  return useMutation({ mutationFn: (to?: string) => sendTestEmail(to) })
}
