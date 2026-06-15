import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Users, FileText, Shield, AlertTriangle, Activity, Download,
  Eye, CheckCircle, XCircle, Clock, TrendingUp, TrendingDown,
  Filter, RefreshCw, Search, ChevronDown, ChevronRight,
  UserPlus, Ban, Edit, Trash2, Mail, Phone, MapPin, Calendar,
  BarChart3, LineChart as LineChartIcon, Server, Database,
  Lock, Key, LogOut, Bell, Settings, HelpCircle, Menu, X,
  ChevronLeft
} from 'lucide-react';
// Fixed: Renamed PieChart from recharts to RechartsPieChart to avoid conflict with lucide-react's PieChart
import { 
  LineChart, Line, BarChart, Bar, 
  PieChart as RechartsPieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, RadarChart, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, Radar 
} from 'recharts';
import { useAuth } from '@/context/AuthContext';
import { useNavigate } from 'react-router-dom';
import api from '@/lib/api';
import { cn, formatDateTime, timeAgo } from '@/lib/utils';
import toast from 'react-hot-toast';

// Types
interface AdminStats {
  total_users: number;
  total_candidates: number;
  total_recruiters: number;
  total_evaluations: number;
  flagged_hirings: number;
  active_reports: number;
  security_events_7d: number;
  bias_alerts: number;
  avg_evaluation_score: number;
  shortlist_rate: number;
}

interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'candidate' | 'recruiter' | 'superadmin';
  created_at: string;
  last_login_at: string | null;
  is_active: boolean;
}

interface AuditLog {
  id: number;
  user_id: number;
  user_name: string;
  action: string;
  entity_type: string;
  ip_address: string;
  created_at: string;
  details: any;
}

interface BiasAlert {
  id: number;
  bias_type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  is_resolved: boolean;
  created_at: string;
}

interface AdminReport {
  id: number;
  evaluation_id: number;
  candidate_name: string;
  job_title: string;
  company: string;
  score: number | null;
  recommendation: string | null;
  fairness_assessment: string;
  recruiter_summary: string;
  interview_questions: string[];
  risk_level: 'low' | 'medium' | 'high';
  generated_at: string | null;
  generation_time_ms: number | null;
}

function reportNeedsFairnessReview(report: AdminReport) {
  const text = (report.fairness_assessment || '').toLowerCase();
  return (
    report.risk_level === 'medium' ||
    report.risk_level === 'high' ||
    text.includes('manual review recommended') ||
    text.includes('bias risk')
  );
}

