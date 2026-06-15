// LinkedInHackathon/frontend/src/components/inclusion/InclusionBadge.tsx
import { Brain, CheckCircle, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface InclusionBadgeProps {
  ndDetected?: boolean;
  type?: string | null;
  source?: 'self_declared' | 'inferred' | string | null;
  confidence?: 'low' | 'medium' | 'high';
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
  className?: string;
}

export function InclusionBadge({
  ndDetected,
  type,
  source,
  confidence = 'medium',
  size = 'md',
  showTooltip = true,
  className,
}: InclusionBadgeProps) {
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-sm px-2.5 py-1 gap-1.5',
    lg: 'text-base px-3 py-1.5 gap-2',
  };

  const confidenceColors = {
    low: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    medium: 'bg-orange-100 text-orange-700 border-orange-200',
    high: 'bg-green-100 text-green-700 border-green-200',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  };

  const detected = ndDetected ?? Boolean(type || source);
  const isSelfDeclared = source === 'self_declared';
  const label = isSelfDeclared
    ? 'Neurodivergence support applied'
    : 'Potential neurodivergent strengths detected';
  const sourceLabel = isSelfDeclared ? 'self-declared' : 'inferred';

  if (detected) {
    return (
      <div
        className={cn(
          'inline-flex items-center rounded-full border font-medium',
          confidenceColors[confidence],
          sizeClasses[size],
          className
        )}
        title={showTooltip ? `${label} (${sourceLabel})` : undefined}
      >
        <Brain className={iconSizes[size]} />
        <span>{label} ({sourceLabel})</span>
        <CheckCircle className={cn(iconSizes[size], 'text-green-600')} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full bg-gray-100 text-gray-600 border border-gray-200 font-medium',
        sizeClasses[size],
        className
      )}
      title={showTooltip ? 'No neurodivergent support applied' : undefined}
    >
      <AlertCircle className={iconSizes[size]} />
      <span>Standard Profile</span>
    </div>
  );
}
