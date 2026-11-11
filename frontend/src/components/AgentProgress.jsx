import React, { useState, useEffect } from 'react'

const NODE_LABELS = {
  global_oracle: "Scanning disruptions...",
  fetch_inventory: "Fetching inventory...",
  a2a_negotiate: "Negotiating with suppliers...",
  draft_plan: "Drafting logistics plan...",
  human_review: "Awaiting human approval...",
  cancelled: "Request cancelled."
}

const STEP_ORDER = ["global_oracle", "fetch_inventory", "a2a_negotiate", "draft_plan", "human_review"]

export default function AgentProgress({ currentNode, currentLabel, itemCount = 20, stockoutCount = 2 }) {
  const activeNode = currentNode || "global_oracle"
  const stepIndex = Math.max(0, STEP_ORDER.indexOf(activeNode))
  const displayLabel = currentLabel || NODE_LABELS[activeNode] || "Processing..."
  const pct = Math.min(100, Math.round(((stepIndex + 1) / STEP_ORDER.length) * 100))

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
        <span>{displayLabel}</span>
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
