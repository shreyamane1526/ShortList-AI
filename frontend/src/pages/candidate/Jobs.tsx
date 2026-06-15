import { useState, useEffect } from 'react'
import { Search, MapPin, Briefcase, ExternalLink, Zap, RefreshCw, Filter } from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import JobAlertBadge from '@/components/JobAlertBadge'
import api from '@/lib/api'
import { cn, timeAgo, scoreBg } from '@/lib/utils'
import type { Job, ScrapedJob, Region } from '@/types'
import toast from 'react-hot-toast'

export default function CandidateJobs() {
  const [tab, setTab] = useState<'posted' | 'scraped'>('posted')
  const [postedJobs, setPostedJobs] = useState<Job[]>([])
  const [scrapedJobs, setScrapedJobs] = useState<ScrapedJob[]>([])
  const [regions, setRegions] = useState<Region[]>([])
  const [regionId, setRegionId] = useState<number | ''>('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState<number | null>(null)
  const [expressing, setExpressing] = useState<number | null>(null)

  useEffect(() => {
    api.get('/regions').then(r => setRegions(r.data.regions)).catch(() => {})
    fetchPosted()
    fetchScraped()
  }, [])

  async function fetchPosted() {
    setLoading(true)
    try {
      const params: Record<string, any> = {}
      if (regionId) params.region_id = regionId
      const res = await api.get('/jobs', { params })
      setPostedJobs(res.data.jobs)
    } catch { /* ignore */ } finally { setLoading(false) }
  }

  async function fetchScraped() {
    try {
      const params: Record<string, any> = { limit: 50 }
      if (regionId) params.region_id = regionId
      if (search) params.q = search
      const res = await api.get('/scraped-jobs', { params })
      setScrapedJobs(res.data.jobs)
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchPosted(); fetchScraped() }, [regionId])

  async function applyToJob(jobId: number) {
    setApplying(jobId)
    try {
      await api.post(`/jobs/${jobId}/apply`, {})
      toast.success('Application submitted!')
      fetchPosted()
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Failed to apply'
      if (msg.includes('Already applied')) toast.error('You already applied to this job')
      else toast.error(msg)
    } finally { setApplying(null) }
  }

  async function expressInterest(jobId: number) {
    setExpressing(jobId)
    try {
      await api.post(`/jobs/${jobId}/express-interest`, { boost: true })
      toast.success('Interest expressed! AI evaluation queued.')
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed')
    } finally { setExpressing(null) }
  }

  const filteredPosted = postedJobs.filter(j =>
    !search || j.title.toLowerCase().includes(search.toLowerCase()) ||
    j.company_name?.toLowerCase().includes(search.toLowerCase()),
  )

  const filteredScraped = scrapedJobs.filter(j =>
    !search || j.title.toLowerCase().includes(search.toLowerCase()) ||
    j.company.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <CandidateLayout>
      <div className="p-6 max-w-4xl mx-auto space-y-5">
        <div>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Job Feed</h1>
              <p className="text-gray-500 text-sm mt-1">Browse jobs posted by recruiters and live scraped listings</p>
            </div>
            <JobAlertBadge />
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              className="input pl-9"
              placeholder="Search jobs…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchScraped()}
            />
          </div>
          <select
            className="input w-44"
            value={regionId}
            onChange={e => setRegionId(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">All Regions</option>
            {regions.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button onClick={() => { fetchPosted(); fetchScraped() }} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
          {(['posted', 'scraped'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'px-4 py-1.5 text-sm font-medium rounded-md transition-all',
                tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700',
              )}
            >
              {t === 'posted' ? `Recruiter Jobs (${filteredPosted.length})` : `Live Jobs (${filteredScraped.length})`}
            </button>
          ))}
        </div>

        {/* Posted Jobs */}
        {tab === 'posted' && (
          <div className="space-y-3">
            {loading ? (
              <div className="text-center py-12 text-gray-400">Loading…</div>
            ) : filteredPosted.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No jobs found</p>
              </div>
            ) : filteredPosted.map(job => (
              <div key={job.id} className="card p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{job.title}</h3>
                      <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{job.employment_type}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{job.company_name}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 flex-wrap">
                      {job.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>}
                      {job.region && <span className="flex items-center gap-1"><Filter className="w-3 h-3" />{job.region.name}</span>}
                      <span>{timeAgo(job.created_at)}</span>
                    </div>
                    {job.skills_required?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {job.skills_required.slice(0, 6).map(s => (
                          <span key={s} className="text-xs bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded-full">{s}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => expressInterest(job.id)}
                      disabled={expressing === job.id}
                      className="btn-primary text-xs px-3 py-1.5"
                    >
                      {expressing === job.id ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Zap className="w-3 h-3" />}
                      Express Interest
                    </button>
                    <button
                      onClick={() => applyToJob(job.id)}
                      disabled={applying === job.id}
                      className="btn-secondary text-xs px-3 py-1.5"
                    >
                      Apply
                    </button>
                  </div>
                </div>
                {job.description && (
                  <p className="text-sm text-gray-500 mt-3 line-clamp-2">{job.description}</p>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Scraped Jobs */}
        {tab === 'scraped' && (
          <div className="space-y-3">
            {filteredScraped.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <Briefcase className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p>No scraped jobs found. Scraper runs every 10 minutes.</p>
              </div>
            ) : filteredScraped.map(job => (
              <div key={job.id} className="card p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{job.title}</h3>
                      {job.match_score != null && (
                        <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full', scoreBg(job.match_score))}>
                          {job.match_score}% match
                        </span>
                      )}
                      <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize">{job.source}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-0.5">{job.company}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 flex-wrap">
                      {job.location && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{job.location}</span>}
                      {job.salary && <span>💰 {job.salary}</span>}
                      {job.posted_at && <span>{timeAgo(job.posted_at)}</span>}
                    </div>
                    {job.tags?.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {job.tags.slice(0, 6).map(t => (
                          <span key={t} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-secondary text-xs px-3 py-1.5 shrink-0"
                    >
                      <ExternalLink className="w-3 h-3" /> View Job
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </CandidateLayout>
  )
}
