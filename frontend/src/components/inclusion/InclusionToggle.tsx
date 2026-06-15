import { useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { InclusionSettingsPanel } from './InclusionSettingsPanel';
import { useInclusionSettings } from '@/hooks/useInclusionSettings';

interface InclusionToggleProps {
  jobId?: number;
  variant?: 'card' | 'inline' | 'minimal';
  onToggle?: (enabled: boolean) => void;
}

export function InclusionToggle({ jobId, variant = 'card', onToggle }: InclusionToggleProps) {
  const { settings, globalEnabled, loading, updateSettings, toggleGlobal, isEnabled } =
    useInclusionSettings(jobId);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  if (loading) {
    return <div className="animate-pulse bg-gray-200 rounded-xl h-24" />;
  }

  const handleToggle = async (checked: boolean) => {
    if (jobId) {
      await updateSettings({ enabled: checked });
    } else {
      await toggleGlobal(checked);
    }
    onToggle?.(checked);
  };

  if (variant === 'minimal') {
    return (
      <div className="flex items-center gap-3">
        <button
          onClick={() => handleToggle(!isEnabled)}
          className={cn(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            isEnabled ? 'bg-green-600' : 'bg-gray-300'
          )}
        >
          <span
            className={cn(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              isEnabled ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
        <div className="flex items-center gap-2">
          <Brain className={cn('w-4 h-4', isEnabled ? 'text-green-600' : 'text-gray-400')} />
          <span className="text-sm font-medium text-gray-700">
            Inclusion Agent {isEnabled ? 'ON' : 'OFF'}
          </span>
        </div>
      </div>
    );
  }

  if (variant === 'inline') {
    return (
      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-purple-100 flex items-center justify-center">
            <Brain className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900">Inclusion Agent</p>
            <p className="text-xs text-gray-500">
              {isEnabled ? 'Fairness adjustments active' : 'Neurodivergent inclusion disabled'}
            </p>
          </div>
        </div>
        <button
          onClick={() => handleToggle(!isEnabled)}
          className={cn(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
            isEnabled ? 'bg-green-600' : 'bg-gray-300'
          )}
        >
          <span
            className={cn(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              isEnabled ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
      </div>
    );
  }

  // Card variant (default)
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'rounded-xl border p-4 transition-all',
        isEnabled
          ? 'bg-gradient-to-r from-purple-50 to-blue-50 border-purple-200'
          : 'bg-gray-50 border-gray-200'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className={cn(
              'w-10 h-10 rounded-lg flex items-center justify-center',
              isEnabled ? 'bg-purple-100' : 'bg-gray-200'
            )}
          >
            <Brain className={cn('w-5 h-5', isEnabled ? 'text-purple-600' : 'text-gray-500')} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-gray-900">Inclusion Agent</h3>
              {isEnabled && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  Active
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 mt-0.5 max-w-md">
              {isEnabled
                ? 'AI detects neurodivergent strengths and applies fairness adjustments'
                : 'Enable to detect ND strengths and ensure fair evaluation'}
            </p>
          </div>
        </div>
        <button
          onClick={() => handleToggle(!isEnabled)}
          className={cn(
            'relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0',
            isEnabled ? 'bg-green-600' : 'bg-gray-300'
          )}
        >
          <span
            className={cn(
              'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
              isEnabled ? 'translate-x-6' : 'translate-x-1'
            )}
          />
        </button>
      </div>

      {isEnabled && (
        <div className="mt-4 pt-3 border-t border-purple-200">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-1 text-xs text-purple-600 hover:text-purple-700"
          >
            {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            Advanced Settings
          </button>

          {showAdvanced && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-3 space-y-2"
            >
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Sensitivity:</span>
                  <select
                    value={settings.nd_detection_sensitivity}
                    onChange={(e) =>
                      updateSettings({
                        nd_detection_sensitivity: e.target.value as any,
                      })
                    }
                    className="text-xs border rounded px-2 py-1"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">Output format:</span>
                  <select
                    value={settings.output_format}
                    onChange={(e) =>
                      updateSettings({
                        output_format: e.target.value as any,
                      })
                    }
                    className="text-xs border rounded px-2 py-1"
                  >
                    <option value="standard">Standard</option>
                    <option value="adhd_friendly">ADHD-friendly</option>
                    <option value="dyslexia_friendly">Dyslexia-friendly</option>
                  </select>
                </div>
              </div>
              <button
                onClick={() => setShowSettings(true)}
                className="text-xs text-purple-600 hover:underline mt-2"
              >
                More settings →
              </button>
            </motion.div>
          )}
        </div>
      )}

      <InclusionSettingsPanel
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        settings={settings}
        onUpdate={updateSettings}
        jobId={jobId}
      />
    </motion.div>
  );
}