import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'

const PROVIDERS = ['openai', 'anthropic', 'google', 'ollama', 'custom']
const MODEL_HINTS = {
  openai:    'gpt-4o-mini, gpt-4o',
  anthropic: 'claude-haiku-4-5, claude-sonnet-4-6',
  google:    'gemini-1.5-flash, gemini-1.5-pro',
  ollama:    'llama3, mistral, phi3',
  custom:    'Enter model name',
}

const BLANK_FORM = {
  provider: 'openai',
  api_key: '',
  model_name: '',
  base_url: '',
  ai_scorer_enabled: false,
}

export default function ApiKeyPanel() {
  const qc = useQueryClient()
  const [form, setForm] = useState(BLANK_FORM)
  const [testResults, setTestResults] = useState({})

  const { data: settings = [] } = useQuery({
    queryKey: ['api-settings'],
    queryFn: () => client.get('/api/settings/api').then(r => r.data),
  })

  const { data: tokens } = useQuery({
    queryKey: ['tokens'],
    queryFn: () => client.get('/api/settings/tokens').then(r => r.data),
    refetchInterval: 10_000,
  })

  const save = useMutation({
    mutationFn: (data) => client.post('/api/settings/api', data),
    onSuccess: () => {
      toast.success('Saved')
      setForm(BLANK_FORM)
      qc.invalidateQueries(['api-settings'])
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Save failed'),
  })

  const remove = useMutation({
    mutationFn: (id) => client.delete(`/api/settings/api/${id}`),
    onSuccess: () => { toast.success('Removed'); qc.invalidateQueries(['api-settings']) },
  })

  const test = useMutation({
    mutationFn: (id) => client.post(`/api/settings/api/${id}/test`).then(r => r.data),
    onSuccess: (data, id) => setTestResults(r => ({ ...r, [id]: data })),
    onError: (_, id) => setTestResults(r => ({ ...r, [id]: { success: false, message: 'Request failed', latency_ms: 0 } })),
  })

  const resetTokens = useMutation({
    mutationFn: () => client.delete('/api/settings/tokens'),
    onSuccess: () => { toast.success('Token counter reset'); qc.invalidateQueries(['tokens']) },
  })

  const needsBaseUrl = ['ollama', 'custom'].includes(form.provider)

  return (
    <div className="space-y-6">
      {/* Token counter */}
      {tokens && (
        <div className="flex items-center justify-between bg-gray-800/50 border border-gray-700 rounded-xl px-4 py-3">
          <div>
            <p className="text-xs font-medium text-gray-400 mb-1">Session Token Usage</p>
            <div className="flex gap-4 text-xs">
              <span className="text-white font-mono">{tokens.total.toLocaleString()} total</span>
              <span className="text-gray-500">{tokens.prompt.toLocaleString()} prompt</span>
              <span className="text-gray-500">{tokens.completion.toLocaleString()} completion</span>
              <span className="text-gray-500">{tokens.calls} calls</span>
            </div>
          </div>
          <button onClick={() => resetTokens.mutate()}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
            Reset
          </button>
        </div>
      )}

      {/* Existing providers */}
      {settings.length > 0 && (
        <ul className="space-y-2">
          {settings.map(s => (
            <li key={s.id}>
              <div className="flex items-center justify-between bg-gray-800 rounded-xl px-4 py-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-white capitalize">{s.provider}</p>
                    {s.ai_scorer_enabled && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-brand-900 text-brand-400">Scorer on</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {s.model_name || 'No model set'} · {s.api_key ? 'Key stored' : 'No key'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => test.mutate(s.id)}
                    disabled={test.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors disabled:opacity-40">
                    Test
                  </button>
                  <button onClick={() => remove.mutate(s.id)}
                    className="text-xs text-red-500 hover:text-red-400 transition-colors">✕</button>
                </div>
              </div>

              {/* Inline test result */}
              {testResults[s.id] && (
                <div className={`mt-1 rounded-lg px-3 py-2 text-xs ${
                  testResults[s.id].success ? 'bg-green-950 text-green-300' : 'bg-red-950 text-red-300'
                }`}>
                  {testResults[s.id].success ? '✓' : '✗'} {testResults[s.id].message}
                  <span className="ml-2 opacity-60">({testResults[s.id].latency_ms}ms)</span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* Add / update form */}
      <div className="bg-gray-800 rounded-xl p-4 space-y-3">
        <h4 className="text-sm font-semibold text-gray-300">Add / Update Provider</h4>

        <select
          value={form.provider}
          onChange={e => setForm(f => ({ ...f, provider: e.target.value }))}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          {PROVIDERS.map(p => <option key={p} value={p} className="capitalize">{p}</option>)}
        </select>

        <input
          type="password"
          placeholder="API Key"
          value={form.api_key}
          onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />

        <input
          type="text"
          placeholder={`Model — e.g. ${MODEL_HINTS[form.provider] || 'model name'}`}
          value={form.model_name}
          onChange={e => setForm(f => ({ ...f, model_name: e.target.value }))}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />

        {needsBaseUrl && (
          <input
            type="text"
            placeholder="Base URL (e.g. http://localhost:11434/v1)"
            value={form.base_url}
            onChange={e => setForm(f => ({ ...f, base_url: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
        )}

        {/* AI Scorer toggle */}
        <div className="flex items-center justify-between py-1">
          <div>
            <p className="text-sm text-gray-300">AI Scorer</p>
            <p className="text-xs text-gray-500">Score each job listing using your API key — costs tokens per listing</p>
          </div>
          <button
            onClick={() => setForm(f => ({ ...f, ai_scorer_enabled: !f.ai_scorer_enabled }))}
            className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${
              form.ai_scorer_enabled ? 'bg-brand-500' : 'bg-gray-600'
            }`}>
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
              form.ai_scorer_enabled ? 'translate-x-5' : 'translate-x-0.5'
            }`} />
          </button>
        </div>

        <button
          onClick={() => save.mutate(form)}
          disabled={save.isPending}
          className="w-full py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors disabled:opacity-40">
          {save.isPending ? 'Saving...' : 'Save Provider'}
        </button>
      </div>
    </div>
  )
}
