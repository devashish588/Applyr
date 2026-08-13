import { useQuery } from "@tanstack/react-query"
import { fetchConfig, fetchSetupStatus, fetchProfile, fetchGmailStatus } from "@/api/settings"

export function useConfig() {
  return useQuery({ queryKey: ["config"], queryFn: fetchConfig })
}

export function useSetupStatus() {
  return useQuery({ queryKey: ["setupStatus"], queryFn: fetchSetupStatus })
}

export function useProfile() {
  return useQuery({ queryKey: ["profile"], queryFn: fetchProfile })
}

export function useGmailStatus() {
  return useQuery({ queryKey: ["gmailStatus"], queryFn: fetchGmailStatus })
}
