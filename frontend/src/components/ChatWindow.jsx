import { useEffect, useRef } from 'react'
import AgentProgress from './AgentProgress'
import HITLCard from './HITLCard'

export default function ChatWindow({ messages, hidden,
                                     onToggle, onClear,
                                     disabled,
                                     agentRunning, currentNode, currentLabel,
                                     isPaused, pendingPO, threadId,
                                     onApprove, onReject }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!hidden && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, hidden])

  const newMsgWhileHidden = hidden &&
    messages.length > 0 &&
    messages[messages.length - 1].role === 'assistant'

  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <button
          onClick={onToggle}
          className="text-xs text-[#8b949e] hover:text-[#e6edf3]
                     border border-[#30363d] rounded px-2 py-1
                     transition-colors">
          {hidden ? 'Show Chat' : 'Hide Chat'}
        </button>
        <button
          onClick={onClear}
          disabled={disabled}
          className="text-xs text-[#8b949e] hover:text-[#e6edf3]
                     border border-[#30363d] rounded px-2 py-1
                     transition-colors disabled:opacity-30
                     disabled:cursor-not-allowed">
          Clear
        </button>
      </div>

      {hidden ? (
        <div className="border border-[#30363d] rounded-lg p-3
                        text-sm text-[#8b949e] bg-[#161b22]">
          💬 Chat hidden ({messages.length} messages)
          {newMsgWhileHidden && (
            <span className="text-[#58a6ff] ml-2">
              ⚡ new response received
            </span>
          )}
          <button onClick={onToggle}
                  className="ml-2 text-[#58a6ff] underline text-xs">
            Show Chat
          </button>
        </div>
      ) : (
        <div className="h-80 overflow-y-auto border border-[#30363d]
                        rounded-lg bg-[#0d1117] p-3 space-y-3">
          {messages.length === 0 && (
            <div className="flex gap-2 text-sm">
              <span>🤖</span>
              <span className="text-[#e6edf3]">
                How can I assist with your supply chain today?
              </span>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={m.id || i} className="flex gap-2 text-sm">
              <span>{m.role === 'user' ? '👤' : '🤖'}</span>
              <span className={m.role === 'user'
                ? 'text-[#e6edf3]'
                : 'text-[#8b949e] whitespace-pre-wrap flex items-center gap-2'}>
                {m.loading && (
                  <span className="w-3 h-3 border-2 border-[#58a6ff] border-t-transparent rounded-full animate-spin inline-block shrink-0" />
                )}
                <span>{m.content}</span>
              </span>
            </div>
          ))}
          {/* Agent progress inline in chat thread */}
          {agentRunning && (
            <div className="px-1 py-2">
              <AgentProgress
                currentNode={currentNode}
                currentLabel={currentLabel}
                itemCount={20}
                stockoutCount={2}
              />
            </div>
          )}

          {/* HITL purchase-order approval — inline in chat thread */}
          {isPaused && pendingPO && (
            <div className="px-1 py-2">
              <HITLCard
                po={pendingPO}
                threadId={threadId}
                onApprove={onApprove}
                onReject={onReject}
              />
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
