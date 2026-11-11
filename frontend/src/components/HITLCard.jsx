import React from 'react'

export default function HITLCard({ po, threadId, onApprove, onReject }) {
  if (!po) return null

  const poId = po.po_id || po.id || "PO-948201"
  const supplier = po.supplier || "Apex Logistics"
  const sku = po.sku || "—"
  const qty = po.quantity != null ? Number(po.quantity).toLocaleString() : "—"
  const price = po.unit_price != null ? `$${Number(po.unit_price).toFixed(2)}` : "—"
  const total = po.total_cost != null ? `$${Number(po.total_cost).toLocaleString()}` : "—"
  const leadTime = po.lead_time != null ? `${po.lead_time} days` : "3 days"
  const terms = po.terms || "NET-15 terms"
  const savings = po.savings != null ? `$${po.savings}` : "$100"

  return (
    <div className="border-2 border-[#e3b341] rounded-lg p-4 bg-[#161b22] my-2 shadow-lg animate-pulse-border">
      <style>{`
        @keyframes pulseBorder {
          0%, 100% { border-color: #e3b341; }
          50% { border-color: #f0d060; }
        }
        .animate-pulse-border {
          animation: pulseBorder 2.5s ease-in-out infinite;
        }
      `}</style>

      {/* Card Header */}
      <div className="border-b border-[#30363d] pb-2 mb-3">
        <div className="flex items-center justify-between text-xs font-semibold text-[#e3b341] uppercase tracking-wider mb-1">
          <span>⏸ PURCHASE ORDER — AWAITING APPROVAL</span>
        </div>
        <div className="flex justify-between text-xs text-[#8b949e] font-mono">
          <span>{poId}</span>
          <span className="text-[#e6edf3] font-medium">{supplier}</span>
        </div>
      </div>

      {/* Formatted PO Table */}
      <div className="overflow-x-auto mb-3">
        <table className="w-full text-left text-xs border border-[#30363d]">
          <thead className="bg-[#0d1117] text-[#8b949e] border-b border-[#30363d]">
            <tr>
              <th className="py-1.5 px-3">SKU</th>
              <th className="py-1.5 px-3 text-right">Qty</th>
              <th className="py-1.5 px-3 text-right">Price</th>
              <th className="py-1.5 px-3 text-right">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#30363d] text-[#e6edf3]">
            <tr>
              <td className="py-2 px-3 font-mono">{sku}</td>
              <td className="py-2 px-3 text-right font-mono">{qty}</td>
              <td className="py-2 px-3 text-right font-mono">{price}</td>
              <td className="py-2 px-3 text-right font-mono">{total}</td>
            </tr>
          </tbody>
          <tfoot className="bg-[#0d1117] border-t-2 border-[#30363d] font-semibold text-xs text-[#e6edf3]">
            <tr>
              <td colSpan={3} className="py-1.5 px-3 text-right text-[#8b949e]">TOTAL</td>
              <td className="py-1.5 px-3 text-right font-mono text-[#3fb950]">{total}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Logistics & Intelligence Details */}
      <div className="space-y-1 mb-4 text-xs text-[#8b949e]">
        <div className="flex items-center justify-between">
          <span>⏱ Lead: <strong className="text-[#e6edf3]">{leadTime}</strong></span>
          <span>💳 <strong className="text-[#e6edf3]">{terms}</strong></span>
        </div>
        <div className="text-[#58a6ff]">
          🤖 AI-negotiated — {savings} saved
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onApprove}
          className="flex-1 bg-[#238636] hover:bg-[#2ea043] text-white text-xs font-semibold py-2 px-3 rounded transition-colors flex items-center justify-center gap-1.5 shadow"
        >
          <span>✅</span> Approve & Execute
        </button>
        <button
          onClick={onReject}
          className="flex-1 bg-[#da3633] hover:bg-[#f85149] text-white text-xs font-semibold py-2 px-3 rounded transition-colors flex items-center justify-center gap-1.5 shadow"
        >
          <span>✗</span> Reject
        </button>
      </div>
    </div>
  )
}
