import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format } from 'date-fns'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function timeAgo(date: string | null | undefined): string {
  if (!date) return '—'
  try {
    return formatDistanceToNow(new Date(date), { addSuffix: true })
  } catch {
    return '—'
  }
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return '—'
  try {
    return format(new Date(date), 'MMM d, yyyy')
  } catch {
    return '—'
  }
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return '—'
  try {
    return format(new Date(date), 'MMM d, yyyy h:mm a')
  } catch {
    return '—'
  }
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return 'text-gray-400'
  if (score >= 80) return 'text-green-700'
  if (score >= 60) return 'text-yellow-700'
  return 'text-red-700'
}

export function scoreBg(score: number | null | undefined): string {
  if (score == null) return 'bg-gray-100 text-gray-500'
  if (score >= 80) return 'bg-green-100 text-green-700'
  if (score >= 60) return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

// Icon + text label alongside color — never color alone for pass/fail
export function recommendationBadge(rec: string): { label: string; cls: string; icon: string } {
  switch (rec) {
    case 'YES':   return { label: 'Strong Match',   cls: 'bg-green-100 text-green-700',  icon: '✓' }
    case 'MAYBE': return { label: 'Possible Match', cls: 'bg-yellow-100 text-yellow-700', icon: '◑' }
    case 'NO':    return { label: 'Not a Match',    cls: 'bg-red-100 text-red-700',       icon: '✗' }
    default:      return { label: 'Pending',        cls: 'bg-gray-100 text-gray-500',     icon: '…' }
  }
}

export function statusBadge(status: string): { label: string; cls: string; icon: string } {
  switch (status) {
    case 'applied':     return { label: 'Applied',     cls: 'bg-blue-100 text-blue-700',    icon: '→' }
    case 'in_review':   return { label: 'In Review',   cls: 'bg-yellow-100 text-yellow-700', icon: '◑' }
    case 'shortlisted': return { label: 'Shortlisted', cls: 'bg-green-100 text-green-700',  icon: '✓' }
    case 'rejected':    return { label: 'Rejected',    cls: 'bg-red-100 text-red-700',       icon: '✗' }
    case 'on_hold':     return { label: 'On Hold',     cls: 'bg-gray-100 text-gray-600',     icon: '⏸' }
    default:            return { label: status,        cls: 'bg-gray-100 text-gray-600',     icon: '·' }
  }
}

export function actionBadge(action: string): { label: string; cls: string; icon: string } {
  switch (action) {
    case 'shortlisted': return { label: 'Shortlisted', cls: 'bg-green-100 text-green-700', icon: '✓' }
    case 'rejected':    return { label: 'Rejected',    cls: 'bg-red-100 text-red-700',      icon: '✗' }
    default:            return { label: 'Pending',     cls: 'bg-gray-100 text-gray-500',    icon: '…' }
  }
}

export function initials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function lcTotal(easy?: number | null, medium?: number | null, hard?: number | null): number {
  return (easy ?? 0) + (medium ?? 0) + (hard ?? 0)
}
