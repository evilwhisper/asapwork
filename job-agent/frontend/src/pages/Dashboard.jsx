import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'
import JobCard from '../components/JobCard'

export default function Dashboard() {
  const qc = useQueryClient()
  const [filters, setFilters] = useState({ status: '', source: '', search: '', minScore: 0 })

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => client.get('/api/jobs', { params: {
      status: filters.status || undefined,
      source: filters.source || undefined,
      search: filters.search || undefined,
      min_score: filters.minScore > 0 ? filters.minScore / 100 : undefined,
    }}).then(r => r.data),
  })

  const { data: stats } = useQuery({
    queryKey: ['job-stats'],
    queryFn: () => client.get('/api/jobs/stats').then(r => r.data),
    refetchInterval: 15_000,
  })

  const scrapeNow = useMutation({
    mutationFn: () => client.post('/api/jobs/scrape-now'),
    onSuccess: () => toast.success('Scrape triggered — jobs will appear shortly'),
    onError: () => toast.error('Scrape failed'),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Dashboard</h1>
        <button onClick={() => scrapeNow.mutate()} disabled={scrapeNow.isPending}
          className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors disabled:opacity-40">
          {scrapeNow.isPending ? 'Scraping...' : '⟳ Scrape Now'}
        </button>
      </div>

      {/* Stat cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Jobs Found', value: stats.total, color: 'text-white' },
            { label: 'In Queue', value: stats.queued, color: 'text-yellow-400' },
            { label: 'Submitted', value: stats.submitted, color: 'text-green-400' },
            { label: 'Failed', value: stats.failed, color: 'text-red-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={`text-2xl font-bold ${color}`}>{value ?? '—'}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text" placeholder="Search jobs..."
          value={filters.search}
          onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 w-48"
        />
        <select value={filters.source} onChange={e => setFilters(f => ({ ...f, source: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All sources</option>
          <option value="seek">Seek</option>
          <option value="indeed_au">Indeed AU</option>
          <option value="linkedin_au">LinkedIn AU</option>
          <option value="jora">Jora</option>
        </select>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All statuses</option>
          <option value="new">New</option>
          <option value="queued">Queued</option>
          <option value="skipped">Skipped</option>
          <option value="applied">Applied</option>
        </select>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Min score:</span>
          <input type="range" min={0} max={100} value={filters.minScore}
            onChange={e => setFilters(f => ({ ...f, minScore: Number(e.target.value) }))}
            className="w-24 accent-brand-500" />
          <span className="text-xs text-gray-400 w-8">{filters.minScore}%</span>
        </div>
      </div>

      {/* Job feed */}
      {isLoading ? (
        <div className="text-center text-gray-500 py-12">Loading jobs...</div>
      ) : jobs.length === 0 ? (
        <div className="text-center text-gray-600 py-16">
          <p className="text-4xl mb-3">🔍</p>
          <p className="text-sm">No jobs yet. Hit <strong>Scrape Now</strong> or configure scrapers in Settings.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map(job => <JobCard key={job.id} job={job} />)}
        </div>
      )}
    </div>
  )
}
