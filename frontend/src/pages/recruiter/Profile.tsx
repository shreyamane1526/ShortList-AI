import { useState } from 'react'
import { Save, RefreshCw } from 'lucide-react'
import RecruiterLayout from '@/components/layout/RecruiterLayout'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import toast from 'react-hot-toast'

export default function RecruiterProfile() {
  const { user, refreshUser } = useAuth()
  const recruiter = user?.recruiter

  const [companyName, setCompanyName] = useState(recruiter?.company_name || '')
  const [jobTitle, setJobTitle] = useState(recruiter?.job_title || '')
  const [saving, setSaving] = useState(false)

  async function save() {
    setSaving(true)
    try {
      await api.put('/me/profile', { company_name: companyName, job_title: jobTitle })
      await refreshUser()
      toast.success('Profile saved!')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to save')
    } finally { setSaving(false) }
  }

  return (
    <RecruiterLayout>
      <div className="p-6 max-w-lg mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
        </div>

        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Account</h2>
          <div>
            <label className="label">Full Name</label>
            <input className="input" value={user?.full_name || ''} disabled />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" value={user?.email || ''} disabled />
          </div>
        </div>

        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Company</h2>
          <div>
            <label className="label">Company Name</label>
            <input className="input" placeholder="Acme Corp" value={companyName} onChange={e => setCompanyName(e.target.value)} />
          </div>
          <div>
            <label className="label">Your Job Title</label>
            <input className="input" placeholder="Head of Engineering" value={jobTitle} onChange={e => setJobTitle(e.target.value)} />
          </div>
        </div>
      </div>
    </RecruiterLayout>
  )
}
