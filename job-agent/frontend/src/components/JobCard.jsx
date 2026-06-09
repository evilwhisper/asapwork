import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'

const SCORE_COLOR = (score) => {
  if (score === null || score === undefined) return 'bg-gray-700 text-gray-400'
  if (score >= 0.7) return 'bg-green-800 text-green-300'
  if (score >= 0.4) return 'bg-yellow-800 text-yellow-300'
  return 'bg-red-900 text-red-400'
}

const SOURCE_BADGE = {
  seek:       'bg-blue-900 text-blue-300',
  indeed_au:  'bg-purple-900 text-purple-300',
  linkedin_au:'bg-sky-900 text-sky-300',
  jora:       'bg-orange-900 text-orange-300',
}

export default function JobCard({ job }) {
  const [expanded, setExpanded] = useState(false)
  const qc = useQueryClient()

  const skip = useMutation({
    mutationFn: () => client.put(`/api/jobs/${job.id}/skip`),
    onSuccess: () => { toast.success('Skipped'); qc.invalidateQueries(['jobs']) },
  })

  const queue = useMutation({
    mutationFn: () => client.post(`/api/jobs/${job.id}/queue`),
    onSuccess: () => { toast.success('Added to queue'); qc.invalidateQueries(['jobs', 'job-stats']) },
  })

  const isFiltered = job.status === 'skipped'

  return (
    <div className={`rounded-xl border p-4 transition-colors ${
      isFiltered ? 'border-gray-800 bg-gray-900/50 opacity-50' : 'border-gray-700 bg-gray-900 hover:border-gray-600'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SOURCE_BADGE[job.source] || 'bg-gray-700 text-gray-300'}`}>
              {job.source}
            </span>
            {isFiltered && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-950 text-red-400">Filtered</span>
            )}
            {job.match_score !== null && job.match_score !== undefined && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-mono ${SCORE_COLOR(job.match_score)}`}>
                {Math.round(job.match_score * 100)}%
              </span>
            )}
          </div>

          <h3 className="font-semibold text-white text-sm leading-snug truncate">{job.title}</h3>
          <p className="text-gray-400 text-xs mt-0.5">{job.company} · {job.location}</p>

          {job.salary_text && (
            <p className="text-green-400 text-xs mt-1 font-medium">{job.salary_text}</p>
          )}
        </div>

        {!isFiltered && (
          <div className="flex gap-2 flex-shrink-0">
            <button
              onClick={() => queue.mutate()}
              disabled={queue.isPending || job.status === 'queued'}
              className="text-xs px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-medium disabled:opacity-40 transition-colors"
            >
              {job.status === 'queued' ? 'Queued' : 'Queue'}
            </button>
            <button
              onClick={() => skip.mutate()}
              disabled={skip.isPending}
              className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium disabled:opacity-40 transition-colors"
            >
              Skip
            </button>
          </div>
        )}
      </div>

      {/* Expand description */}
      {job.description && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {expanded ? '▲ Hide description' : '▼ Show description'}
        </button>
      )}
      {expanded && (
        <div className="mt-2 text-xs text-gray-400 leading-relaxed max-h-48 overflow-y-auto whitespace-pre-wrap border-t border-gray-800 pt-2">
          {job.description}
        </div>
      )}

      <div className="mt-2 flex items-center justify-between">
        <p className="text-xs text-gray-600">
          {job.posted_at ? new Date(job.posted_at).toLocaleDateString() : 'Date unknown'}
        </p>
        {job.url && (
          <a href={job.url} target="_blank" rel="noopener noreferrer"
            className="text-xs text-brand-500 hover:text-brand-400 transition-colors">
            View listing ↗
          </a>
        )}
      </div>
    </div>
  )
}
