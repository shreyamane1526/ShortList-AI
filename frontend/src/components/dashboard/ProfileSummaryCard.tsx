import { useNavigate } from 'react-router-dom'
import { Github, Code2, FileText, MapPin, Briefcase, ExternalLink, ArrowRight } from 'lucide-react'
import { cn, initials, lcTotal } from '@/lib/utils'
import type { Candidate, EnrichmentStatus } from '@/types'

interface Props {
  candidate: Candidate
  enrichStatus: EnrichmentStatus | null
}

function completeness(c: Candidate): { score: number; missing: string[] } {
  const checks = [
    { label: 'Headline',    done: !!c.headline },
    { label: 'Location',    done: !!c.location },
    { label: 'Summary',     done: !!c.summary },
    { label: 'GitHub',      done: !!c.github_username },
    { label: 'LeetCode',    done: !!c.leetcode_username },
    { label: 'Resume',      done: !!c.resume_url },
    { label: 'Skills',      done: (c.skills?.length ?? 0) > 0 },
    { label: 'Projects',    done: (c.projects?.length ?? 0) > 0 },
  ]
  const done = checks.filter(x => x.done).length
  const missing = checks.filter(x => !x.done).map(x => x.label)
  return { score: Math.round((done / checks.length) * 100), missing }
}

export default function ProfileSummaryCard({ candidate, enrichStatus }: Props) {
  const navigate = useNavigate()
  const { score, missing } = completeness(candidate)

  const barColor =
    score >= 80 ? 'bg-green-500' :
    score >= 50 ? 'bg-yellow-400' :
                  'bg-red-400'

  return (
    <div className="flex flex-col gap-4">
      {/* Avatar + name */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-xl font-bold shrink-0 shadow-md">
          {initials(candidate.full_name || 'U')}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-gray-900 truncate">{candidate.full_name}</p>
          {candidate.headline && (
            <p className="text-xs text-gray-500 truncate">{candidate.headline}</p>
          )}
          <div className="flex items-center gap-3 mt-1 text-xs text-gray-400 flex-wrap">
            {candidate.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />{candidate.location}
              </span>
            )}
            {candidate.years_experience != null && (
              <span className="flex items-center gap-1">
                <Briefcase className="w-3 h-3" />{candidate.years_experience}y exp
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Profile completeness */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-gray-600">Profile Strength</span>
          <span className={cn(
            'text-xs font-bold',
            score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-500',
          )}>
            {score}%
          </span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-700', barColor)}
            style={{ width: `${score}%` }}
          />
        </div>
        {missing.length > 0 && (
          <p className="text-[10px] text-gray-400 mt-1">
            Missing: {missing.slice(0, 3).join(', ')}{missing.length > 3 ? ` +${missing.length - 3}` : ''}
            {' · '}
            <button onClick={() => navigate('/candidate/profile')} className="text-brand-600 hover:underline">
              Complete profile
            </button>
          </p>
        )}
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-gray-50 rounded-lg p-2.5 text-center">
          <Github className="w-4 h-4 text-gray-600 mx-auto mb-1" />
          <p className="text-sm font-bold text-gray-900">{enrichStatus?.github_repos ?? '—'}</p>
          <p className="text-[10px] text-gray-500">Repos</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-2.5 text-center">
          <Code2 className="w-4 h-4 text-orange-500 mx-auto mb-1" />
          <p className="text-sm font-bold text-gray-900">
            {lcTotal(enrichStatus?.lc_easy, enrichStatus?.lc_medium, enrichStatus?.lc_hard) || '—'}
          </p>
          <p className="text-[10px] text-gray-500">Solved</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-2.5 text-center">
          <FileText className="w-4 h-4 text-purple-500 mx-auto mb-1" />
          <p className="text-sm font-bold text-gray-900">{enrichStatus?.resume_skills?.length ?? '—'}</p>
          <p className="text-[10px] text-gray-500">Skills</p>
        </div>
      </div>

      {/* Top skills */}
      {(candidate.skills?.length > 0 || (enrichStatus?.resume_skills?.length ?? 0) > 0) && (
        <div>
          <p className="text-xs font-semibold text-gray-600 mb-2">Top Skills</p>
          <div className="flex flex-wrap gap-1.5">
            {[...new Set([...(candidate.skills || []), ...(enrichStatus?.resume_skills || [])])]
              .slice(0, 8)
              .map(s => (
                <span key={s} className="text-[10px] bg-brand-50 text-brand-700 border border-brand-100 px-2 py-0.5 rounded-full">
                  {s}
                </span>
              ))}
          </div>
        </div>
      )}

      {/* Suggested jobs */}
      {enrichStatus?.top_job_matches?.length ? (
        <div>
          <p className="text-xs font-semibold text-gray-600 mb-2">Suggested Jobs</p>
          <div className="space-y-1.5">
            {enrichStatus.top_job_matches.slice(0, 3).map((job, i) => (
              <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 hover:bg-brand-50 transition-colors">
                <span className={cn(
                  'text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0',
                  job.match_score >= 70 ? 'bg-green-100 text-green-700' :
                  job.match_score >= 40 ? 'bg-yellow-100 text-yellow-700' :
                                          'bg-gray-100 text-gray-600',
                )}>
                  {job.match_score}%
                </span>
                <p className="text-xs text-gray-700 truncate flex-1">{job.title}</p>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                    <ExternalLink className="w-3 h-3 text-gray-400 hover:text-brand-600" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <button
        onClick={() => navigate('/candidate/profile')}
        className="w-full flex items-center justify-center gap-1.5 text-xs text-brand-600 hover:text-brand-800 font-medium py-1.5 border border-brand-200 rounded-lg hover:bg-brand-50 transition-colors"
      >
        Edit Profile <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  )
}
