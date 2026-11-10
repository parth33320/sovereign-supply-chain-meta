export default function HITLCard({ po, threadId,
                                   onApprove, onReject }) {
  if (!po) return null
  return (
    <div className="border-2 border-[#e3b341] rounded-lg p-4
                    animate-pulse-border bg-[#161b22] my-2">
      <style>{`
        @keyframes pulseBorder {
          0%,100% { border-color: #e3b341; }
          50%      { border-color: #f0d060; }
        }
        .animate-pulse-border {
          animation: pulseBorder 2s ease-in-out infinite;
        }
      `}</style>
      <p className="text-xs font-semibold text-[#e3b341] uppercase
                    tracking-wider mb-3">
        ⚡ Action Required: Purchase Order
      </p>
      <div className="text-sm text-[#e6edf3] space-y-1 mb-4">
        <p>Supplier: {po.supplier}</p>
        <p>SKU: {po.sku}</p>
        <p>Qty: {po.quantity} units · ${po.unit_price}/u</p>
        <p className="font-semibold">
          Total: ${po.total_cost} · Lead: {po.lead_time} days
        </p>
      </div>
      <div className="flex gap-3">
        <button onClick={onApprove}
                className="flex-1 bg-[#238636] hover:bg-[#2ea043]
                           text-white text-sm font-medium py-2
                           rounded-md transition-colors">
          ✅ Approve
        </button>
        <button onClick={onReject}
                className="flex-1 bg-[#da3633] hover:bg-[#f85149]
                           text-white text-sm font-medium py-2
                           rounded-md transition-colors">
          ❌ Reject
        </button>
      </div>
    </div>
  )
}
