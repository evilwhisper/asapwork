import { NavLink } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import client from '../api/client'

const NAV = [
  { to: '/dashboard', icon: '🔍', label: 'Dashboard' },
  { to: '/queue',     icon: '📋', label: 'Queue' },
  { to: '/log',       icon: '📊', label: 'Log' },
  { to: '/profile',   icon: '👤', label: 'Profile' },
  { to: '/settings',  icon: '⚙️',  label: 'Settings' },
]

export default function Sidebar() {
  const { data: stats } = useQuery({
    queryKey: ['job-stats'],
    queryFn: () => client.get('/api/jobs/stats').then(r => r.data),
    refetchInterval: 30_000,
  })

  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🤖</span>
          <div>
            <p className="font-bold text-white text-sm leading-tight">Job Agent</p>
            <p className="text-xs text-gray-500">Autopilot job seeking</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            <span>{label}</span>
            {label === 'Queue' && stats?.queued > 0 && (
              <span className="ml-auto bg-brand-500 text-white text-xs rounded-full px-1.5 py-0.5">
                {stats.queued}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Status */}
      {stats && (
        <div className="px-4 py-4 border-t border-gray-800 text-xs text-gray-500 space-y-1">
          <p>Found: <span className="text-gray-300">{stats.total}</span></p>
          <p>Submitted: <span className="text-green-400">{stats.submitted}</span></p>
          {stats.failed > 0 && <p>Failed: <span className="text-red-400">{stats.failed}</span></p>}
        </div>
      )}
    </aside>
  )
}
