import { useState, useEffect } from 'react'
import { Save, Upload, Plus, Trash2, RefreshCw, Brain } from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import type { Region } from '@/types'
import toast from 'react-hot-toast'
import { CharCounter, FieldHelper } from '@/components/accessibility/FormHelpers'

export default function CandidateProfile() {
  const { user, refreshUser } = useAuth()
  const candidate = user?.candidate

  const [headline, setHeadline] = useState(candidate?.headline || '')
  const [location, setLocation] = useState(candidate?.location || '')
  const [summary, setSummary] = useState(candidate?.summary || '')
  const [years, setYears] = useState(String(candidate?.years_experience || ''))
  const [github, setGithub] = useState(candidate?.github_username || '')
  const [leetcode, setLeetcode] = useState(candidate?.leetcode_username || '')
  const [skillInput, setSkillInput] = useState('')
  const [skills, setSkills] = useState<string[]>(candidate?.skills || [])
  const [projects, setProjects] = useState(candidate?.projects || [])
  const [neurodivergent, setNeurodivergent] = useState<boolean | null>(candidate?.neurodivergent ?? null)
  const [ndType, setNdType] = useState(candidate?.nd_type || '')
  const [regionId, setRegionId] = useState<number | ''>(candidate?.preferred_region?.id || '')
  const [regions, setRegions] = useState<Region[]>([])
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [enriching, setEnriching] = useState(false)

  useEffect(() => {
    api.get('/regions').then(r => setRegions(r.data.regions)).catch(() => {})
  }, [])

  function addSkill() {
    const s = skillInput.trim()
    if (s && !skills.includes(s)) { setSkills(sk => [...sk, s]); setSkillInput('') }
  }

  function removeSkill(s: string) { setSkills(sk => sk.filter(x => x !== s)) }

  function addProject() { setProjects(p => [...p, { name: '', description: '', url: '' }]) }
  function removeProject(i: number) { setProjects(p => p.filter((_, idx) => idx !== i)) }
  function updateProject(i: number, field: string, val: string) {
    setProjects(p => p.map((pr, idx) => idx === i ? { ...pr, [field]: val } : pr))
  }

  async function saveProfile() {
    setSaving(true)
    try {
      await api.put('/me/profile', {
        headline, location, summary,
        years_experience: years ? parseInt(years) : null,
        skills,
        projects: projects.filter(p => p.name),
        github_username: github || null,
        leetcode_username: leetcode || null,
        preferred_region_id: regionId || null,
        neurodivergent,
        nd_type: neurodivergent === true ? ndType || null : null,
      })
      await refreshUser()
      toast.success('Profile saved!')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to save')
    } finally { setSaving(false) }
  }

  async function runEnrichment() {
    setEnriching(true)
    try {
      const form = new FormData()
      if (github) form.append('github_username', github)
      if (leetcode) form.append('leetcode_username', leetcode)
      if (resumeFile) form.append('resume', resumeFile)
      await api.post('/me/profile/enrich', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      toast.success('AI analysis started! Check your dashboard for results.')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to start enrichment')
    } finally { setEnriching(false) }
  }

  return (
    <CandidateLayout>
      <div className="p-6 max-w-2xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
            <p className="text-gray-500 text-sm mt-1">Keep your profile up to date for better job matches</p>
          </div>
          <button onClick={saveProfile} disabled={saving} className="btn-primary">
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
        </div>

        {/* Basic Info */}
        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Basic Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Full Name</label>
              <input className="input" value={user?.full_name || ''} disabled />
            </div>
            <div>
              <label className="label">Email</label>
              <input className="input" value={user?.email || ''} disabled />
            </div>
          </div>
          <div>
            <label className="label" htmlFor="profile-headline">Professional Headline</label>
            <input
              id="profile-headline"
              className="input"
              placeholder="e.g. Full-Stack Engineer"
              value={headline}
              onChange={e => setHeadline(e.target.value)}
              aria-describedby="profile-headline-helper"
            />
            <FieldHelper id="profile-headline-helper">
              A short phrase describing your role and main skills. Example: "Full-Stack Engineer | React + Python".
            </FieldHelper>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Location</label>
              <input className="input" placeholder="San Francisco, CA" value={location} onChange={e => setLocation(e.target.value)} />
            </div>
            <div>
              <label className="label">Years of Experience</label>
              <input className="input" type="number" min="0" value={years} onChange={e => setYears(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label" htmlFor="profile-summary">Summary</label>
            <textarea
              id="profile-summary"
              className="input resize-none"
              rows={3}
              value={summary}
              onChange={e => setSummary(e.target.value)}
              aria-describedby="profile-summary-helper"
            />
            <FieldHelper id="profile-summary-helper">
              Write 2–4 sentences about your background, what you build, and what you're looking for.
            </FieldHelper>
            <CharCounter value={summary} maxChars={500} showWords />
          </div>
          <div>
            <label className="label">Preferred Region</label>
            <select className="input" value={regionId} onChange={e => setRegionId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">No preference</option>
              {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
        </div>

        {/* Neurodiversity Support */}
        <div className="card p-5 space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-green-50 text-green-700 flex items-center justify-center shrink-0">
              <Brain className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Neurodiversity Support (Optional)</h2>
              <p className="text-sm text-gray-500 mt-1">
                This information is optional and used only to improve fairness in evaluation.
                It will not negatively impact your application.
              </p>
            </div>
          </div>

          <div>
            <p className="label">Are you neurodivergent? (Optional)</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {[
                { label: 'Yes', value: true },
                { label: 'No', value: false },
                { label: 'Prefer not to say', value: null },
              ].map(option => (
                <label
                  key={option.label}
                  className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 cursor-pointer hover:bg-gray-50"
                >
                  <input
                    type="radio"
                    name="neurodivergent"
                    checked={neurodivergent === option.value}
                    onChange={() => {
                      setNeurodivergent(option.value)
                      if (option.value !== true) setNdType('')
                    }}
                    className="accent-brand-600"
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>

          {neurodivergent === true && (
            <div>
              <label className="label">Select type (optional)</label>
              <select className="input" value={ndType} onChange={e => setNdType(e.target.value)}>
                <option value="">No specific type</option>
                <option value="adhd">ADHD</option>
                <option value="dyslexia">Dyslexia</option>
                <option value="autism">Autism</option>
                <option value="other">Other</option>
              </select>
            </div>
          )}
        </div>

        {/* AI Enrichment */}
        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">AI Profile Analysis</h2>
          <p className="text-sm text-gray-500">Connect your profiles to let AI agents analyze your skills automatically.</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">GitHub Username</label>
              <input className="input" placeholder="octocat" value={github} onChange={e => setGithub(e.target.value)} />
            </div>
            <div>
              <label className="label">LeetCode Username</label>
              <input className="input" placeholder="leetcoder" value={leetcode} onChange={e => setLeetcode(e.target.value)} />
            </div>
          </div>
          <div>
            <label className="label">Resume (PDF/DOC/DOCX)</label>
            <div className="flex gap-3 items-center">
              <label className="btn-secondary cursor-pointer">
                <Upload className="w-4 h-4" />
                {resumeFile ? resumeFile.name : candidate?.resume_url ? 'Replace Resume' : 'Upload Resume'}
                <input type="file" className="hidden" accept=".pdf,.doc,.docx,.txt" onChange={e => setResumeFile(e.target.files?.[0] || null)} />
              </label>
              {candidate?.resume_url && !resumeFile && (
                <span className="text-xs text-green-600">✓ Resume on file</span>
              )}
            </div>
          </div>
          <button onClick={runEnrichment} disabled={enriching} className="btn-primary">
            {enriching ? <RefreshCw className="w-4 h-4 animate-spin" /> : '🤖'}
            {enriching ? 'Analyzing…' : 'Run AI Analysis'}
          </button>
        </div>

        {/* Skills */}
        <div className="card p-5 space-y-4">
          <h2 className="font-semibold text-gray-900">Skills</h2>
          <div className="flex gap-2">
            <input
              className="input flex-1"
              placeholder="Add a skill…"
              value={skillInput}
              onChange={e => setSkillInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addSkill()}
            />
            <button onClick={addSkill} className="btn-secondary"><Plus className="w-4 h-4" /></button>
          </div>
          <div className="flex flex-wrap gap-2">
            {skills.map(s => (
              <span key={s} className="flex items-center gap-1 text-sm bg-brand-50 text-brand-700 border border-brand-200 px-2.5 py-1 rounded-full">
                {s}
                <button onClick={() => removeSkill(s)} className="text-brand-400 hover:text-brand-700 ml-0.5">×</button>
              </span>
            ))}
          </div>
          {candidate?.resume_skills?.length ? (
            <div>
              <p className="text-xs text-gray-500 mb-2">From resume analysis:</p>
              <div className="flex flex-wrap gap-1.5">
                {candidate.resume_skills.map(s => (
                  <button
                    key={s}
                    onClick={() => { if (!skills.includes(s)) setSkills(sk => [...sk, s]) }}
                    className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full hover:bg-brand-50 hover:text-brand-700 transition-colors"
                  >
                    + {s}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* Projects */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Projects</h2>
            <button onClick={addProject} className="btn-secondary text-xs"><Plus className="w-3 h-3" /> Add</button>
          </div>
          {projects.map((p, i) => (
            <div key={i} className="border border-gray-200 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">Project {i + 1}</span>
                <button onClick={() => removeProject(i)} className="text-red-400 hover:text-red-600">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <input className="input" placeholder="Project name" value={p.name} onChange={e => updateProject(i, 'name', e.target.value)} />
              <textarea className="input resize-none" rows={2} placeholder="Description" value={p.description} onChange={e => updateProject(i, 'description', e.target.value)} />
              <input className="input" placeholder="URL (optional)" value={p.url || ''} onChange={e => updateProject(i, 'url', e.target.value)} />
            </div>
          ))}
          {projects.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-4">No projects added yet</p>
          )}
        </div>
      </div>
    </CandidateLayout>
  )
}
