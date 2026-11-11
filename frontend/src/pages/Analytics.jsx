import React, { useState, useEffect } from 'react'
import { getKPIs, runWhatIf } from '../api/client'
import { BarChart2, Zap, X } from 'lucide-react'

export default function Analytics({ tenantId = 'Tenant_A' }) {
  const [kpiData, setKpiData] = useState(null)
  const [loading, setLoading] = useState(true)

  // What-If scenario states
  const [whatIfInput, setWhatIfInput] = useState('')
  const [whatIfLoading, setWhatIfLoading] = useState(false)
  const [whatIfResult, setWhatIfResult] = useState(null)

  const fetchKPIs = async () => {
    setLoading(true)
    try {
      const data = await getKPIs(tenantId)
      setKpiData(data)
    } catch (e) {
      console.error('Failed to load KPIs:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKPIs()
  }, [tenantId])

  const handleRunWhatIf = async () => {
    if (!whatIfInput.trim() || whatIfLoading) return
    setWhatIfLoading(true)
    try {
      const res = await runWhatIf(whatIfInput.trim(), 'whatif-analytics-thread', tenantId)
      setWhatIfResult(res)
    } catch (e) {
      console.error('What-if simulation failed:', e)
    } finally {
      setWhatIfLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col p-6 overflow-y-auto max-w-5xl mx-auto w-full space-y-6">
      {/* Page Title */}
      <div className="flex items-center justify-between border-b border-[#30363d] pb-4">
        <div>
          <h1 className="text-lg font-semibold text-[#e6edf3] flex items-center gap-2">
            <span>📊</span> Analytics Dashboard
          </h1>
          <p className="text-xs text-[#8b949e] mt-0.5">
            Real-time supply chain health, KPI tracking, and what-if risk simulations
          </p>
        </div>
      </div>

      {/* KPI Section */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 space-y-4 shadow-sm">
        <div className="flex items-center justify-between border-b border-[#30363d] pb-2">
          <span className="font-semibold text-xs tracking-wider uppercase text-[#e6edf3] flex items-center gap-1.5">
            <BarChart2 size={15} className="text-[#58a6ff]" />
            <span>SUPPLY CHAIN KPIs — {tenantId}</span>
          </span>
          {kpiData && (
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
              kpiData.risk_rating === 'red'
                ? 'bg-[#b62324]/20 text-[#ff7b72] border-[#b62324]/40'
                : kpiData.risk_rating === 'yellow'
                ? 'bg-[#d29922]/20 text-[#f0883e] border-[#d29922]/40'
                : 'bg-[#238636]/20 text-[#3fb950] border-[#238636]/40'
            }`}>
              {kpiData.risk_rating === 'green' ? '🟢 LOW RISK' : kpiData.risk_rating === 'yellow' ? '🟡 MEDIUM RISK' : '🔴 HIGH RISK'}
            </span>
          )}
        </div>

        {loading ? (
          <div className="h-16 bg-[#21262d] rounded animate-pulse" />
        ) : kpiData ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-[#0d1117] border border-[#30363d] rounded p-3 text-center">
                <span className="text-[11px] text-[#8b949e] uppercase font-semibold">Stockout Rate</span>
                <p className="text-xl font-mono font-bold text-[#ff7b72] mt-1">
                  {(kpiData.stockout_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-[#0d1117] border border-[#30363d] rounded p-3 text-center">
                <span className="text-[11px] text-[#8b949e] uppercase font-semibold">Fill Rate</span>
                <p className="text-xl font-mono font-bold text-[#3fb950] mt-1">
                  {(kpiData.fill_rate * 100).toFixed(1)}%
                </p>
              </div>
              <div className="bg-[#0d1117] border border-[#30363d] rounded p-3 text-center">
                <span className="text-[11px] text-[#8b949e] uppercase font-semibold">Low Stock Rate</span>
                <p className="text-xl font-mono font-bold text-[#f0883e] mt-1">
                  {(kpiData.low_stock_rate * 100).toFixed(1)}%
                </p>
              </div>
            </div>

            {kpiData.summary && (
              <div className="bg-[#0d1117] border border-[#30363d]/60 rounded p-3 text-xs text-[#8b949e]">
                🤖 <strong className="text-[#e6edf3]">AI Health Summary:</strong> {kpiData.summary}
              </div>
            )}
          </div>
        ) : (
          <p className="text-xs text-[#8b949e]">No KPI metrics available.</p>
        )}
      </div>

      {/* What-If Scenario Simulation Panel */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4 space-y-4 shadow-sm">
        <div className="border-b border-[#30363d] pb-2 flex items-center justify-between">
          <span className="font-semibold text-xs tracking-wider uppercase text-[#e6edf3] flex items-center gap-1.5">
            <Zap size={15} className="text-[#58a6ff]" />
            <span>What-If Scenario Simulation (Meta Muse-Spark-1.3)</span>
          </span>
        </div>

        <div className="space-y-2">
          <label className="text-xs text-[#8b949e]">
            Describe a hypothetical disruption scenario to evaluate SKU impact and AI-recommended mitigations:
          </label>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              placeholder="Describe a scenario (e.g. transit time doubles, supplier goes offline)..."
              value={whatIfInput}
              onChange={e => setWhatIfInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleRunWhatIf()}
              className="flex-1 bg-[#0d1117] border border-[#30363d] rounded px-3 py-2 text-xs text-[#e6edf3] placeholder-[#8b949e] focus:outline-none focus:border-[#58a6ff]"
            />
            <button
              onClick={handleRunWhatIf}
              disabled={whatIfLoading || !whatIfInput.trim()}
              className="px-4 py-2 text-xs font-semibold bg-[#238636] hover:bg-[#2ea043] text-white rounded transition-colors disabled:opacity-40 shrink-0"
            >
              {whatIfLoading ? 'Simulating...' : 'Run Simulation'}
            </button>
          </div>
        </div>

        {whatIfResult && (
          <div className="space-y-3 pt-2 border-t border-[#30363d]">
            <p className="text-xs text-[#e6edf3] font-medium bg-[#0d1117] p-2.5 rounded border border-[#30363d]/60">
              {whatIfResult.summary}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border border-[#30363d] rounded">
                <thead className="bg-[#0d1117] text-[#8b949e]">
                  <tr>
                    <th className="py-2 px-3">SKU</th>
                    <th className="py-2 px-3">Current Qty</th>
                    <th className="py-2 px-3">Risk Level</th>
                    <th className="py-2 px-3">Days to Stockout</th>
                    <th className="py-2 px-3">Recommended Mitigation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#30363d]">
                  {(whatIfResult.affected_skus || []).map((row, idx) => {
                    const r = (row.risk_level || '').toUpperCase()
                    const badgeColor =
                      r === 'CRITICAL' || r === 'HIGH'
                        ? 'bg-[#b62324]/20 text-[#ff7b72] border-[#b62324]/30'
                        : r === 'MEDIUM'
                        ? 'bg-[#d29922]/20 text-[#f0883e] border-[#d29922]/30'
                        : 'bg-[#238636]/20 text-[#3fb950] border-[#238636]/30'
                    return (
                      <tr key={idx} className="hover:bg-[#0d1117]">
                        <td className="py-2 px-3 font-mono text-[#e6edf3] font-medium">{row.sku}</td>
                        <td className="py-2 px-3 text-[#8b949e] font-mono">{row.current_qty}</td>
                        <td className="py-2 px-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${badgeColor}`}>
                            {row.risk_level}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-[#8b949e] font-mono">{row.days_to_stockout}d</td>
                        <td className="py-2 px-3 text-[#8b949e]">{row.mitigation}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
