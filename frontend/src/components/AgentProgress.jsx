import React, { useState, useEffect } from 'react'

const PROGRESS_STEPS = [
  "Scanning disruption feeds",
  "Fetching inventory from supply-chain-db",
  "Running demand forecast",
  "Initiating A2A negotiation",
  "Drafting logistics plan"
]

export default function AgentProgress({ itemCount = 20, stockoutCount = 2 }) {
  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setStepIndex(prev => (prev + 1) % PROGRESS_STEPS.length)
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  const currentStep = PROGRESS_STEPS[stepIndex]
  const pct = Math.min(100, Math.round(((stepIndex + 1) / PROGRESS_STEPS.length) * 100))

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-3 my-2 text-xs font-mono space-y-1.5 shadow-sm">
      <div className="flex items-center gap-2 text-[#3fb950]">
        <span>✅</span>
        <span>Disruption radar scan complete</span>
      </div>

      <div className="flex items-center gap-2 text-[#3fb950]">
        <span>✅</span>
        <span>Inventory fetched — {itemCount} items, {stockoutCount} stockouts</span>
      </div>

      <div className="flex items-center gap-2 text-[#58a6ff] font-semibold animate-pulse">
        <span>⚡</span>
        <span>{currentStep}...</span>
      </div>

      <div className="flex items-center gap-2 text-[#8b949e]">
        <span>○</span>
        <span>Awaiting your authorization</span>
      </div>

      <div className="pt-2">
        <div className="flex justify-between text-[11px] text-[#8b949e] mb-1">
          <span>Agent pipeline</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full bg-[#21262d] rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-[#58a6ff] h-1.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    </div>
  )
}
