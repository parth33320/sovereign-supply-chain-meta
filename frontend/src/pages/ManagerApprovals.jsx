import React, { useState, useEffect } from 'react'
import { getManagerPending, approveManagerRequest, rejectManagerRequest } from '../api/client'
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react'

export default function ManagerApprovals() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionMessage, setActionMessage] = useState(null)

  const fetchPending = async () => {
    setLoading(true)
    try {
      const data = await getManagerPending()
      setRequests(data || [])
    } catch (err) {
      console.error('Failed to load pending requests:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPending()
  }, [])

  const handleApprove = async (id) => {
    try {
      await approveManagerRequest(id)
      setActionMessage(`Approved request #${id}`)
      setRequests(prev => prev.filter(r => r.id !== id))
    } catch {
      setActionMessage(`Failed to approve request #${id}`)
    }
  }

  const handleReject = async (id) => {
    try {
      await rejectManagerRequest(id)
      setActionMessage(`Rejected request #${id}`)
      setRequests(prev => prev.filter(r => r.id !== id))
    } catch {
      setActionMessage(`Failed to reject request #${id}`)
    }
  }

  return (
    <div className="flex-1 flex flex-col p-6 max-w-5xl mx-auto w-full">
      <div className="flex items-center justify-between border-b border-[#30363d] pb-4 mb-6">
        <div>
          <h1 className="text-base font-semibold text-[#e6edf3] flex items-center gap-2">
            <span>⚙️</span> INVENTORY GOVERNANCE — PENDING APPROVALS
          </h1>
          <p className="text-xs text-[#8b949e] mt-1">
            Review and authorize administrative restock orders and supply chain overrides.
          </p>
        </div>
        <button
          onClick={fetchPending}
          className="p-1.5 text-[#8b949e] hover:text-[#e6edf3] rounded hover:bg-[#21262d] transition-colors"
          title="Refresh pending list"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {actionMessage && (
        <div className="mb-4 p-2 bg-[#21262d] border border-[#30363d] rounded text-xs text-[#58a6ff]">
          {actionMessage}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-10 bg-[#161b22] rounded animate-pulse" />
          ))}
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-12 text-[#8b949e] text-sm bg-[#161b22] border border-[#30363d] rounded-lg">
          No pending governance approvals. All requests resolved.
        </div>
      ) : (
        <div className="border border-[#30363d] rounded-lg overflow-hidden bg-[#161b22]">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#0d1117] border-b border-[#30363d] text-[#8b949e]">
                <th className="py-2.5 px-3">Action</th>
                <th className="py-2.5 px-3">Item</th>
                <th className="py-2.5 px-3 text-right">Qty</th>
                <th className="py-2.5 px-3">Supplier</th>
                <th className="py-2.5 px-3 text-center">Decisions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#30363d]">
              {requests.map(req => (
                <tr key={req.id} className="hover:bg-[#21262d] transition-colors">
                  <td className="py-2 px-3 font-semibold text-[#58a6ff]">
                    {req.action}
                  </td>
                  <td className="py-2 px-3 text-[#e6edf3] font-medium">
                    {req.item_name}
                  </td>
                  <td className="py-2 px-3 text-right font-mono text-[#8b949e]">
                    {req.quantity}
                  </td>
                  <td className="py-2 px-3 text-[#8b949e] font-mono">
                    {req.supplier_id}
                  </td>
                  <td className="py-2 px-3">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => handleApprove(req.id)}
                        className="bg-[#238636] hover:bg-[#2ea043] text-white px-2 py-1 rounded text-[11px] font-semibold transition-colors flex items-center gap-1"
                      >
                        <CheckCircle size={12} /> Approve
                      </button>
                      <button
                        onClick={() => handleReject(req.id)}
                        className="bg-[#da3633] hover:bg-[#f85149] text-white px-2 py-1 rounded text-[11px] font-semibold transition-colors flex items-center gap-1"
                      >
                        <XCircle size={12} /> Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
