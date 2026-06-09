import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'
import ApiKeyPanel from '../components/ApiKeyPanel'

const SOURCES = ['seek', 'indeed_au', 'linkedin_au', 'jora']
const PLUGINS = ['LinkedIn Global', 'Indeed International', 'Glassdoor']

export default function Settings() {
  const qc = useQueryClient()

  const { data: scrapers = [] } = useQuery({
    queryKey: ['scrapers'],
    queryFn: () => client.get('/api/settings/scrapers').then(r => r.data),
  })

  const { data: allApiSettings = [] } = useQuery({
    queryKey: ['api-settings'],
    queryFn: () => client.get('/api/settings/api').then(r => r.data),
  })

  const updateScraper = useMutation({
    mutationFn: ({ source, data }) => client.put(`/api/settings/scrapers/${source}`, data),
    onSuccess: () => { toast.success('Scraper saved'); qc.invalidateQueries(['scrapers']) },
    onError: () => toast.error('Save failed'),
  })

  const saveSmtp = useMutation({
    mutationFn: (data) => client.post('/api/settings/api', data),
    onSuccess: () => { toast.success('SMTP settings saved'); qc.invalidateQueries(['api-settings']) },
    onError: () => toast.error('Save failed'),
  })

  const sendTest = useMutation({
    mutationFn: () => client.post('/api/notifications/test'),
    onSuccess: () => toast.success('Test email sent — check your inbox'),
    onError: (e) => toast.error(e.response?.data?.detail || 'Email failed'),
  })

  const getConfig = (source) => scrapers.find(s => s.source === source) || {}

  // Find existing SMTP config (stored against a provider entry that has smtp_host)
  const smtpConfig = allApiSettings.find(s => s.smtp_host) || {}

  return (
    <div className="max-w-2xl space-y-10">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      {/* ── AI Providers ───────────────────────────────────── */}
      <section>
        <SectionHeader title="AI Provider" subtitle="Add your API key. All AI costs go directly to your provider." />
        <ApiKeyPanel />
      </section>

      {/* ── Job Board Scrapers ────────────────────────────── */}
      <section>
        <SectionHeader title="Job Board Scrapers" subtitle="Configure which boards to search and how often." />
        <div className="space-y-4">
          {SOURCES.map(source => (
            <ScraperCard
              key={source}
              source={source}
              config={getConfig(source)}
              onSave={(data) => updateScraper.mutate({ source, data })}
            />
          ))}
        </div>

        <div className="mt-4">
          <p className="text-xs font-medium text-gray-600 mb-2 uppercase tracking-wide">Coming Soon</p>
          <div className="space-y-2">
            {PLUGINS.map(p => (
              <div key={p} className="flex items-center justify-between bg-gray-900/40 border border-gray-800 rounded-lg px-4 py-3">
                <p className="text-sm text-gray-600">{p}</p>
                <span className="text-xs bg-gray-800 text-gray-600 px-2 py-0.5 rounded-full">Coming soon</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── SMTP / Email ──────────────────────────────────── */}
      <section>
        <SectionHeader
          title="Email Notifications & Submission"
          subtitle="Used for daily digests and email-based job applications."
        />
        <SmtpForm existing={smtpConfig} onSave={saveSmtp.mutate} saving={saveSmtp.isPending} />
        <div className="mt-3 flex gap-3">
          <button
            onClick={() => sendTest.mutate()}
            disabled={sendTest.isPending || !smtpConfig.smtp_host}
            className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition-colors disabled:opacity-40">
            {sendTest.isPending ? 'Sending...' : 'Send Test Email'}
          </button>
          {!smtpConfig.smtp_host && (
            <p className="text-xs text-gray-600 self-center">Save SMTP settings above first</p>
          )}
        </div>
      </section>

      {/* ── Submission Rate ───────────────────────────────── */}
      <section>
        <SectionHeader title="Submission Rate Limits" subtitle="Control how aggressively the agent applies." />
        <SubmissionRateForm existing={smtpConfig} onSave={saveSmtp.mutate} saving={saveSmtp.isPending} />
      </section>
    </div>
  )
}

/* ── Sub-components ─────────────────────────────────────────── */

function SectionHeader({ title, subtitle }) {
  return (
    <div className="mb-4">
      <h2 className="text-base font-semibold text-gray-200">{title}</h2>
      {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  )
}

function SmtpForm({ existing, onSave, saving }) {
  const [form, setForm] = useState({
    provider: existing.provider || 'custom',
    smtp_host: existing.smtp_host || '',
    smtp_port: existing.smtp_port || 587,
    smtp_user: existing.smtp_user || '',
    smtp_pass: '',
    notify_email: existing.notify_email || '',
  })

  useEffect(() => {
    setForm(f => ({
      ...f,
      provider: existing.provider || 'custom',
      smtp_host: existing.smtp_host || '',
      smtp_port: existing.smtp_port || 587,
      smtp_user: existing.smtp_user || '',
      notify_email: existing.notify_email || '',
    }))
  }, [existing.smtp_host])

  const F = ({ label, field, type = 'text', placeholder, half }) => (
    <div className={half ? 'col-span-1' : 'col-span-2'}>
      <label className="block text-xs font-medium text-gray-400 mb-1">{label}</label>
      <input type={type} placeholder={placeholder}
        value={form[field] || ''}
        onChange={e => setForm(f => ({ ...f, [field]: type === 'number' ? Number(e.target.value) : e.target.value }))}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
    </div>
  )

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="grid grid-cols-2 gap-3">
        <F label="SMTP Host" field="smtp_host" placeholder="smtp.gmail.com" />
        <div className="col-span-2 grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">Port</label>
            <input type="number" value={form.smtp_port}
              onChange={e => setForm(f => ({ ...f, smtp_port: Number(e.target.value) }))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-400 mb-1">Username / Email</label>
            <input type="text" placeholder="you@gmail.com" value={form.smtp_user}
              onChange={e => setForm(f => ({ ...f, smtp_user: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
          </div>
        </div>
        <F label="Password / App Password" field="smtp_pass" type="password" placeholder="Leave blank to keep existing" />
        <F label="Notify Email (digest recipient)" field="notify_email" placeholder="you@gmail.com" />
      </div>
      <p className="text-xs text-gray-600 mt-2">
        For Gmail: use an <a href="https://support.google.com/accounts/answer/185833" target="_blank" rel="noopener noreferrer" className="text-brand-500 hover:underline">App Password</a> — not your main password.
      </p>
      <button
        onClick={() => onSave(form)}
        disabled={saving}
        className="mt-3 w-full py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition-colors disabled:opacity-40">
        {saving ? 'Saving...' : 'Save SMTP Settings'}
      </button>
    </div>
  )
}

function SubmissionRateForm({ existing, onSave, saving }) {
  const [form, setForm] = useState({
    provider: existing.provider || 'custom',
    max_submissions_per_hour: existing.max_submissions_per_hour ?? 10,
    min_gap_minutes: existing.min_gap_minutes ?? 3,
    auto_submit: existing.auto_submit ?? false,
    auto_approve_threshold: existing.auto_approve_threshold ?? null,
  })

  useEffect(() => {
    setForm(f => ({
      ...f,
      max_submissions_per_hour: existing.max_submissions_per_hour ?? 10,
      min_gap_minutes: existing.min_gap_minutes ?? 3,
      auto_submit: existing.auto_submit ?? false,
      auto_approve_threshold: existing.auto_approve_threshold ?? null,
    }))
  }, [existing.max_submissions_per_hour])

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Max submissions / hour</label>
          <input type="number" min={1} max={50} value={form.max_submissions_per_hour}
            onChange={e => setForm(f => ({ ...f, max_submissions_per_hour: Number(e.target.value) }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-400 mb-1">Min gap between submissions (min)</label>
          <input type="number" min={1} max={60} value={form.min_gap_minutes}
            onChange={e => setForm(f => ({ ...f, min_gap_minutes: Number(e.target.value) }))}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
        </div>
      </div>

      {/* Auto-submit toggle */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-300">Auto-submit on approval</p>
          <p className="text-xs text-gray-500">Submit immediately when you click Approve — skips the manual Submit step</p>
        </div>
        <button
          onClick={() => setForm(f => ({ ...f, auto_submit: !f.auto_submit }))}
          className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${form.auto_submit ? 'bg-brand-500' : 'bg-gray-600'}`}>
          <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.auto_submit ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>

      {/* Auto-approve threshold */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <div>
            <p className="text-sm text-gray-300">Auto-approve threshold</p>
            <p className="text-xs text-gray-500">Automatically approve applications above this match score (requires AI Scorer)</p>
          </div>
          <button
            onClick={() => setForm(f => ({ ...f, auto_approve_threshold: f.auto_approve_threshold !== null ? null : 0.75 }))}
            className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${form.auto_approve_threshold !== null ? 'bg-brand-500' : 'bg-gray-600'}`}>
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${form.auto_approve_threshold !== null ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </div>
        {form.auto_approve_threshold !== null && (
          <div className="flex items-center gap-3 mt-2">
            <input type="range" min={50} max={95} step={5}
              value={Math.round((form.auto_approve_threshold ?? 0.75) * 100)}
              onChange={e => setForm(f => ({ ...f, auto_approve_threshold: Number(e.target.value) / 100 }))}
              className="flex-1 accent-brand-500" />
            <span className="text-sm font-mono text-white w-10 text-right">
              {Math.round((form.auto_approve_threshold ?? 0.75) * 100)}%
            </span>
          </div>
        )}
      </div>

      <button
        onClick={() => onSave(form)}
        disabled={saving}
        className="w-full py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition-colors disabled:opacity-40">
        {saving ? 'Saving...' : 'Save Rate Settings'}
      </button>
    </div>
  )
}

function ScraperCard({ source, config, onSave }) {
  const [local, setLocal] = useState({
    enabled: config.enabled ?? false,
    keywords: Array.isArray(config.keywords) ? config.keywords.join(', ') : '',
    location: config.location || '',
    schedule_hours: config.schedule_hours ?? 2,
    linkedin_session_cookie: '',
  })

  useEffect(() => {
    setLocal(l => ({
      ...l,
      enabled: config.enabled ?? false,
      keywords: Array.isArray(config.keywords) ? config.keywords.join(', ') : '',
      location: config.location || '',
      schedule_hours: config.schedule_hours ?? 2,
    }))
  }, [config.source])

  const isLinkedIn = source === 'linkedin_au'
  const sourceLabel = source.replace('_au', ' AU').replace('_', ' ')

  const handleSave = () => onSave({
    ...local,
    enabled: local.enabled,
    keywords: local.keywords.split(',').map(k => k.trim()).filter(Boolean),
    source,
  })

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              const next = { ...local, enabled: !local.enabled }
              setLocal(next)
              onSave({ ...next, keywords: next.keywords.split(',').map(k => k.trim()).filter(Boolean), source })
            }}
            className={`w-10 h-5 rounded-full transition-colors relative ${local.enabled ? 'bg-brand-500' : 'bg-gray-700'}`}>
            <span className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${local.enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
          <span className="text-sm font-medium text-white capitalize">{sourceLabel}</span>
        </div>
        {config.last_run && (
          <span className="text-xs text-gray-600">
            Last run: {new Date(config.last_run).toLocaleString()}
          </span>
        )}
      </div>

      <div className="space-y-2">
        <input
          value={local.keywords}
          onChange={e => setLocal(l => ({ ...l, keywords: e.target.value }))}
          placeholder="Keywords (comma-separated, e.g. software engineer, python)"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />

        <div className="flex gap-2">
          <input
            value={local.location}
            onChange={e => setLocal(l => ({ ...l, location: e.target.value }))}
            placeholder="Location (e.g. Sydney, NSW)"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-xs text-gray-500">Every</span>
            <input type="number" min={1} max={24} value={local.schedule_hours}
              onChange={e => setLocal(l => ({ ...l, schedule_hours: Number(e.target.value) }))}
              className="w-14 bg-gray-800 border border-gray-700 rounded-lg px-2 py-2 text-sm text-white text-center focus:outline-none focus:border-brand-500" />
            <span className="text-xs text-gray-500">hrs</span>
          </div>
        </div>

        {isLinkedIn && (
          <div>
            <input
              type="password"
              value={local.linkedin_session_cookie}
              onChange={e => setLocal(l => ({ ...l, linkedin_session_cookie: e.target.value }))}
              placeholder="LinkedIn li_at session cookie (paste to update)"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
            <p className="text-xs text-gray-600 mt-1">
              Chrome DevTools → Application → Cookies → www.linkedin.com → copy <code className="bg-gray-800 px-1 rounded">li_at</code>
            </p>
          </div>
        )}

        <button
          onClick={handleSave}
          className="w-full py-2 rounded-lg bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 text-sm font-medium transition-colors">
          Save
        </button>
      </div>
    </div>
  )
}
