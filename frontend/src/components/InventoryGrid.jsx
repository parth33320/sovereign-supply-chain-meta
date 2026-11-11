import React, { useState, useEffect, useMemo } from 'react'
import { getInventory } from '../api/client'
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

// Sparkline helper generating 7 fake points ending at current quantity
function Sparkline({ quantity }) {
  // Deterministic 7-point trend based on quantity
  const isZero = quantity === 0
  const isNetUp = !isZero && quantity >= 50
  const points = isZero
    ? [30, 25, 20, 15, 10, 5, 0]
    : isNetUp
      ? [
          Math.max(0, quantity * 0.7),
          Math.max(0, quantity * 0.8),
          Math.max(0, quantity * 0.75),
          Math.max(0, quantity * 0.9),
          Math.max(0, quantity * 0.85),
          Math.max(0, quantity * 0.95),
          quantity
        ]
      : [
          Math.max(0, quantity * 1.5),
          Math.max(0, quantity * 1.4),
          Math.max(0, quantity * 1.3),
          Math.max(0, quantity * 1.2),
          Math.max(0, quantity * 1.15),
          Math.max(0, quantity * 1.05),
          quantity
        ]

  const maxVal = Math.max(...points, 1)
  const minVal = Math.min(...points, 0)
  const range = maxVal - minVal || 1
  const width = 60
  const height = 18

  const coords = points.map((p, idx) => {
    const x = (idx / (points.length - 1)) * (width - 4) + 2
    const y = height - ((p - minVal) / range) * (height - 6) - 3
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  const strokeColor = isZero || !isNetUp ? '#f85149' : '#3fb950'

  return (
    <svg width={width} height={height} className="inline-block">
      <polyline
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={coords}
      />
    </svg>
  )
}

export default function InventoryGrid({ tenantId = 'Tenant_A', onSelectStockout }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [textFilter, setTextFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [isExpanded, setIsExpanded] = useState(true) // Expanded by default on desktop

  const fetchInventory = async () => {
    setLoading(true)
    try {
      const invData = await getInventory(tenantId)
      setItems(invData.items || [])
    } catch (err) {
      console.error('Failed to load inventory:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchInventory()
  }, [tenantId])

  const stockoutCount = useMemo(() => {
    return items.filter(i => i.quantity === 0 || i.status === 'stockout').length
  }, [items])

  const filteredItems = useMemo(() => {
    return items.map(item => {
      // LOW STOCK THRESHOLD: For any item with quantity > 0 and quantity <= 10, mark as low
      const isStockout = item.quantity === 0 || item.status === 'stockout'
      const isLow = !isStockout && item.quantity > 0 && item.quantity <= 10
      const computedStatus = isStockout ? 'stockout' : isLow ? 'low' : 'ok'
      return { ...item, status: computedStatus }
    }).filter(item => {
      const matchesText = item.name.toLowerCase().includes(textFilter.toLowerCase()) ||
                          item.supplier.toLowerCase().includes(textFilter.toLowerCase())
      if (!matchesText) return false
      if (statusFilter === 'STOCKOUT') return item.status === 'stockout'
      if (statusFilter === 'LOW') return item.status === 'low'
      if (statusFilter === 'OK') return item.status === 'ok'
      return true
    })
  }, [items, textFilter, statusFilter])

  return (
    <div className="mb-4 bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden transition-all">
      {/* Header bar */}
      <div className="px-4 py-2.5 bg-[#0d1117] border-b border-[#30363d] flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-xs tracking-wide text-[#e6edf3]">
            📦 LIVE INVENTORY — {tenantId}
          </span>
          {stockoutCount > 0 && (
            <span className="bg-[#b62324]/20 text-[#ff7b72] border border-[#b62324]/40 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
              🔴 {stockoutCount} STOCKOUTS
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchInventory}
            title="Refresh inventory"
            className="p-1 text-[#8b949e] hover:text-[#e6edf3] rounded hover:bg-[#21262d] transition-colors"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => setIsExpanded(prev => !prev)}
            className="md:hidden flex items-center text-xs text-[#8b949e] hover:text-[#e6edf3] gap-1"
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Grid Content - Desktop expanded, mobile collapsible */}
      <div className={`${isExpanded ? 'block' : 'hidden md:block'} p-3`}>
        {/* Filter controls */}
        <div className="flex flex-col sm:flex-row gap-2 mb-3">
          <input
            type="text"
            placeholder="🔍 Filter inventory..."
            value={textFilter}
            onChange={e => setTextFilter(e.target.value)}
            className="flex-1 bg-[#0d1117] border border-[#30363d] rounded px-2.5 py-1 text-xs text-[#e6edf3] placeholder-[#8b949e] focus:outline-none focus:border-[#58a6ff]"
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="bg-[#0d1117] border border-[#30363d] rounded px-2.5 py-1 text-xs text-[#e6edf3] focus:outline-none focus:border-[#58a6ff]"
          >
            <option value="ALL">All Items</option>
            <option value="LOW">🟡 LOW (Low stock only)</option>
            <option value="STOCKOUT">🔴 Stockouts only</option>
            <option value="OK">✅ OK only</option>
          </select>
        </div>

        {/* Inventory Table or Loading Skeleton */}
        {loading ? (
          <div className="space-y-2 py-2">
            {[1, 2, 3, 4].map(n => (
              <div key={n} className="h-6 bg-[#21262d] rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#30363d] text-[#8b949e]">
                  <th className="py-1.5 px-2">Item</th>
                  <th className="py-1.5 px-2">Stock</th>
                  <th className="py-1.5 px-2">Reorder Pt</th>
                  <th className="py-1.5 px-2">Status</th>
                  <th className="py-1.5 px-2">Supplier</th>
                  <th className="py-1.5 px-2">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#21262d]">
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-[#8b949e]">
                      No items matching filter
                    </td>
                  </tr>
                ) : (
                  filteredItems.map(item => {
                    const isStockout = item.status === 'stockout'
                    const isLow = item.status === 'low'
                    return (
                      <tr
                        key={item.name}
                        onClick={() => {
                          if (isStockout && onSelectStockout) {
                            onSelectStockout(item.name)
                          }
                        }}
                        className={`hover:bg-[#21262d] transition-colors ${
                          isStockout ? 'cursor-pointer hover:bg-[#b62324]/10' : ''
                        }`}
                        title={isStockout ? `Click to request emergency restock for ${item.name}` : ''}
                      >
                        <td className="py-1.5 px-2 font-medium text-[#e6edf3]">
                          {item.name}
                        </td>
                        <td className="py-1.5 px-2 text-[#8b949e] font-mono">
                          {item.quantity.toLocaleString()}
                        </td>
                        <td className="py-1.5 px-2 text-[#58a6ff] font-mono text-[11px]">
                          {item.reorder_point != null ? item.reorder_point : '—'}
                        </td>
                        <td className="py-1.5 px-2">
                          {isStockout && (
                            <span className="bg-[#b62324]/20 text-[#ff7b72] border border-[#b62324]/30 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                              🔴 STOCKOUT
                            </span>
                          )}
                          {isLow && (
                            <span className="bg-[#d29922]/20 text-[#f0883e] border border-[#d29922]/30 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                              🟡 LOW
                            </span>
                          )}
                          {!isStockout && !isLow && (
                            <span className="bg-[#238636]/20 text-[#3fb950] border border-[#238636]/30 px-1.5 py-0.5 rounded text-[10px] font-semibold">
                              ✅ OK
                            </span>
                          )}
                        </td>
                        <td className="py-1.5 px-2 text-[#8b949e] font-mono text-[11px]">
                          {item.supplier}
                        </td>
                        <td className="py-1.5 px-2">
                          <Sparkline quantity={item.quantity} />
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
