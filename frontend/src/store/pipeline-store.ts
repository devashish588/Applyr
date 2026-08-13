import { create } from "zustand"
import type { PipelineEvent } from "@/types/api"

interface PipelineState {
  isRunning: boolean
  runId: string | null
  events: PipelineEvent[]
  currentStep: string
  currentPct: number
  currentMsg: string
  error: string | null

  startRun: (runId: string) => void
  addEvent: (event: PipelineEvent) => void
  reset: () => void
}

export const usePipelineStore = create<PipelineState>((set) => ({
  isRunning: false,
  runId: null,
  events: [],
  currentStep: "",
  currentPct: 0,
  currentMsg: "Ready",
  error: null,

  startRun: (runId) =>
    set({
      isRunning: true,
      runId,
      events: [],
      currentStep: "init",
      currentPct: 0,
      currentMsg: "Initializing...",
      error: null,
    }),

  addEvent: (event) =>
    set((state) => ({
      events: [...state.events, event],
      currentStep: event.step,
      currentPct: event.pct,
      currentMsg: event.msg,
      isRunning: !["done", "error", "blocked"].includes(event.step),
      error: event.step === "error" ? event.msg : state.error,
    })),

  reset: () =>
    set({
      isRunning: false,
      runId: null,
      events: [],
      currentStep: "",
      currentPct: 0,
      currentMsg: "Ready",
      error: null,
    }),
}))
