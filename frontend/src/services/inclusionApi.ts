import api from '@/lib/api';

export interface InclusionSettings {
  enabled: boolean;
  nd_detection_sensitivity: 'low' | 'medium' | 'high';
  detect_hyperfocus: boolean;
  detect_pattern_recognition: boolean;
  detect_debugging_consistency: boolean;
  apply_score_uplift: boolean;
  generate_accessible_summaries: boolean;
  flag_underestimation_risks: boolean;
  output_format: 'standard' | 'adhd_friendly' | 'dyslexia_friendly';
}

export interface NDInclusionReport {
  nd_flag: boolean;
  nd_type: string;
  nd_source?: 'self_declared' | 'inferred' | string;
  risk_of_underestimation: string;
  recommended_action: string;
  penalty_reduction_weight: number;
  strengths_detected: Array<{
    weight: string;
    strength_label: string;
    evidence: string;
  }>;
  underestimation_risks: Array<{
    severity: string;
    risk_factor: string;
    affected_metric: string;
  }>;
}

export interface EvaluationWithInclusion {
  evaluation_id: number;
  original_score: number;
  adjusted_score: number;
  nd_inclusion: NDInclusionReport | null;
  accessible_summary: string | null;
}

// Get inclusion settings for a job
export async function getJobInclusionSettings(jobId: number): Promise<InclusionSettings> {
  const response = await api.get(`/admin/jobs/${jobId}/inclusion-settings`);
  return response.data;
}

// Update inclusion settings for a job
export async function updateJobInclusionSettings(
  jobId: number,
  settings: Partial<InclusionSettings>
): Promise<InclusionSettings> {
  const response = await api.patch(`/admin/jobs/${jobId}/inclusion-settings`, settings);
  return response.data;
}

// Get evaluation with inclusion data
export async function getEvaluationWithInclusion(
  evaluationId: number
): Promise<EvaluationWithInclusion> {
  const response = await api.get(`/evaluations/${evaluationId}/inclusion`);
  return response.data;
}

// Generate accessible summary for an evaluation
export async function generateAccessibleSummary(
  evaluationId: number,
  format: 'standard' | 'adhd_friendly' | 'dyslexia_friendly'
): Promise<{ summary: string }> {
  const response = await api.post(`/evaluations/${evaluationId}/accessible-summary`, { format });
  return response.data;
}

// Toggle inclusion agent globally
export async function toggleInclusionAgent(enabled: boolean): Promise<{ enabled: boolean }> {
  const response = await api.post('/admin/inclusion/toggle', { enabled });
  return response.data;
}

// Get global inclusion status
export async function getGlobalInclusionStatus(): Promise<{ enabled: boolean }> {
  const response = await api.get('/admin/inclusion/status');
  return response.data;
}
