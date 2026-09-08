import { useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useQueryClient } from "@tanstack/react-query"
import { runPipeline, createPipelineStream } from "@/api/pipeline"
import { usePipelineStore } from "@/store/pipeline-store"
import type { PipelineEvent } from "@/types/api"

export function usePipeline() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { isRunning, runId, currentStep, currentPct, currentMsg, events, error, startRun, addEvent, reset } = usePipelineStore()

  const start = useCallback(async () => {
    try {
      const result = await runPipeline()
      const id = result.run_id
      startRun(id)
      // Immediate navigation to dedicated status page (authoritative run_id)
      navigate(`/pipeline/${id}`)

      const es = createPipelineStream(id)
      es.onmessage = (e) => {
        try {
          const event: PipelineEvent = JSON.parse(e.data)
          addEvent(event)
          if (["done", "error", "blocked"].includes(event.step)) {
            es.close()
            queryClient.invalidateQueries({ queryKey: ["jobs"] })
            queryClient.invalidateQueries({ queryKey: ["analytics"] })
            queryClient.invalidateQueries({ queryKey: ["emailDrafts"] })
            queryClient.invalidateQueries({ queryKey: ["recruiters"] })
          }
        } catch {
          // ignore parse errors
        }
      }
      es.onerror = () => {
        // retain state, will be recovered via GET /api/pipeline/logs/:runId on refresh
        es.close()
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error || String(err)
      if (msg.includes("already running") || err?.response?.status === 409) {
        // Conflict — navigate to active run if known
        const activeId = usePipelineStore.getState().runId
        if (activeId) navigate(`/pipeline/${activeId}`)
      }
      addEvent({ step: "error", msg, pct: 0, agent: "", status: "error" })
    }
  }, [startRun, addEvent, queryClient, navigate])

  return { isRunning, runId, currentStep, currentPct, currentMsg, events, error, start, reset }
}
