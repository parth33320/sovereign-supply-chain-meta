import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Orchestrator from './pages/Orchestrator'
import ManagerApprovals from './pages/ManagerApprovals'
import Analytics from './pages/Analytics'
import { useMuseStatus } from './hooks/useMuseStatus'

const params = new URLSearchParams(window.location.search)
const devMode = params.get('dev') === '1'
const adminMode = params.get('admin') === '1'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-screen bg-[#0d1117] text-[#e6edf3]">
          <div className="max-w-lg p-6 bg-[#161b22] border border-[#f85149] rounded-xl text-center space-y-3">
            <div className="text-3xl">⚠️</div>
            <h2 className="text-lg font-semibold text-[#f85149]">Something went wrong</h2>
            <p className="text-xs text-[#8b949e] font-mono break-all">
              {String(this.state.error?.message || this.state.error)}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#238636] text-white rounded-lg text-sm hover:bg-[#2ea043]"
            >
              Reload
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

export default function App() {
  const [role, setRole] = useState('operator')
  const [activePage, setActivePage] = useState(() => {
    const path = window.location.pathname.toLowerCase()
    if (path.includes('analytics')) return 'analytics'
    if (path.includes('manager')) return 'manager'
    return 'orchestrator'
  })
  const museStatus = useMuseStatus()

  const handleNavigate = (page) => {
    setActivePage(page)
    const newPath = page === 'orchestrator' ? '/' : `/${page}`
    window.history.pushState({}, '', newPath)
  }

  return (
    <ErrorBoundary>
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      <Sidebar
        devMode={devMode}
        adminMode={adminMode}
        role={role}
        onRoleChange={setRole}
        activePage={activePage}
        onNavigate={handleNavigate}
      />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Muse Status Banner */}
        <div
          className={`text-center text-xs font-semibold py-1.5 border-b ${
            museStatus.isLive
              ? 'bg-[#0d1f0d] text-[#3fb950] border-[#238636]'
              : 'bg-[#1a1200] text-[#d29922] border-[#9e6a03]'
          }`}
          style={{ letterSpacing: '0.03em' }}
        >
          {museStatus.isLive
            ? '🟢 Meta Muse AI Agent active · muse-spark-1.3'
            : '⚠️ Mock AI agent demo active · Set META_API_KEY env var to enable Muse'}
        </div>
        <main className="flex-1 overflow-y-auto">
          {activePage === 'manager' && role === 'manager' ? (
            <ManagerApprovals />
          ) : activePage === 'analytics' ? (
            <Analytics />
          ) : (
            <Orchestrator />
          )}
        </main>
      </div>
    </div>
    </ErrorBoundary>
  )
}
