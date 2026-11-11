import React, { useState } from 'react'
import Sidebar from './components/Sidebar'
import Orchestrator from './pages/Orchestrator'
import ManagerApprovals from './pages/ManagerApprovals'
import Analytics from './pages/Analytics'

const params = new URLSearchParams(window.location.search)
const devMode = params.get('dev') === '1'
const adminMode = params.get('admin') === '1'

export default function App() {
  const [role, setRole] = useState('operator')
  const [activePage, setActivePage] = useState(() => {
    const path = window.location.pathname.toLowerCase()
    if (path.includes('analytics')) return 'analytics'
    if (path.includes('manager')) return 'manager'
    return 'orchestrator'
  })

  const handleNavigate = (page) => {
    setActivePage(page)
    const newPath = page === 'orchestrator' ? '/' : `/${page}`
    window.history.pushState({}, '', newPath)
  }

  return (
    <div className="flex h-screen bg-[#0d1117] text-[#e6edf3] overflow-hidden">
      <Sidebar
        devMode={devMode}
        adminMode={adminMode}
        role={role}
        onRoleChange={setRole}
        activePage={activePage}
        onNavigate={handleNavigate}
      />
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
  )
}
