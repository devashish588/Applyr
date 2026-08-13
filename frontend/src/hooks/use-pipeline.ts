import { useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { runPipeline, createPipelineStream } from "@/api/pipeline"
import { usePipelineStore } from "@/store/pipeline-store"
import type { PipelineEvent } from "@/types/api"

export function usePipeline() {
  const queryClient = useQueryClient()
  const { isRunning, runId, currentStep, currentPct, currentMsg, events, error, startRun, addEvent, reset } = usePipelineStore()

  const start = useCallback(async () => {
    try {
      const result = await runPipeline()
      const id = result.run_id
      startRun(id)

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
        es.close()
        addEvent({ step: "error", msg: "Connection lost", pct: 0, agent: "", status: "error" })
      }
    } catch (err) {
      addEvent({ step: "error", msg: String(err), pct: 0, agent: "", status: "error" })
    }
  }, [startRun, addEvent, queryClient])

  return { isRunning, runId, currentStep, currentPct, currentMsg, events, error, start, reset }
}
