import pathlib
p = pathlib.Path("frontend/src/pages/opportunities.tsx")
txt = p.read_text(encoding="utf-8")
if "showTimeline" not in txt:
    txt = txt.replace(
        "  const [showEvidence, setShowEvidence] = useState(false)",
        "  const [showEvidence, setShowEvidence] = useState(false)\n  const [showTimeline, setShowTimeline] = useState(false)"
    )
    txt = txt.replace(
        '<button onClick={() => setShowEvidence(!showEvidence)}',
        '<button onClick={() => setShowTimeline(!showTimeline)} className="mt-1 flex w-full items-center justify-center gap-1 rounded bg-bg-secondary py-1 text-[10px] text-text-muted hover:text-text-primary">Timeline</button>\n      {showTimeline && <div className="mt-2 text-[10px] text-text-muted">Timeline via /api/applications/:id/timeline</div>}\n      <button onClick={() => setShowEvidence(!showEvidence)}'
    )
    p.write_text(txt, encoding="utf-8")
    print("added")
else:
    print("already")
