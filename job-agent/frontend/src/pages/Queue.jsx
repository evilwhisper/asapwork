import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'
import ApplicationCard from '../components/ApplicationCard'

export default function Queue() {
  const { data: apps = [], isLoading } = useQuery({
    queryKey: ['applications', 'pending'],
    queryFn: () => client.get('/api/applications', { params: { status: 'pending' } }).then(r => r.data),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-white">Approval Queue</h1>
        <span className="text-sm text-gray-400">{apps.length} pending</span>
      </div>

      {isLoading ? (
        <div className="text-center text-gray-500 py-12">Loading queue...</div>
      ) : apps.length === 0 ? (
        <div className="text-center text-gray-600 py-16">
          <p className="text-4xl mb-3">📋</p>
          <p className="text-sm">Queue is empty. Queue some jobs from the Dashboard first.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {apps.map(app => <ApplicationCard key={app.id} app={app} />)}
        </div>
      )}
    </div>
  )
}
