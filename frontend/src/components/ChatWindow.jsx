import { useEffect, useRef } from 'react'

export default function ChatWindow({ messages, hidden,
                                     onToggle, onClear,
                                     disabled }) {
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
            <div key={i} className="flex gap-2 text-sm">
              <span>{m.role === 'user' ? '👤' : '🤖'}</span>
              <span className={m.role === 'user'
                ? 'text-[#e6edf3]'
                : 'text-[#8b949e] whitespace-pre-wrap'}>
                {m.content}
              </span>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
