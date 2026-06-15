import { useState, useEffect } from 'react'
import { Plus, Edit2, Trash2, RefreshCw, ToggleLeft, ToggleRight, X } from 'lucide-react'
import RecruiterLayout from '@/components/layout/RecruiterLayout'
import Modal from '@/components/ui/Modal'
import api from '@/lib/api'
import { cn, timeAgo } from '@/lib/utils'
import type { Job, Region } from '@/types'
import toast from 'react-hot-toast'
import { InclusionToggle } from '@/components/inclusion/InclusionToggle'

const EMPTY_FORM = {
  title: '', company: '', location: '', employment_type: 'Full-time',
  description: '', requirements: '', skills_required: '',
  salary_min: '', salary_max: '', region_id: '', is_active: true,
}

export default function RecruiterJobs() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [regions, setRegions] = useState<Region[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editJob, setEditJob] = useState<Job | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchJobs()
    api.get('/regions').then(r => setRegions(r.data.regions)).catch(() => {})
  }, [])

  async function fetchJobs() {
    setLoading(true)
    try {
      const res = await api.get('/jobs')
      setJobs(res.data.jobs)
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  function openCreate() {
    setEditJob(null)
    setForm(EMPTY_FORM)
    setShowModal(true)
  }

  function openEdit(job: Job) {
    setEditJob(job)
    setForm({
      title: job.title,
      company: job.company || '',
      location: job.location || '',
      employment_type: job.employment_type || 'Full-time',
      description: job.description || '',
      requirements: (job.requirements || []).join('\n'),
      skills_required: (job.skills_required || []).join(', '),
      salary_min: job.salary_min != null ? String(job.salary_min) : '',
      salary_max: job.salary_max != null ? String(job.salary_max) : '',
      region_id: job.region?.id != null ? String(job.region.id) : '',
      is_active: job.is_active,
    })
    setShowModal(true)
  }

  async function saveJob() {
    if (!form.title.trim()) { toast.error('Title is required'); return }
    setSaving(true)
    try {
      const payload = {
        title: form.title.trim(),
        company: form.company.trim(),
        location: form.location.trim(),
        employment_type: form.employment_type,
        description: form.description.trim(),
        requirements: form.requirements.split('\n').map(s => s.trim()).filter(Boolean),
        skills_required: form.skills_required.split(',').map(s => s.trim()).filter(Boolean),
        salary_min: form.salary_min ? parseInt(form.salary_min) : null,
        salary_max: form.salary_max ? parseInt(form.salary_max) : null,
        region_id: form.region_id ? parseInt(form.region_id) : null,
        is_active: form.is_active,
      }
      if (editJob) {
        await api.put(`/jobs/${editJob.id}`, payload)
        toast.success('Job updated!')
      } else {
        await api.post('/jobs', payload)
        toast.success('Job posted!')
      }
      setShowModal(false)
      fetchJobs()
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to save job')
    } finally { setSaving(false) }
  }

  async function deleteJob(id: number) {
    if (!confirm('Delete this job? This cannot be undone.')) return
    try {
      await api.delete(`/jobs/${id}`)
      setJobs(j => j.filter(x => x.id !== id))
      toast.success('Job deleted')
    } catch { toast.error('Failed to delete') }
  }

  async function toggleActive(job: Job) {
    try {
      await api.put(`/jobs/${job.id}`, { is_active: !job.is_active })
      setJobs(js => js.map(j => j.id === job.id ? { ...j, is_active: !j.is_active } : j))
    } catch { toast.error('Failed to update') }
  }

  return (
    <RecruiterLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
            <p className="text-gray-500 text-sm mt-1">{jobs.length} total · {jobs.filter(j => j.is_active).length} active</p>
          </div>
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> Post Job
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16 card">
            <p className="text-gray-500 mb-4">No jobs posted yet</p>
            <button onClick={openCreate} className="btn-primary">Post your first job</button>
          </div>
        ) : (
          <div className="space-y-3">
            {jobs.map(job => (
              <div key={job.id} className="card p-5">
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{job.title}</h3>
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full',
                        job.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500',
                      )}>
                        {job.is_active ? 'Active' : 'Inactive'}
                      </span>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{job.employment_type}</span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">{job.location} · {timeAgo(job.created_at)}</p>
                    {job.skills_required?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {job.skills_required.slice(0, 5).map(s => (
                          <span key={s} className="text-xs bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded-full">{s}</span>
                        ))}
                      </div>
                    )}
                    <p className="text-sm text-gray-500 mt-2">
                      <span className="font-medium text-gray-700">{job.application_count}</span> applicants
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button onClick={() => toggleActive(job)} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title={job.is_active ? 'Deactivate' : 'Activate'}>
                      {job.is_active
                        ? <ToggleRight className="w-5 h-5 text-green-600" />
                        : <ToggleLeft className="w-5 h-5 text-gray-400" />}
                    </button>
                    <button onClick={() => openEdit(job)} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors">
                      <Edit2 className="w-4 h-4 text-gray-500" />
                    </button>
                    <button onClick={() => deleteJob(job.id)} className="p-1.5 rounded-lg hover:bg-red-50 transition-colors">
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      <Modal open={showModal} onClose={() => setShowModal(false)} title={editJob ? 'Edit Job' : 'Post a Job'} size="xl">
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="label">Job Title *</label>
              <input className="input" placeholder="Senior Software Engineer" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
            </div>
            <div>
              <label className="label">Company</label>
              <input className="input" placeholder="Acme Corp" value={form.company} onChange={e => setForm(f => ({ ...f, company: e.target.value }))} />
            </div>
            <div>
              <label className="label">Location</label>
              <input className="input" placeholder="Remote / New York" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} />
            </div>
            <div>
              <label className="label">Employment Type</label>
              <select className="input" value={form.employment_type} onChange={e => setForm(f => ({ ...f, employment_type: e.target.value }))}>
                <option>Full-time</option>
                <option>Part-time</option>
                <option>Contract</option>
                <option>Internship</option>
              </select>
            </div>
            <div>
              <label className="label">Region</label>
              <select className="input" value={form.region_id} onChange={e => setForm(f => ({ ...f, region_id: e.target.value }))}>
                <option value="">No region</option>
                {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Min Salary (USD)</label>
              <input className="input" type="number" placeholder="80000" value={form.salary_min} onChange={e => setForm(f => ({ ...f, salary_min: e.target.value }))} />
            </div>
            <div>
              <label className="label">Max Salary (USD)</label>
              <input className="input" type="number" placeholder="120000" value={form.salary_max} onChange={e => setForm(f => ({ ...f, salary_max: e.target.value }))} />
            </div>
          </div>

          <div>
            <label className="label">Job Description</label>
            <textarea className="input resize-none" rows={4} placeholder="Describe the role, responsibilities, and what you're looking for…" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          </div>

          <div>
            <label className="label">Required Skills (comma-separated)</label>
            <input className="input" placeholder="React, TypeScript, Node.js, PostgreSQL" value={form.skills_required} onChange={e => setForm(f => ({ ...f, skills_required: e.target.value }))} />
          </div>

          <div>
            <label className="label">Requirements (one per line)</label>
            <textarea className="input resize-none" rows={3} placeholder="5+ years of experience&#10;Strong communication skills&#10;Experience with cloud platforms" value={form.requirements} onChange={e => setForm(f => ({ ...f, requirements: e.target.value }))} />
          </div>

          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active" checked={form.is_active} onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} className="rounded" />
            <label htmlFor="is_active" className="text-sm text-gray-700">Post as active (visible to candidates)</label>
          </div>

          {/* Inclusion Agent Toggle - Only show when editing an existing job */}
          {editJob && (
            <div className="pt-2">
              <InclusionToggle jobId={editJob.id} variant="card" />
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button onClick={() => setShowModal(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
            <button onClick={saveJob} disabled={saving} className="btn-primary flex-1 justify-center">
              {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : null}
              {editJob ? 'Save Changes' : 'Post Job'}
            </button>
          </div>
        </div>
      </Modal>
    </RecruiterLayout>
  )
}