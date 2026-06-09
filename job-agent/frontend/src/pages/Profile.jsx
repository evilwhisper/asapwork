import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'
import DocumentUpload from '../components/DocumentUpload'

const TONES = ['professional', 'conversational', 'technical']
const WORK_TYPES = ['remote', 'hybrid', 'onsite']

export default function Profile() {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    name: '', email: '', phone: '', location: '',
    target_roles: [], target_salary_min: '', target_salary_max: '',
    work_types: [], industries: [], blacklist_keywords: [],
    whitelist_companies: [], tone_preference: 'professional',
  })
  const [tagInputs, setTagInputs] = useState({
    target_roles: '', industries: '', blacklist_keywords: '', whitelist_companies: '',
  })

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: () => client.get('/api/profile').then(r => r.data),
  })

  useEffect(() => {
    if (profile) setForm(f => ({ ...f, ...profile }))
  }, [profile])

  const save = useMutation({
    mutationFn: () => client.put('/api/profile', form),
    onSuccess: () => { toast.success('Profile saved'); qc.invalidateQueries(['profile']) },
    onError: () => toast.error('Save failed'),
  })

  const toggleWorkType = (wt) => setForm(f => ({
    ...f,
    work_types: f.work_types.includes(wt)
      ? f.work_types.filter(x => x !== wt)
      : [...f.work_types, wt],
  }))

  const addTag = (field) => {
    const val = tagInputs[field].trim()
    if (!val || form[field].includes(val)) return
    setForm(f => ({ ...f, [field]: [...f[field], val] }))
    setTagInputs(t => ({ ...t, [field]: '' }))
  }

  const removeTag = (field, val) => setForm(f => ({ ...f, [field]: f[field].filter(x => x !== val) }))

  const Field = ({ label, field, type = 'text', placeholder }) => (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1">{label}</label>
      <input type={type} placeholder={placeholder}
        value={form[field] || ''}
        onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
    </div>
  )

  const TagInput = ({ label, field, placeholder }) => (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1">{label}</label>
      <div className="flex gap-2 mb-2">
        <input
          value={tagInputs[field]}
          onChange={e => setTagInputs(t => ({ ...t, [field]: e.target.value }))}
          onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addTag(field))}
          placeholder={placeholder}
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500" />
        <button onClick={() => addTag(field)}
          className="px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm text-white transition-colors">Add</button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(form[field] || []).map(tag => (
          <span key={tag} className="flex items-center gap-1 bg-gray-700 text-gray-200 text-xs px-2 py-1 rounded-full">
            {tag}
            <button onClick={() => removeTag(field, tag)} className="text-gray-400 hover:text-white">✕</button>
          </span>
        ))}
      </div>
    </div>
  )

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-bold text-white mb-6">Profile</h1>

      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full Name" field="name" placeholder="Jane Smith" />
          <Field label="Email" field="email" type="email" placeholder="jane@example.com" />
          <Field label="Phone" field="phone" placeholder="+61 4xx xxx xxx" />
          <Field label="Location" field="location" placeholder="Sydney, NSW" />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Min Salary (AUD)" field="target_salary_min" type="number" placeholder="80000" />
          <Field label="Max Salary (AUD)" field="target_salary_max" type="number" placeholder="120000" />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">Work Type</label>
          <div className="flex gap-3">
            {WORK_TYPES.map(wt => (
              <button key={wt} onClick={() => toggleWorkType(wt)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                  form.work_types?.includes(wt)
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}>
                {wt}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-400 mb-2">Tone Preference</label>
          <div className="flex gap-3">
            {TONES.map(t => (
              <button key={t} onClick={() => setForm(f => ({ ...f, tone_preference: t }))}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                  form.tone_preference === t
                    ? 'bg-brand-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}>
                {t}
              </button>
            ))}
          </div>
        </div>

        <TagInput label="Target Roles" field="target_roles" placeholder="Software Engineer" />
        <TagInput label="Industries" field="industries" placeholder="Technology" />
        <TagInput label="Blacklist Keywords" field="blacklist_keywords" placeholder="unpaid, commission" />
        <TagInput label="Whitelist Companies" field="whitelist_companies" placeholder="Google, Atlassian" />

        <button onClick={() => save.mutate()} disabled={save.isPending}
          className="w-full py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-medium transition-colors disabled:opacity-40">
          {save.isPending ? 'Saving...' : 'Save Profile'}
        </button>

        {/* Documents */}
        <div className="border-t border-gray-800 pt-6 space-y-6">
          <DocumentUpload type="resume" />
          <DocumentUpload type="cover_letter" />
        </div>
      </div>
    </div>
  )
}
