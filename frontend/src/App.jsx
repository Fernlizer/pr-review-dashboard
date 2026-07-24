import { Routes, Route, NavLink } from 'react-router-dom'
import { Shield, GitPullRequest, LayoutDashboard, Settings as SettingsIcon, RefreshCw } from 'lucide-react'
import Dashboard from './pages/Dashboard'
import PRList from './pages/PRList'
import PRDetail from './pages/PRDetail'
import SettingsPage from './pages/Settings'
import { useState } from 'react'

function App() {
  const [polling, setPolling] = useState(false)

  const triggerPoll = async () => {
    setPolling(true)
    try {
      await fetch('/api/poll', { method: 'POST' })
      // Backend returns immediately — poll runs in background
      // Auto-reload after 5 seconds to show updated results
      setTimeout(() => {
        window.location.reload()
      }, 5000)
    } catch (e) {
      console.error(e)
      setPolling(false)
    }
  }

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/prs', icon: GitPullRequest, label: 'Pull Requests' },
    { to: '/settings', icon: SettingsIcon, label: 'Settings' },
  ]

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className="w-[240px] flex-shrink-0 flex flex-col border-r"
        style={{
          background: 'var(--color-paper-2)',
          borderColor: 'var(--color-rule)',
        }}
      >
        {/* Wordmark */}
        <div
          className="px-md py-lg border-b"
          style={{ borderColor: 'var(--color-rule)' }}
        >
          <div className="flex items-center gap-sm">
            <div
              className="w-8 h-8 rounded-md flex items-center justify-center"
              style={{ background: 'var(--color-accent-bg)' }}
            >
              <Shield
                className="w-4 h-4"
                style={{ color: 'var(--color-accent)' }}
              />
            </div>
            <div>
              <h1
                className="text-sm font-semibold tracking-tight"
                style={{ color: 'var(--color-ink)', letterSpacing: '-0.02em' }}
              >
                PR Review
              </h1>
              <p
                className="text-xs font-mono"
                style={{ color: 'var(--color-ink-3)' }}
              >
                security scanner
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-sm py-sm" style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `group flex items-center gap-sm px-sm py-[7px] rounded-md text-sm font-medium transition-colors`
              }
              style={({ isActive }) => ({
                background: isActive ? 'var(--color-paper-3)' : 'transparent',
                color: isActive ? 'var(--color-ink)' : 'var(--color-ink-3)',
                transitionDuration: 'var(--dur-micro)',
              })}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className="w-4 h-4 flex-shrink-0"
                    style={{
                      color: isActive ? 'var(--color-accent)' : 'var(--color-ink-4)',
                      transition: `color var(--dur-micro) var(--ease-out)`,
                    }}
                  />
                  {label}
                  {isActive && (
                    <div
                      className="ml-auto w-1.5 h-1.5 rounded-full"
                      style={{ background: 'var(--color-accent)' }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Poll button */}
        <div className="p-sm border-t" style={{ borderColor: 'var(--color-rule)' }}>
          <button
            onClick={triggerPoll}
            disabled={polling}
            className="w-full flex items-center justify-center gap-2xs rounded-md text-sm font-semibold transition-all"
            style={{
              background: polling ? 'var(--color-accent-2)' : 'var(--color-accent)',
              color: 'var(--color-accent-ink)',
              padding: '10px 16px',
              opacity: polling ? 0.7 : 1,
              cursor: polling ? 'not-allowed' : 'pointer',
              transitionDuration: 'var(--dur-short)',
            }}
          >
            <RefreshCw
              className="w-3.5 h-3.5"
              style={polling ? { animation: 'spin 1s linear infinite' } : {}}
            />
            {polling ? 'Polling...' : 'Poll Now'}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto min-w-0">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/prs" element={<PRList />} />
          <Route path="/prs/:id" element={<PRDetail />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
