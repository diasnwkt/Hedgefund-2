import { Link, useLocation } from 'react-router-dom'
import ModeIndicator from './ModeIndicator'
import KillSwitch from './KillSwitch'

const NAV = [
  { to: '/', label: 'Dashboard' },
  { to: '/portfolio', label: 'Portfolio' },
  { to: '/signals', label: 'Signals' },
  { to: '/recommendations', label: 'Recommendations' },
  { to: '/risk', label: 'Risk' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout({ children, mode }) {
  const { pathname } = useLocation()

  return (
    <div className="min-h-screen flex flex-col bg-gray-950">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-lg tracking-tight text-white">
            HedgeFund
          </span>
          <nav className="flex gap-4">
            {NAV.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={`text-sm px-3 py-1 rounded transition-colors ${
                  pathname === to
                    ? 'bg-sky-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          {mode && <ModeIndicator mode={mode} />}
          <KillSwitch />
        </div>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}
