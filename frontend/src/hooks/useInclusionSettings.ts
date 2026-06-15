import { useState, useEffect, useCallback } from 'react';
import {
  InclusionSettings,
  getJobInclusionSettings,
  updateJobInclusionSettings,
  getGlobalInclusionStatus,
  toggleInclusionAgent,
} from '@/services/inclusionApi';
import toast from 'react-hot-toast';

const DEFAULT_SETTINGS: InclusionSettings = {
  enabled: true,
  nd_detection_sensitivity: 'medium',
  detect_hyperfocus: true,
  detect_pattern_recognition: true,
  detect_debugging_consistency: true,
  apply_score_uplift: true,
  generate_accessible_summaries: true,
  flag_underestimation_risks: true,
  output_format: 'standard',
};

export function useInclusionSettings(jobId?: number) {
  const [settings, setSettings] = useState<InclusionSettings>(DEFAULT_SETTINGS);
  const [globalEnabled, setGlobalEnabled] = useState<boolean>(true);
  const [loading, setLoading] = useState(true);

  const fetchSettings = useCallback(async () => {
    setLoading(true);
    try {
      if (jobId) {
        const data = await getJobInclusionSettings(jobId);
        setSettings(data);
      }
      const global = await getGlobalInclusionStatus();
      setGlobalEnabled(global.enabled);
    } catch (error) {
      console.error('Failed to fetch inclusion settings:', error);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const updateSettings = useCallback(
    async (newSettings: Partial<InclusionSettings>) => {
      if (!jobId) return;
      try {
        const updated = await updateJobInclusionSettings(jobId, newSettings);
        setSettings(updated);
        toast.success('Inclusion settings updated');
        return updated;
      } catch (error) {
        toast.error('Failed to update settings');
        throw error;
      }
    },
    [jobId]
  );

  const toggleGlobal = useCallback(async (enabled: boolean) => {
    try {
      await toggleInclusionAgent(enabled);
      setGlobalEnabled(enabled);
      toast.success(`Inclusion Agent ${enabled ? 'enabled' : 'disabled'} globally`);
    } catch (error) {
      toast.error('Failed to toggle inclusion agent');
      throw error;
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return {
    settings,
    globalEnabled,
    loading,
    updateSettings,
    toggleGlobal,
    isEnabled: settings.enabled && globalEnabled,
  };
}