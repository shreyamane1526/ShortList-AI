import { CheckCircle2, XCircle, Download, X, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { DashboardCandidate } from '@/types'

interface Props {
  selected: Set<number>
  candidates: DashboardCandidate[]
  onClear: () => void
  onBulkShortlist: () => void
  onBulkReject: () => void
  onExportCSV: () => void
  loading?: boolean
}

export default function BulkActionBar({
  selected, candidates, onClear,
  onBulkShortlist, onBulkReject, onExportCSV, loading,
}: Props) {
  if (selected.size === 0) return null

  const names = candidates
    .filter(c => selected.has(c.id))
    .map(c => c.full_name.split(' ')[0])
    .slice(0, 3)
    .join(', ')

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 bg-gray-900 text-white px-5 py-3 rounded-2xl shadow-2xl border border-gray-700">
      <div className="flex items-center gap-2 mr-2">
        <div className="w-6 h-6 rounded-full bg-brand-500 flex items-center justify-center text-xs font-bold">
          {selected.size}
        </div>
        <span className="text-sm font-medium">
          {names}{selected.size > 3 ? ` +${selected.size - 3}` : ''} selected
        </span>
      </div>

      <div className="w-px h-5 bg-gray-600" />

      <button
        onClick={onBulkShortlist}
        disabled={loading}
        className="flex items-center gap-1.5 text-sm font-medium text-green-400 hover:text-green-300 transition-colors disabled:opacity-50"
        title="Shortlist selected (S)"
      >
        {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
        Shortlist
      </button>

      <button
        onClick={onBulkReject}
        disabled={loading}
        className="flex items-center gap-1.5 text-sm font-medium text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
        title="Reject selected (R)"
      >
        <XCircle className="w-4 h-4" />
        Reject
      </button>

      <button
        onClick={onExportCSV}
        className="flex items-center gap-1.5 text-sm font-medium text-blue-400 hover:text-blue-300 transition-colors"
        title="Export to CSV"
      >
        <Download className="w-4 h-4" />
        Export
      </button>

      <div className="w-px h-5 bg-gray-600" />

      <button
        onClick={onClear}
        className="text-gray-400 hover:text-white transition-colors"
        title="Clear selection (Esc)"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