function cleanReportText(text: string | null | undefined) {
  if (!text) return 'Not available.';
  return text
    .replace(/##+\s*/g, '')
    .replace(/\*\*/g, '')
    .replace(/[^\x00-\x7F]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function fairnessSummary(report: AdminReport) {
  const cleaned = cleanReportText(report.fairness_assessment);
  const parts = cleaned.split(/Bias Risk:/i);
  return parts[0]?.trim() || cleaned;
}

function recruiterSummary(report: AdminReport) {
  const cleaned = cleanReportText(report.recruiter_summary);
  return cleaned.length > 220 ? `${cleaned.slice(0, 220)}...` : cleaned;
}

// Stat Card Component
function StatCard({ title, value, icon, trend, color, alert }: any) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-all"
    >
      <div className="flex items-center justify-between">
        <div className={cn("p-2 rounded-lg", color)}>
          {icon}
        </div>
        {trend && (
          <span className={cn("text-xs font-medium", trend > 0 ? "text-green-600" : "text-red-600")}>
            {trend > 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900 mt-3">{value.toLocaleString()}</p>
      <p className="text-sm text-gray-500 mt-1">{title}</p>
      {alert && <p className="text-xs text-red-600 mt-2 animate-pulse">⚠️ Requires attention</p>}
    </motion.div>
  );
}

// Activity Chart Component
function ActivityChart({ data }: { data: any[] }) {
  if (!data.length) {
    return (
      <div className="h-[300px] flex items-center justify-center text-sm text-gray-500">
        No recent activity available yet.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
        <YAxis stroke="#6b7280" fontSize={12} />
        <Tooltip
          contentStyle={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '8px' }}
        />
        <Legend />
        <Area type="monotone" dataKey="evaluations" stroke="#3b82f6" fill="#93c5fd" fillOpacity={0.3} name="Evaluations" />
        <Area type="monotone" dataKey="users" stroke="#10b981" fill="#6ee7b7" fillOpacity={0.3} name="New Users" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Users Table Component
function UsersTable({ users, onRefresh }: { users: User[]; onRefresh: () => void }) {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editRole, setEditRole] = useState<User['role']>('candidate');

  const filteredUsers = users.filter(user => {
    if (search && !user.full_name?.toLowerCase().includes(search.toLowerCase()) &&
        !user.email?.toLowerCase().includes(search.toLowerCase())) return false;
    if (roleFilter !== 'all' && user.role !== roleFilter) return false;
    return true;
  });

  async function toggleUserStatus(userId: number, currentStatus: boolean) {
    setActionLoading(userId);
    try {
      await api.patch(`/admin/users/${userId}/status`, { is_active: !currentStatus });
      toast.success(`User ${currentStatus ? 'deactivated' : 'activated'} successfully`);
      onRefresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to update user status');
    } finally {
      setActionLoading(null);
    }
  }

  async function deleteUser(userId: number) {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;
    setActionLoading(userId);
    try {
      await api.delete(`/admin/users/${userId}`);
      toast.success('User deleted successfully');
      onRefresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to delete user');
    } finally {
      setActionLoading(null);
    }
  }

  function startEdit(user: User) {
    setEditingUserId(user.id);
    setEditName(user.full_name || '');
    setEditRole(user.role);
  }

  function cancelEdit() {
    setEditingUserId(null);
    setEditName('');
    setEditRole('candidate');
  }

  async function saveUser(userId: number) {
    setActionLoading(userId);
    try {
      await api.patch(`/admin/users/${userId}`, {
        full_name: editName,
        role: editRole,
      });
      toast.success('User updated successfully');
      cancelEdit();
      onRefresh();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to update user');
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div>
      <div className="flex gap-3 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="input pl-9"
            placeholder="Search users..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-36" value={roleFilter} onChange={e => setRoleFilter(e.target.value)}>
          <option value="all">All Roles</option>
          <option value="candidate">Candidates</option>
          <option value="recruiter">Recruiters</option>
          <option value="superadmin">Super Admins</option>
        </select>
        <button onClick={onRefresh} className="btn-secondary">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">User</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Role</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Joined</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Last Active</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredUsers.map(user => (
              <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3">
                  {editingUserId === user.id ? (
                    <div className="space-y-2">
                      <input
                        className="input text-sm"
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                      />
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  ) : (
                    <div>
                      <p className="font-medium text-gray-900">{user.full_name}</p>
                      <p className="text-xs text-gray-500">{user.email}</p>
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  {editingUserId === user.id ? (
                    <select
                      className="input w-36 text-sm"
                      value={editRole}
                      onChange={e => setEditRole(e.target.value as User['role'])}
                    >
                      <option value="candidate">candidate</option>
                      <option value="recruiter">recruiter</option>
                      <option value="superadmin">superadmin</option>
                    </select>
                  ) : (
                    <span className={cn(
                      'badge',
                      user.role === 'superadmin' ? 'bg-purple-100 text-purple-700' :
                      user.role === 'recruiter' ? 'bg-blue-100 text-blue-700' :
                      'bg-green-100 text-green-700'
                    )}>
                      {user.role}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs">{timeAgo(user.created_at)}</td>
                <td className="px-4 py-3 text-gray-600 text-xs">{user.last_login_at ? timeAgo(user.last_login_at) : 'Never'}</td>
                <td className="px-4 py-3">
                  <span className={cn(
                    'badge',
                    user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
                  )}>
                    {user.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {editingUserId === user.id ? (
                      <>
                        <button
                          onClick={() => saveUser(user.id)}
                          disabled={actionLoading === user.id}
                          className="p-1.5 rounded-lg hover:bg-green-50 text-green-600 transition-colors"
                          title="Save"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          onClick={cancelEdit}
                          disabled={actionLoading === user.id}
                          className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
                          title="Cancel"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => startEdit(user)}
                        disabled={actionLoading === user.id}
                        className="p-1.5 rounded-lg hover:bg-blue-50 text-gray-400 hover:text-blue-500 transition-colors"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => toggleUserStatus(user.id, user.is_active)}
                      disabled={actionLoading === user.id}
                      className={cn(
                        'p-1.5 rounded-lg transition-colors',
                        user.is_active ? 'hover:bg-red-50 text-red-500' : 'hover:bg-green-50 text-green-500'
                      )}
                      title={user.is_active ? 'Deactivate' : 'Activate'}
                    >
                      {user.is_active ? <Ban className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => deleteUser(user.id)}
                      disabled={actionLoading === user.id || editingUserId === user.id}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Bias Detection Monitor Component
function BiasDetectionMonitor({ alerts, reports }: { alerts: BiasAlert[]; reports: AdminReport[] }) {
  const [generatingTest, setGeneratingTest] = useState(false);
  const severityColors = {
    low: 'bg-yellow-100 text-yellow-700',
    medium: 'bg-orange-100 text-orange-700',
    high: 'bg-red-100 text-red-700'
  };
  const reviewReports = reports.filter(reportNeedsFairnessReview);

  async function resolveAlert(alertId: number) {
    try {
      await api.patch(`/admin/bias-alerts/${alertId}/resolve`);
      toast.success('Alert resolved');
    } catch (err) {
      toast.error('Failed to resolve alert');
    }
  }

  async function generateTestAlerts() {
    setGeneratingTest(true);
    try {
      const res = await api.post('/admin/bias-alerts/generate-test');
      toast.success(res.data.message);
      // Optionally refresh the dashboard
      window.location.reload();
    } catch (err: any) {
      toast.error(err?.response?.data?.error || 'Failed to generate test alerts');
    } finally {
      setGeneratingTest(false);
    }
  }

  return (
    <div className="space-y-3">
      {reviewReports.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-4 h-4 text-orange-500" />
            <h3 className="font-semibold text-gray-900">Fairness Reports Requiring Review</h3>
          </div>
          <div className="space-y-3">
            {reviewReports.map(report => (
              <div key={report.id} className="rounded-lg border border-orange-100 bg-orange-50/60 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium text-gray-900">{report.candidate_name} · {report.job_title}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {report.company || 'Company'} · Eval #{report.evaluation_id} · {report.generated_at ? `${formatDateTime(report.generated_at)} · ${timeAgo(report.generated_at)}` : 'Unknown time'}
                    </p>
                  </div>
                  <span className={cn(
                    'badge shrink-0',
                    report.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                    report.risk_level === 'medium' ? 'bg-orange-100 text-orange-700' :
                    'bg-yellow-100 text-yellow-700'
                  )}>
                    {report.risk_level.toUpperCase()} Review
                  </span>
                </div>
                <p className="text-sm text-gray-700 mt-3 whitespace-pre-wrap">
                  {report.fairness_assessment || 'No fairness assessment available.'}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {alerts.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
          <p>No actionable bias alerts detected.</p>
          <p className="text-xs text-gray-400 mt-2">
            {reviewReports.length > 0
              ? 'Review items are shown above, but they are not escalated as confirmed bias alerts.'
              : 'No fairness reports currently require follow-up.'}
          </p>
          <button
            onClick={generateTestAlerts}
            disabled={generatingTest}
            className="mt-4 btn-secondary text-sm"
          >
            {generatingTest ? 'Generating...' : 'Generate Test Alerts'}
          </button>
        </div>
      ) : (
        <>
          <div className="flex justify-end">
            <button
              onClick={generateTestAlerts}
              disabled={generatingTest}
              className="btn-secondary text-sm"
            >
              {generatingTest ? 'Generating...' : 'Generate More Test Alerts'}
            </button>
          </div>
          {alerts.map(alert => (
            <div key={alert.id} className="card p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertTriangle className={cn(
                  'w-5 h-5',
                  alert.severity === 'high' ? 'text-red-500' :
                  alert.severity === 'medium' ? 'text-orange-500' : 'text-yellow-500'
                )} />
                <div>
                  <p className="font-medium text-gray-900">{alert.bias_type.replace('_', ' ').toUpperCase()}</p>
                  <p className="text-sm text-gray-500 mt-0.5">{alert.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={cn('badge', severityColors[alert.severity])}>
                  {alert.severity.toUpperCase()} Severity
                </span>
                <button
                  onClick={() => resolveAlert(alert.id)}
                  className="btn-secondary text-xs px-3 py-1.5"
                >
                  <CheckCircle className="w-3 h-3" /> Resolve
                </button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

// Audit Log Viewer Component
function AuditLogViewer({ logs }: { logs: AuditLog[] }) {
  const [filter, setFilter] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const filteredLogs = logs.filter(log =>
    !filter || log.action.includes(filter) || log.entity_type.includes(filter)
  );

  return (
    <div>
      <div className="flex gap-3 mb-4">
        <input
          className="input flex-1"
          placeholder="Filter by action or entity..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
      </div>
      {filteredLogs.length === 0 && (
        <div className="card p-6 text-center text-gray-500">
          No audit activity found yet.
        </div>
      )}
      <div className="space-y-2">
        {filteredLogs.map(log => (
          <div key={log.id} className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 hover:bg-gray-50">
            <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center">
              <Clock className="w-4 h-4 text-gray-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900">
                {log.user_name} - {log.action}
              </p>
              <p className="text-xs text-gray-500">
                {log.entity_type} · IP: {log.ip_address} · {formatDateTime(log.created_at)} · {timeAgo(log.created_at)}
              </p>
            </div>
            {log.details && (
              <button
                onClick={() => setSelectedLog(log)}
                className="text-xs text-brand-600 hover:underline"
              >
                View Details
              </button>
            )}
          </div>
        ))}
      </div>

      {/* Details Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
          >
            <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Audit Log Details</h2>
                <p className="text-sm text-gray-500 mt-1">{selectedLog.user_name} - {selectedLog.action}</p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">User</label>
                  <p className="text-gray-900 font-medium mt-1">{selectedLog.user_name}</p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">User ID</label>
                  <p className="text-gray-900 font-medium mt-1">{selectedLog.user_id}</p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Action</label>
                  <p className="text-gray-900 font-medium mt-1">{selectedLog.action}</p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Entity Type</label>
                  <p className="text-gray-900 font-medium mt-1">{selectedLog.entity_type}</p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">IP Address</label>
                  <p className="text-gray-900 font-medium mt-1 font-mono text-sm">{selectedLog.ip_address}</p>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Timestamp</label>
                  <p className="text-gray-900 font-medium mt-1">{formatDateTime(selectedLog.created_at)}</p>
                </div>
              </div>

              {selectedLog.details && (
                <div>
                  <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Details</label>
                  <div className="mt-2 bg-gray-50 rounded-lg p-4 border border-gray-200 overflow-x-auto">
                    <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap break-words">
                      {typeof selectedLog.details === 'string'
                        ? selectedLog.details
                        : JSON.stringify(selectedLog.details, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>

            <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6 flex justify-end gap-3">
              <button
                onClick={() => setSelectedLog(null)}
                className="btn-secondary"
              >
                Close
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

// Main Admin Dashboard Component
export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [alerts, setAlerts] = useState<BiasAlert[]>([]);
  const [reports, setReports] = useState<AdminReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const chartData = Array.from({ length: 7 }, (_, index) => {
    const day = new Date();
    day.setDate(day.getDate() - (6 - index));
    const key = day.toISOString().slice(0, 10);
    const label = day.toLocaleDateString(undefined, { weekday: 'short' });

    return {
      date: label,
      evaluations: logs.filter(log => log.created_at?.slice(0, 10) === key && /evaluation|application|candidate/i.test(`${log.action} ${log.entity_type}`)).length,
      users: users.filter(entry => entry.created_at?.slice(0, 10) === key).length,
    };
  });

  const resolvedAlertsCount = alerts.filter(alert => alert.is_resolved).length;
  const biasResolutionRate = alerts.length ? Math.round((resolvedAlertsCount / alerts.length) * 100) : 0;
  const recentUsers = users.slice(0, 5);
  const hasOverviewData = Boolean(
    stats &&
    (stats.total_users > 0 || stats.total_evaluations > 0 || logs.length > 0 || alerts.length > 0)
  );

  const menuItems = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'users', label: 'User Management', icon: <Users className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports', icon: <FileText className="w-4 h-4" /> },
    { id: 'bias', label: 'Bias Detection', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'security', label: 'Security', icon: <Shield className="w-4 h-4" /> },
    { id: 'audit', label: 'Audit Logs', icon: <Clock className="w-4 h-4" /> },
  ];

  useEffect(() => {
    fetchDashboardData(true);
    
    // Auto-refresh dashboard every 10 seconds to show live audit logs and reports
    const interval = setInterval(() => fetchDashboardData(false), 10000);
    return () => clearInterval(interval);
  }, []);

  async function fetchDashboardData(isInitial = false) {
    if (isInitial) setLoading(true);
    try {
      // Stats syncs DB activity into audit_logs before other admin data loads.
      const statsRes = await api.get('/admin/stats');
      const [usersRes, logsRes, alertsRes, reportsRes] = await Promise.all([
        api.get('/admin/users'),
        api.get('/admin/audit-logs', { params: { limit: 500 } }),
        api.get('/admin/bias-alerts'),
        api.get('/admin/reports'),
      ]);
      setStats(statsRes.data);
      setUsers(usersRes.data.users);
      setLogs(logsRes.data.logs);
      setAlerts(alertsRes.data.alerts);
      setReports(reportsRes.data.reports || []);
    } catch (err: any) {
      if (isInitial) toast.error(err?.response?.data?.error || 'Failed to load dashboard data');
    } finally {
      if (isInitial) setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-brand-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className={cn(
        "fixed left-0 top-0 h-full bg-white border-r border-gray-200 transition-all duration-300 z-30",
        sidebarOpen ? "w-64" : "w-20"
      )}>
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className={cn("flex items-center gap-2", !sidebarOpen && "justify-center w-full")}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            {sidebarOpen && <span className="font-bold text-gray-900">Admin Portal</span>}
          </div>
          <button onClick={() => setSidebarOpen(!sidebarOpen)} className="p-1 rounded-lg hover:bg-gray-100">
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
        </div>

        <nav className="p-3 space-y-1">
          {menuItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                activeTab === item.id
                  ? "bg-blue-50 text-blue-600"
                  : "text-gray-600 hover:bg-gray-100"
              )}
            >
              {item.icon}
              {sidebarOpen && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
              <span className="text-xs font-bold">{user?.full_name?.charAt(0) || 'A'}</span>
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 truncate">Super Admin</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={cn("transition-all duration-300", sidebarOpen ? "ml-64" : "ml-20")}>
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {menuItems.find(m => m.id === activeTab)?.label || 'Dashboard'}
              </h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {activeTab === 'overview' && 'Platform analytics and key metrics at a glance'}
                {activeTab === 'users' && 'Manage all users, roles, and permissions'}
                {activeTab === 'bias' && 'Monitor and review bias detection alerts'}
                {activeTab === 'audit' && 'System activity and audit trail logs'}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={() => fetchDashboardData(false)} className="btn-secondary">
                <RefreshCw className="w-4 h-4" /> Refresh
              </button>
              <button
                onClick={async () => { await logout(); navigate('/auth'); }}
                className="btn-ghost flex items-center gap-2"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'overview' && stats && (
            <div className="space-y-6">
              {!hasOverviewData && (
                <div className="card p-6 text-gray-600">
                  <p className="font-medium text-gray-900 mb-2">The dashboard is live, but your platform data is still sparse.</p>
                  <p>
                    The cards below now use real backend values. To make this page feel fuller, you’ll need more users,
                    evaluations, audit events, or bias alerts in the database.
                  </p>
                </div>
              )}

              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Total Users" value={stats.total_users} icon={<Users className="w-4 h-4 text-blue-600" />} color="bg-blue-50" />
                <StatCard title="Total Evaluations" value={stats.total_evaluations} icon={<Activity className="w-4 h-4 text-green-600" />} color="bg-green-50" />
                <StatCard title="Flagged Hirings" value={stats.flagged_hirings} icon={<AlertTriangle className="w-4 h-4 text-red-600" />} color="bg-red-50" alert />
                <StatCard title="Bias Alerts" value={stats.bias_alerts} icon={<Shield className="w-4 h-4 text-purple-600" />} color="bg-purple-50" />
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Activity Trends</h3>
                  <ActivityChart data={chartData} />
                </div>
                <div className="card p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Key Metrics</h3>
                  <div className="space-y-4">
                    {[
                      { label: 'Average Evaluation Score', value: stats.avg_evaluation_score, max: 100, color: 'bg-blue-500' },
                      { label: 'Shortlist Rate', value: stats.shortlist_rate, max: 100, color: 'bg-green-500' },
                      { label: 'Bias Alert Resolution Rate', value: biasResolutionRate, max: 100, color: 'bg-purple-500' },
                    ].map(metric => (
                      <div key={metric.label}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">{metric.label}</span>
                          <span className="font-semibold text-gray-900">{metric.value}%</span>
                        </div>
                        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className={cn("h-full rounded-full", metric.color)} style={{ width: `${(metric.value / metric.max) * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="card p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">Latest Users</h3>
                  <div className="space-y-3">
                    {recentUsers.length === 0 ? (
                      <p className="text-sm text-gray-500">No users have been created yet.</p>
                    ) : (
                      recentUsers.map(entry => (
                        <div key={entry.id} className="flex items-center justify-between rounded-lg border border-gray-100 p-3">
                          <div>
                            <p className="font-medium text-gray-900">{entry.full_name}</p>
                            <p className="text-xs text-gray-500">{entry.email}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xs font-medium text-gray-700">{entry.role}</p>
                            <p className="text-xs text-gray-500">{timeAgo(entry.created_at)}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="card p-5">
                  <h3 className="font-semibold text-gray-900 mb-4">System Health</h3>
                  <div className="space-y-3 text-sm text-gray-700">
                    <div className="flex items-center justify-between">
                      <span>Open bias alerts</span>
                      <span className="font-semibold">{stats.bias_alerts}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Security events in last 7 days</span>
                      <span className="font-semibold">{stats.security_events_7d}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Audit reports logged</span>
                      <span className="font-semibold">{reports.length || stats.active_reports}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Total recruiters</span>
                      <span className="font-semibold">{stats.total_recruiters}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Total candidates</span>
                      <span className="font-semibold">{stats.total_candidates}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Recent Activity</h3>
                  <button onClick={() => setActiveTab('audit')} className="text-sm text-brand-600 hover:underline">
                    View all logs →
                  </button>
                </div>
                <AuditLogViewer logs={logs.slice(0, 5)} />
              </div>
            </div>
          )}

          {activeTab === 'users' && <UsersTable users={users} onRefresh={fetchDashboardData} />}
          {activeTab === 'bias' && <BiasDetectionMonitor alerts={alerts} reports={reports} />}

          {activeTab === 'reports' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Generated Reports</h3>
              {reports.length === 0 ? (
                <div className="card p-6 text-gray-600">
                  <p>No feedback or fairness reports have been generated yet.</p>
                </div>
              ) : (
                reports.map(report => (
                  <div key={report.id} className="card p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium text-gray-900">{report.candidate_name} · {report.job_title}</p>
                        <p className="text-xs text-gray-500">
                          {report.company || 'Company'} · Eval #{report.evaluation_id} · {report.generated_at ? `${formatDateTime(report.generated_at)} · ${timeAgo(report.generated_at)}` : 'Unknown time'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className={cn(
                          'badge',
                          report.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                          report.risk_level === 'medium' ? 'bg-orange-100 text-orange-700' :
                          'bg-green-100 text-green-700'
                        )}>
                          {report.risk_level.toUpperCase()} risk
                        </span>
                        {report.score != null && (
                          <span className="badge bg-blue-100 text-blue-700">{report.score}%</span>
                        )}
                      </div>
                    </div>
                    <div className="mt-3 space-y-3 text-sm text-gray-700">
                      <div>
                        <p className="font-medium text-gray-900 mb-1">Recruiter Summary</p>
                        <p className="line-clamp-3 whitespace-pre-wrap">{report.recruiter_summary || 'No recruiter summary available.'}</p>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 mb-1">Fairness Assessment</p>
                        <p className="line-clamp-3 whitespace-pre-wrap">{report.fairness_assessment || 'No fairness assessment available.'}</p>
                      </div>
                      {report.interview_questions?.length > 0 && (
                        <div>
                          <p className="font-medium text-gray-900 mb-1">Interview Questions</p>
                          <p className="text-gray-600">{report.interview_questions.slice(0, 2).join(' ')}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {false && activeTab === 'reports' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Audit Reports</h3>
              {logs.filter(l => l.entity_type && l.entity_type.toLowerCase().includes('report')).length === 0 ? (
                <div className="card p-6 text-gray-600">
                  <p>No structured audit report entries found. Showing recent activity as a fallback.</p>
                  <div className="mt-4">
                    <AuditLogViewer logs={logs.slice(0, 10)} />
                  </div>
                </div>
              ) : (
                logs.filter(l => l.entity_type && l.entity_type.toLowerCase().includes('report')).map(r => (
                  <div key={r.id} className="card p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium">{r.entity_type}</p>
                      <p className="text-xs text-gray-500">{r.action} · {formatDateTime(r.created_at)} · {timeAgo(r.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button className="btn-secondary text-xs">Download</button>
                      <button onClick={() => console.log(r.details)} className="text-sm text-brand-600">View</button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Security Events</h3>
              {(() => {
                const securityEvents = logs.filter(l => (l.entity_type && l.entity_type.toLowerCase().includes('security')) || /login|auth|failed|ip|password/i.test(l.action))
                return securityEvents.length === 0 ? (
                  <div className="card p-6 text-gray-600">No recent security events detected.</div>
                ) : (
                  securityEvents.map(ev => (
                    <div key={ev.id} className="card p-3 flex items-center justify-between">
                      <div>
                        <p className="font-medium">{ev.action}</p>
                        <p className="text-xs text-gray-500">{ev.entity_type} · IP: {ev.ip_address} · {formatDateTime(ev.created_at)} · {timeAgo(ev.created_at)}</p>
                      </div>
                      <div className="text-xs text-gray-500">{formatDateTime(ev.created_at)}</div>
                    </div>
                  ))
                )
              })()}
            </div>
          )}

          {activeTab === 'audit' && <AuditLogViewer logs={logs} />}
        </div>
      </main>
    </div>
  );
}
