import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Github, Code2, Upload, Plus, Trash2, CheckCircle2, Loader2, Zap } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import api from '@/lib/api'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'
import { CharCounter, FieldHelper } from '@/components/accessibility/FormHelpers'

interface Project { name: string; description: string; url: string }

const STEPS = ['Profile', 'GitHub & LeetCode', 'Resume', 'Projects', 'Done']

export default function CandidateOnboarding() {
  const { refreshUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [loading, setLoading] = useState(false)

  // Step 0 — basic profile
  const [headline, setHeadline] = useState('')
  const [location, setLocation] = useState('')
  const [summary, setSummary] = useState('')
  const [years, setYears] = useState('')

  // Step 1 — usernames
  const [github, setGithub] = useState('')
  const [leetcode, setLeetcode] = useState('')

  // Step 2 — resume
  const [resumeFile, setResumeFile] = useState<File | null>(null)

  // Step 3 — projects
  const [projects, setProjects] = useState<Project[]>([{ name: '', description: '', url: '' }])

  function addProject() { setProjects(p => [...p, { name: '', description: '', url: '' }]) }
  function removeProject(i: number) { setProjects(p => p.filter((_, idx) => idx !== i)) }
  function updateProject(i: number, field: keyof Project, val: string) {
    setProjects(p => p.map((pr, idx) => idx === i ? { ...pr, [field]: val } : pr))
  }

  async function handleFinish() {
    setLoading(true)
    try {
      // 1. Save basic profile + projects
      await api.put('/me/profile', {
        headline,
        location,
        summary,
        years_experience: years ? parseInt(years) : null,
        projects: projects.filter(p => p.name.trim()),
      })

      // 2. Enrich (GitHub + LeetCode + resume)
      const form = new FormData()
      if (github.trim()) form.append('github_username', github.trim())
      if (leetcode.trim()) form.append('leetcode_username', leetcode.trim())
      if (resumeFile) form.append('resume', resumeFile)

      if (github.trim() || leetcode.trim() || resumeFile) {
        await api.post('/me/profile/enrich', form, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }

      await refreshUser()
      toast.success('Profile created! AI agents are analyzing your profile.')
      navigate('/candidate')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to save profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-white to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-bold text-gray-900">Shortlist AI</span>
          </div>
        </div>

        {/* Progress */}
        <div className="flex items-center gap-1 mb-6">
          {STEPS.map((s, i) => (
            <div key={s} className="flex items-center flex-1">
              <div className={cn(
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all',
                i < step ? 'bg-brand-600 text-white' :
                i === step ? 'bg-brand-600 text-white ring-4 ring-brand-100' :
                'bg-gray-200 text-gray-500',
              )}>
                {i < step ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn('flex-1 h-0.5 mx-1', i < step ? 'bg-brand-600' : 'bg-gray-200')} />
              )}
            </div>
          ))}
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">{STEPS[step]}</h2>

          {/* Step 0 — Basic profile */}
          {step === 0 && (
            <div className="space-y-4 mt-4">
              <div>
                <label className="label" htmlFor="onboard-headline">Professional Headline</label>
                <input
                  id="onboard-headline"
                  className="input"
                  placeholder="e.g. Full-Stack Engineer | React + Python"
                  value={headline}
                  onChange={e => setHeadline(e.target.value)}
                  aria-describedby="onboard-headline-helper"
                />
                <FieldHelper id="onboard-headline-helper">
                  A short phrase describing your role. Example: "Backend Engineer | Python + AWS".
                </FieldHelper>
              </div>
              <div>
                <label className="label" htmlFor="onboard-location">Location</label>
                <input
                  id="onboard-location"
                  className="input"
                  placeholder="e.g. San Francisco, CA"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                  aria-describedby="onboard-location-helper"
                />
                <FieldHelper id="onboard-location-helper">
                  City and country or state. Used to match you with relevant jobs.
                </FieldHelper>
              </div>
              <div>
                <label className="label" htmlFor="onboard-summary">Summary</label>
                <textarea
                  id="onboard-summary"
                  className="input resize-none"
                  rows={3}
                  placeholder="Brief professional summary…"
                  value={summary}
                  onChange={e => setSummary(e.target.value)}
                  aria-describedby="onboard-summary-helper"
                />
                <FieldHelper id="onboard-summary-helper">
                  2–4 sentences about your background and what you're looking for. Keep it concise.
                </FieldHelper>
                <CharCounter value={summary} maxChars={500} showWords />
              </div>
              <div>
                <label className="label" htmlFor="onboard-years">Years of Experience</label>
                <input
                  id="onboard-years"
                  className="input"
                  type="number"
                  min="0"
                  max="50"
                  placeholder="3"
                  value={years}
                  onChange={e => setYears(e.target.value)}
                  aria-describedby="onboard-years-helper"
                />
                <FieldHelper id="onboard-years-helper">
                  Total years of professional work experience. Enter 0 if you're a student or new graduate.
                </FieldHelper>
              </div>
            </div>
          )}

          {/* Step 1 — GitHub & LeetCode */}
          {step === 1 && (
            <div className="space-y-4 mt-4">
              <p className="text-sm text-gray-500">AI agents will analyze your public profiles to build your skill evidence.</p>
              <div>
                <label className="label flex items-center gap-2"><Github className="w-4 h-4" /> GitHub Username</label>
                <input className="input" placeholder="octocat" value={github} onChange={e => setGithub(e.target.value)} />
              </div>
              <div>
                <label className="label flex items-center gap-2"><Code2 className="w-4 h-4" /> LeetCode Username</label>
                <input className="input" placeholder="leetcoder123" value={leetcode} onChange={e => setLeetcode(e.target.value)} />
              </div>
            </div>
          )}

          {/* Step 2 — Resume */}
          {step === 2 && (
            <div className="mt-4">
              <p className="text-sm text-gray-500 mb-4">Upload your resume to extract skills and experience automatically.</p>
              <label className={cn(
                'flex flex-col items-center justify-center w-full h-36 border-2 border-dashed rounded-xl cursor-pointer transition-colors',
                resumeFile ? 'border-brand-400 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50',
              )}>
                <Upload className={cn('w-8 h-8 mb-2', resumeFile ? 'text-brand-500' : 'text-gray-400')} />
                {resumeFile ? (
                  <span className="text-sm font-medium text-brand-700">{resumeFile.name}</span>
                ) : (
                  <>
                    <span className="text-sm font-medium text-gray-600">Click to upload resume</span>
                    <span className="text-xs text-gray-400 mt-1">PDF, DOC, DOCX, TXT</span>
                  </>
                )}
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={e => setResumeFile(e.target.files?.[0] || null)}
                />
              </label>
              {resumeFile && (
                <button onClick={() => setResumeFile(null)} className="mt-2 text-xs text-red-500 hover:underline">
                  Remove file
                </button>
              )}
            </div>
          )}

          {/* Step 3 — Projects */}
          {step === 3 && (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-gray-500">Add notable projects (optional — AI will also find them from GitHub).</p>
              {projects.map((p, i) => (
                <div key={i} className="border border-gray-200 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">Project {i + 1}</span>
                    {projects.length > 1 && (
                      <button onClick={() => removeProject(i)} className="text-red-400 hover:text-red-600">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  <input className="input" placeholder="Project name" value={p.name} onChange={e => updateProject(i, 'name', e.target.value)} />
                  <textarea className="input resize-none" rows={2} placeholder="Brief description" value={p.description} onChange={e => updateProject(i, 'description', e.target.value)} />
                  <input className="input" placeholder="URL (optional)" value={p.url} onChange={e => updateProject(i, 'url', e.target.value)} />
                </div>
              ))}
              <button onClick={addProject} className="btn-secondary w-full justify-center">
                <Plus className="w-4 h-4" /> Add Project
              </button>
            </div>
          )}

          {/* Step 4 — Done */}
          {step === 4 && (
            <div className="text-center py-6">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">You're all set!</h3>
              <p className="text-sm text-gray-500">AI agents will analyze your profile in the background. You'll see results on your dashboard.</p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-3 mt-6">
            {step > 0 && step < 4 && (
              <button onClick={() => setStep(s => s - 1)} className="btn-secondary flex-1 justify-center">
                Back
              </button>
            )}
            {step < 3 && (
              <button onClick={() => setStep(s => s + 1)} className="btn-primary flex-1 justify-center">
                Continue
              </button>
            )}
            {step === 3 && (
              <button onClick={() => { setStep(4); handleFinish() }} disabled={loading} className="btn-primary flex-1 justify-center">
                {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</> : 'Finish Setup'}
              </button>
            )}
            {step === 4 && (
              <button onClick={() => navigate('/candidate')} className="btn-primary flex-1 justify-center">
                Go to Dashboard
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
