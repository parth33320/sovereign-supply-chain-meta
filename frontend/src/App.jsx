import Sidebar from './components/Sidebar'
import Orchestrator from './pages/Orchestrator'

const params = new URLSearchParams(window.location.search)
const devMode = params.get('dev') === '1'
const adminMode = params.get('admin') === '1'

export default function App() {
  return (
    <div className="flex h-screen bg-[#0d1117]
                    text-[#e6edf3] overflow-hidden">
      <Sidebar devMode={devMode} adminMode={adminMode} />
      <main className="flex-1 overflow-y-auto">
        <Orchestrator />
      </main>
    </div>
  )
}
