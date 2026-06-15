interface Props {
  badges: string[]
  size?: 'sm' | 'md'
}

const BADGE_STYLES: Record<string, string> = {
  '🏆': 'bg-yellow-50 text-yellow-800 border-yellow-200',
  '🔥': 'bg-orange-50 text-orange-800 border-orange-200',
  '⚡': 'bg-blue-50 text-blue-800 border-blue-200',
}

function getBadgeStyle(badge: string): string {
  for (const [emoji, cls] of Object.entries(BADGE_STYLES)) {
    if (badge.startsWith(emoji)) return cls
  }
  return 'bg-gray-50 text-gray-700 border-gray-200'
}

export default function BadgeRow({ badges, size = 'md' }: Props) {
  if (!badges?.length) return null

  return (
    <div className="flex flex-wrap gap-2">
      {badges.map((badge, i) => (
        <span
          key={i}
          className={`inline-flex items-center gap-1 border rounded-full font-semibold ${
            size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'
          } ${getBadgeStyle(badge)}`}
        >
          {badge}
        </span>
      ))}
    </div>
  )
}
