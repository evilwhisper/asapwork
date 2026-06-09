import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'

const STATUS_BADGE = {
  pending:   'bg-yellow-900 text-yellow-300',
  approved:  'bg-blue-900 text-blue-300',
  submitted: 'bg-green-900 text-green-300',
  rejected:  'bg-gray-800 text-gray-400',
  failed:    'bg-red-900 text-red-400',
}

export default function ApplicationCard({ app }) {
  const [editing, setEditing] = useState(false)
  const [coverLetter, setCoverLetter] = useState(app.cover_letter || '')
  const qc = useQueryClient()

  const approve = useMutation({
    mutationFn: () => client.put(`/api/applications/${app.id}/approve`),
    onSuccess: () => { toast.success('Approved'); qc.invalidateQueries(['applications']) },
  })

  const reject = useMutation({
    mutationFn: () => client.put(`/api/applications/${app.id}/reject`),
    onSuccess: () => { toast.success('Rejected'); qc.invalidateQueries(['applications']) },
  })

  const save = useMutation({
    mutationFn: () => client.put(`/api/applications/${app.id}`, { ...app, cover_letter: coverLetter }),
    onSuccess: () => { toast.success('Saved'); setEditing(false); qc.invalidateQueries(['applications']) },
  })

  const submit = useMutation({
    mutationFn: () => client.post(`/api/applications/${app.id}/submit`),
    onSuccess: () => { toast.success('Submission triggered'); qc.invalidateQueries(['applications']) },
    onError: (e) => toast.error(e.response?.data?.detail || 'Submission failed'),
  })

  const job = app.job

  return (
    <div className="rounded-xl border border-gray-700 bg-gray-900 p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_BADGE[app.status]}`}>
              {app.status}
            </span>
            {job?.match_score !== null && (
              <span className="text-xs text-gray-500 font-mono">{Math.round((job?.match_score || 0) * 100)}% match</span>
            )}
          </div>
          <h3 className="font-semibold text-white text-sm">{job?.title || 'Unknown Role'}</h3>
          <p className="text-gray-400 text-xs">{job?.company} · {job?.location}</p>
        </div>

        <div className="flex gap-2 flex-shrink-0">
          {app.status === 'pending' && (
            <>
              <button onClick={() => approve.mutate()}
                className="text-xs px-3 py-1.5 rounded-lg bg-green-700 hover:bg-green-600 text-white font-medium transition-colors">
                Approve
              </button>
              <button onClick={() => reject.mutate()}
                className="text-xs px-3 py-1.5 rounded-lg bg-red-900 hover:bg-red-800 text-red-300 font-medium transition-colors">
                Reject
              </button>
            </>
          )}
          {app.status === 'approved' && (
            <button onClick={() => submit.mutate()} disabled={submit.isPending}
              className="text-xs px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-40">
              {submit.isPending ? 'Submitting...' : 'Submit'}
            </button>
          )}
          {app.status === 'failed' && (
            <button onClick={() => submit.mutate()}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-white font-medium transition-colors">
              Retry
            </button>
          )}
        </div>
      </div>

      {/* Cover letter */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <p className="text-xs font-medium text-gray-400">Cover Letter</p>
          <button onClick={() => setEditing(!editing)}
            className="text-xs text-brand-500 hover:text-brand-400">
            {editing ? 'Cancel' : 'Edit'}
          </button>
        </div>
        {editing ? (
          <div>
            <textarea
              value={coverLetter}
              onChange={e => setCoverLetter(e.target.value)}
              rows={8}
              className="w-full bg-gray-800 border border-gray-600 rounded-lg p-2 text-xs text-gray-200 resize-none focus:outline-none focus:border-brand-500"
            />
            <button onClick={() => save.mutate()} disabled={save.isPending}
              className="mt-1 text-xs px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors">
              Save
            </button>
          </div>
        ) : (
          <p className="text-xs text-gray-400 line-clamp-3 whitespace-pre-wrap">{coverLetter || 'No cover letter generated yet.'}</p>
        )}
      </div>

      {/* Resume */}
      {app.resume_version && (
        <a href={`/api/applications/${app.id}/resume`} target="_blank" rel="noopener noreferrer"
          className="text-xs text-brand-500 hover:text-brand-400">
          Download tailored resume ↗
        </a>
      )}

      {app.notes && (
        <p className="mt-2 text-xs text-red-400 bg-red-950 rounded px-2 py-1">{app.notes}</p>
      )}
    </div>
  )
}
