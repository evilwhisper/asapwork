import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import client from '../api/client'

export default function DocumentUpload({ type }) {
  const qc = useQueryClient()
  const label = type === 'resume' ? 'Resume' : 'Cover Letter'

  const { data: docs = [] } = useQuery({
    queryKey: ['documents'],
    queryFn: () => client.get('/api/profile/documents').then(r => r.data),
  })

  const filtered = docs.filter(d => d.type === type)

  const upload = useMutation({
    mutationFn: (file) => {
      const form = new FormData()
      form.append('file', file)
      form.append('type', type)
      return client.post('/api/profile/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => { toast.success(`${label} uploaded`); qc.invalidateQueries(['documents']) },
    onError: () => toast.error('Upload failed'),
  })

  const activate = useMutation({
    mutationFn: (id) => client.put(`/api/profile/documents/${id}/activate`),
    onSuccess: () => qc.invalidateQueries(['documents']),
  })

  const remove = useMutation({
    mutationFn: (id) => client.delete(`/api/profile/documents/${id}`),
    onSuccess: () => { toast.success('Deleted'); qc.invalidateQueries(['documents']) },
  })

  const onDrop = useCallback((files) => {
    files.forEach(f => upload.mutate(f))
  }, [upload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    multiple: true,
  })

  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-300 mb-2">{label}s</h3>

      <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
        isDragActive ? 'border-brand-500 bg-brand-500/10' : 'border-gray-700 hover:border-gray-500'
      }`}>
        <input {...getInputProps()} />
        <p className="text-gray-400 text-sm">
          {isDragActive ? 'Drop it here' : `Drop PDF or DOCX here, or click to browse`}
        </p>
        {upload.isPending && <p className="text-brand-500 text-xs mt-1">Uploading...</p>}
      </div>

      {filtered.length > 0 && (
        <ul className="mt-3 space-y-2">
          {filtered.map(doc => (
            <li key={doc.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
              <div>
                <p className="text-sm text-white">{doc.filename}</p>
                <p className="text-xs text-gray-500">{new Date(doc.uploaded_at).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-2">
                {doc.is_active
                  ? <span className="text-xs px-2 py-0.5 rounded-full bg-brand-800 text-brand-300">Active</span>
                  : <button onClick={() => activate.mutate(doc.id)}
                      className="text-xs text-gray-400 hover:text-brand-400 transition-colors">Set active</button>
                }
                <button onClick={() => remove.mutate(doc.id)}
                  className="text-xs text-red-500 hover:text-red-400 transition-colors">✕</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
