import { useState, useRef, useEffect } from 'react'

export default function Tooltip({ children, content, position = 'top' }) {
  const [visible, setVisible] = useState(false)
  const ref = useRef(null)

  // Hide on outside click
  useEffect(() => {
    if (!visible) return
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setVisible(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [visible])

  return (
    <div ref={ref} className="relative inline-flex" style={{ zIndex: 50 }}>
      {/* Trigger — show on hover OR keep open if pinned */}
      <div
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      >
        {children}
      </div>

      {/* Tooltip panel */}
      {visible && (
        <div
          className={`absolute z-50 w-72 bg-[#161b22] border
                      border-[#30363d] rounded-lg shadow-xl p-3
                      text-xs text-[#e6edf3]
                      ${position === 'top'
                        ? 'bottom-full mb-2 left-0'
                        : 'top-full mt-2 left-0'}`}
          onMouseEnter={() => setVisible(true)}
          onMouseLeave={() => setVisible(false)}
        >
          {content}
          {/* Arrow */}
          <div className={`absolute w-2 h-2 bg-[#161b22]
                           border-[#30363d] rotate-45
                           ${position === 'top'
                             ? 'border-b border-r -bottom-1 left-3'
                             : 'border-t border-l -top-1 left-3'}`}
          />
        </div>
      )}
    </div>
  )
}
