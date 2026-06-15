import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, BookOpen, CheckCircle2 } from 'lucide-react'
import CandidateLayout from '@/components/layout/CandidateLayout'
import LearningPath from '@/components/feedback/LearningPath'
import api from '@/lib/api'
import type { LearningPath as LearningPathType } from '@/types'
import toast from 'react-hot-toast'

export default function CandidateLearningHub() {
  const [learningPaths, setLearningPaths] = useState<LearningPathType[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function load() {
      try {
        const res = await api.get('/learning/hub')
        setLearningPaths(res.data.learning_paths || [])
      } catch (err: any) {
        toast.error(err?.response?.data?.error || 'Failed to load learning hub')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <CandidateLayout>
      <div className="p-6 max-w-6xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Learning Hub</h1>
            <p className="text-gray-500 text-sm mt-1">Track adaptive plans and progress across your evaluated jobs.</p>
          </div>
          <button onClick={() => navigate('/candidate/applications')} className="btn-secondary">
            <BookOpen className="w-4 h-4 mr-2" /> View Applications
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-56 rounded-2xl border border-gray-200 bg-white">
            <RefreshCw className="w-6 h-6 text-brand-500 animate-spin" />
          </div>
        ) : learningPaths.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-10 text-center">
            <CheckCircle2 className="w-10 h-10 mx-auto text-brand-500 mb-4" />
            <p className="text-lg font-semibold text-gray-900">No learning paths yet</p>
            <p className="text-sm text-gray-500 mt-2">Complete an application evaluation to generate a personalized learning plan.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {learningPaths.map((path) => (
              <div key={`${path.evaluation_id}-${path.job_title}`} className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
                  <div>
                    <p className="text-sm uppercase tracking-[0.2em] text-brand-600 font-semibold">{path.job_title}</p>
                    <p className="text-xl font-semibold text-gray-900">{path.company}</p>
                  </div>
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span>{path.completed_tasks}/{path.total_tasks} tasks complete</span>
                    <span className="px-2 py-1 rounded-full bg-green-50 text-green-700">{Math.round((path.completed_tasks / Math.max(path.total_tasks, 1)) * 100)}%</span>
                  </div>
                </div>
                <LearningPath
                  learningResources={path.learning_resources}
                  taskChecklist={path.task_checklist}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </CandidateLayout>
  )
}
