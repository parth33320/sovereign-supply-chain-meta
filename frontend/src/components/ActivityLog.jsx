import { useEffect, useRef } from 'react'

export default function ActivityLog({ entries, hidden,
                                      onToggle, onClear,
                                      disabled }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    if (!hidden && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [entries, hidden])

  return (
    <div className="flex flex-col mt-2">
      <div className="flex items-center gap-2 mb-2">
        <button onClick={onToggle}
                className="text-xs text-[#8b949e] hover:text-[#e6edf3]
                           border border-[#30363d] rounded px-2 py-1
                           transition-colors">
          {hidden ? 'Show Log' : 'Hide Log'}
        </button>
        <button onClick={onClear}
                disabled={disabled}
                className="text-xs text-[#8b949e] hover:text-[#e6edf3]
                           border border-[#30363d] rounded px-2 py-1
                           transition-colors disabled:opacity-30
                           disabled:cursor-not-allowed">
          Clear
        </button>
      </div>

      {hidden ? (
        <p className="text-xs text-[#8b949e]">
          ⚡ Activity Log ({entries.length} entries) —
          click Show Log to expand
        </p>
      ) : (
        <div className="h-40 overflow-y-auto border border-[#30363d]
                        rounded-lg bg-[#0d1117] p-3 font-mono
                        text-xs text-[#8b949e] space-y-1">
          {entries.map((e, i) => (
            <div key={i} className="truncate">
              [{e.ts}] {e.icon} {e.source}: {e.msg}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
