import { useState } from 'react';
import { X, Brain, Zap, Eye, Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { InclusionSettings } from '@/services/inclusionApi';
import Modal from '@/components/ui/Modal';

interface InclusionSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  settings: InclusionSettings;
  onUpdate: (settings: Partial<InclusionSettings>) => Promise<InclusionSettings | undefined>;
  jobId?: number;
}

// Strongly typed output format labels
type OutputFormatOption = 'standard' | 'adhd_friendly' | 'dyslexia_friendly';
const outputFormatLabels: Record<OutputFormatOption, string> = {
  standard: 'Standard (detailed)',
  adhd_friendly: 'ADHD-friendly (concise, bullet points)',
  dyslexia_friendly: 'Dyslexia-friendly (clear fonts, short sentences)',
};

export function InclusionSettingsPanel({
  isOpen,
  onClose,
  settings,
  onUpdate,
}: InclusionSettingsPanelProps) {
  const [localSettings, setLocalSettings] = useState(settings);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate(localSettings);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const sections = [
    {
      title: 'ND Detection',
      icon: <Eye className="w-4 h-4" />,
      fields: [
        {
          label: 'Detection Sensitivity',
          key: 'nd_detection_sensitivity',
          type: 'select' as const,
          options: ['low', 'medium', 'high'],
        },
        { label: 'Detect Hyperfocus', key: 'detect_hyperfocus', type: 'checkbox' as const },
        { label: 'Detect Pattern Recognition', key: 'detect_pattern_recognition', type: 'checkbox' as const },
        {
          label: 'Detect Debugging Consistency',
          key: 'detect_debugging_consistency',
          type: 'checkbox' as const,
        },
      ],
    },
    {
      title: 'Fairness Adjustments',
      icon: <Shield className="w-4 h-4" />,
      fields: [
        { label: 'Apply Score Uplift', key: 'apply_score_uplift', type: 'checkbox' as const },
        {
          label: 'Generate Accessible Summaries',
          key: 'generate_accessible_summaries',
          type: 'checkbox' as const,
        },
        { label: 'Flag Underestimation Risks', key: 'flag_underestimation_risks', type: 'checkbox' as const },
      ],
    },
    {
      title: 'Output Format',
      icon: <Zap className="w-4 h-4" />,
      fields: [
        {
          label: 'Response Format',
          key: 'output_format',
          type: 'radio' as const,
          options: ['standard', 'adhd_friendly', 'dyslexia_friendly'] as OutputFormatOption[],
        },
      ],
    },
  ];

  return (
    <Modal open={isOpen} onClose={onClose} title="Inclusion Agent Settings" size="lg">
      <div className="p-6 space-y-6 max-h-[70vh] overflow-y-auto">
        <div className="flex items-center gap-2 pb-4 border-b border-gray-100">
          <Brain className="w-5 h-5 text-purple-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Configure Inclusion Agent</h2>
            <p className="text-sm text-gray-500">
              Customize how the AI detects and adjusts for neurodivergent strengths
            </p>
          </div>
        </div>

        {sections.map((section) => (
          <div key={section.title} className="space-y-3">
            <div className="flex items-center gap-2">
              {section.icon}
              <h3 className="font-medium text-gray-900">{section.title}</h3>
            </div>
            <div className="space-y-3 pl-6">
              {section.fields.map((field) => {
                const value = localSettings[field.key as keyof InclusionSettings];
                if (field.type === 'checkbox') {
                  return (
                    <label key={field.key} className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={value as boolean}
                        onChange={(e) =>
                          setLocalSettings({ ...localSettings, [field.key]: e.target.checked })
                        }
                        className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <span className="text-sm text-gray-700">{field.label}</span>
                    </label>
                  );
                }
                if (field.type === 'select') {
                  return (
                    <div key={field.key} className="flex items-center gap-3">
                      <span className="text-sm text-gray-700 w-32">{field.label}</span>
                      <select
                        value={value as string}
                        onChange={(e) =>
                          setLocalSettings({ ...localSettings, [field.key]: e.target.value })
                        }
                        className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-purple-500 focus:border-purple-500"
                      >
                        {field.options?.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt.charAt(0).toUpperCase() + opt.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>
                  );
                }
                if (field.type === 'radio') {
                  return (
                    <div key={field.key} className="space-y-2">
                      <span className="text-sm text-gray-700 block">{field.label}</span>
                      {field.options?.map((opt) => (
                        <label key={opt} className="flex items-center gap-3 cursor-pointer ml-4">
                          <input
                            type="radio"
                            name={field.key}
                            value={opt}
                            checked={value === opt}
                            onChange={(e) =>
                              setLocalSettings({ ...localSettings, [field.key]: e.target.value })
                            }
                            className="w-4 h-4 text-purple-600 focus:ring-purple-500"
                          />
                          <span className="text-sm text-gray-600">
                            {outputFormatLabels[opt as OutputFormatOption]}
                          </span>
                        </label>
                      ))}
                    </div>
                  );
                }
                return null;
              })}
            </div>
          </div>
        ))}

        <div className="flex gap-3 pt-4 border-t border-gray-100">
          <button onClick={onClose} className="btn-secondary flex-1 justify-center">
            Cancel
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-primary flex-1 justify-center">
            {saving ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" /> : null}
            Save Settings
          </button>
        </div>
      </div>
    </Modal>
  );
}