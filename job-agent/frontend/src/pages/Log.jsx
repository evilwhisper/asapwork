import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'

const STATUS_BADGE = {
  pending:   'bg-yellow-900 text-yellow-300',
  approved:  'bg-blue-900 text-blue-300',
  submitted: 'bg-green-900 text-green-300',
  rejected:  'bg-gray-700 text-gray-400',
  failed:    'bg-red-900 text-red-400',
}

export default function Log() {
  const [expanded, setExpanded] = useState(null)
  const qc = useQueryClient()

  const { data: apps = [], isLoading } = useQuery({
    queryKey: ['applications-all'],
    queryFn: () => client.get('/api/applications').then(r => r.data),
    refetchInterval: 15_000,
  })

  const submit = useMutation({
    mutationFn: (id) => client.post(`/api/applications/${id}/submit`),
    onSuccess: () => { toast.success('Submission triggered'); qc.invalidateQueries(['applications-all']) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  return (
    <div>
      <h1 className="text-xl font-bold text-white mb-6">Submission Log</h1>

      {isLoading ? (
        <div className="text-center text-gray-500 py-12">Loading...</div>
      ) : apps.length === 0 ? (
        <div className="text-center text-gray-600 py-16">
          <p className="text-4xl mb-3">📊</p>
          <p className="text-sm">No applications yet.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-900 border-b border-gray-800">
              <tr>
                {['Company', 'Role', 'Date', 'Source', 'Status', 'Score', 'Actions'].map(h => (
                  <th key={h} className="text-left text-xs font-medium text-gray-500 px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {apps.map(app => (
                <>
                  <tr key={app.id}
                    onClick={() => setExpanded(expanded === app.id ? null : app.id)}
                    className="hover:bg-gray-900/50 cursor-pointer transition-colors">
                    <td className="px-4 py-3 text-white">{app.job?.company || '—'}</td>
                    <td className="px-4 py-3 text-gray-300 max-w-[180px] truncate">{app.job?.title || '—'}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {app.submitted_at
                        ? new Date(app.submitted_at).toLocaleDateString()
                        : new Date(app.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{app.job?.source || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_BADGE[app.status]}`}>
                        {app.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs font-mono">
                      {app.job?.match_score !== null ? `${Math.round((app.job?.match_score || 0) * 100)}%` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2" onClick={e => e.stopPropagation()}>
                        {app.status === 'failed' && (
                          <button onClick={() => submit.mutate(app.id)}
                            className="text-xs text-brand-500 hover:text-brand-400">Retry</button>
                        )}
                        {app.status === 'approved' && (
                          <button onClick={() => submit.mutate(app.id)}
                            className="text-xs text-brand-500 hover:text-brand-400">Submit</button>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expanded === app.id && (
                    <tr key={`${app.id}-detail`} className="bg-gray-900/30">
                      <td colSpan={7} className="px-4 py-3">
                        <div className="text-xs text-gray-400 space-y-1">
                          {app.notes && <p className="text-red-400">{app.notes}</p>}
                          {app.cover_letter && (
                            <details>
                              <summary className="cursor-pointer text-gray-500 hover:text-gray-300">Cover letter</summary>
                              <p className="mt-2 whitespace-pre-wrap">{app.cover_letter}</p>
                            </details>
                          )}
                          {app.resume_version && (
                            <a href={`/api/applications/${app.id}/resume`} target="_blank" rel="noopener noreferrer"
                              className="text-brand-500 hover:text-brand-400">Download resume ↗</a>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
