export default function Sidebar({ devMode, adminMode }) {
  return (
    <aside className="w-14 bg-[#0d1117] border-r border-[#30363d]
                      flex flex-col items-center py-4 shrink-0
                      h-screen sticky top-0">
      <span className="text-xl mb-8" title="Sovereign Supply Chain">
        🛡️
      </span>
      {devMode && (
        <div className="mt-auto text-xs text-[#8b949e] rotate-180
                        writing-mode-vertical">
          DEV
        </div>
      )}
    </aside>
  )
}
