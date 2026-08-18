const API_BASE = '/api/v1/dashboard';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface DashboardStats {
  appointments_today: number;
  appointments_today_breakdown: Record<string, number>;
  upcoming_appointments: number;
  active_calls: number;
  completed_calls_today: number;
  total_calls_today: number;
  bookings_today: number;
  booking_conversion: number;
  emails: { sent: number; pending: number; failed: number };
  call_outcomes: Record<string, number>;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface Call {
  id: string;
  customer_id: string | null;
  direction: string;
  livekit_room_id: string;
  status: string;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  summary: string | null;
  outcome: string | null;
  created_at: string;
  customers: { id: string; name: string; company: string | null; email: string | null; phone: string | null } | null;
  appointments?: Appointment[];
  emails?: EmailDelivery[];
}

export interface Appointment {
  id: string;
  customer_id: string;
  call_id: string | null;
  appointment_date: string;
  start_time: string;
  end_time: string;
  timezone: string;
  status: string;
  meeting_details: string | null;
  created_at: string;
  updated_at: string | null;
  customers?: { id: string; name: string; company: string | null; email: string | null; phone: string | null } | null;
  call?: { id: string; status: string; outcome: string | null; summary: string | null; duration_seconds: number | null } | null;
}

export interface Customer {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  company: string | null;
  description: string | null;
  created_at: string;
  total_calls?: number;
  total_appointments?: number;
  last_interaction?: string | null;
  calls?: Call[];
  appointments?: Appointment[];
  emails?: EmailDelivery[];
}

export interface EmailDelivery {
  id: string;
  customer_id: string | null;
  call_id: string | null;
  appointment_id: string | null;
  email_type: string;
  recipient_email: string;
  subject: string | null;
  status: string;
  provider: string | null;
  attempt_count: number;
  last_error: string | null;
  sent_at: string | null;
  created_at: string;
  customers?: { id: string; name: string; email: string | null } | null;
}

export interface KnowledgeRecord {
  id: string;
  category: string;
  title: string;
  content: string;
  access_level: string;
  priority: number;
  is_active: boolean;
  keywords: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CalendarDay {
  date: string;
  total: number;
  statuses: Record<string, number>;
}

export interface AnalyticsData {
  period_days: number;
  calls_by_day: { date: string; total: number; completed: number; failed: number }[];
  appointments_by_day: { date: string; total: number; booked: number; cancelled: number; completed: number }[];
  avg_call_duration: number;
  total_calls: number;
  total_appointments: number;
  email_stats: { sent: number; pending: number; failed: number };
}

export interface SystemHealth {
  database: { status: string; message: string };
  knowledge_search: { status: string; message: string };
  api: { status: string; message: string };
}

// ── API Functions ──

export const api = {
  getStats: () => fetchApi<DashboardStats>('/stats'),

  getCalls: (params?: { status?: string; search?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.search) sp.set('search', params.search);
    if (params?.page) sp.set('page', String(params.page));
    return fetchApi<PaginatedResponse<Call>>(`/calls?${sp}`);
  },

  getCall: (id: string) => fetchApi<Call>(`/calls/${id}`),

  getAppointments: (params?: { status?: string; date_from?: string; date_to?: string; search?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.date_from) sp.set('date_from', params.date_from);
    if (params?.date_to) sp.set('date_to', params.date_to);
    if (params?.search) sp.set('search', params.search);
    if (params?.page) sp.set('page', String(params.page));
    return fetchApi<PaginatedResponse<Appointment>>(`/appointments?${sp}`);
  },

  getAppointment: (id: string) => fetchApi<Appointment>(`/appointments/${id}`),

  getCalendar: (year: number, month: number) =>
    fetchApi<CalendarDay[]>(`/calendar/${year}/${month}`),

  getCustomers: (params?: { search?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set('search', params.search);
    if (params?.page) sp.set('page', String(params.page));
    return fetchApi<PaginatedResponse<Customer>>(`/customers?${sp}`);
  },

  getCustomer: (id: string) => fetchApi<Customer>(`/customers/${id}`),

  getEmails: (params?: { status?: string; email_type?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.status) sp.set('status', params.status);
    if (params?.email_type) sp.set('email_type', params.email_type);
    if (params?.page) sp.set('page', String(params.page));
    return fetchApi<PaginatedResponse<EmailDelivery>>(`/emails?${sp}`);
  },

  getKnowledge: (params?: { search?: string; access_level?: string; page?: number }) => {
    const sp = new URLSearchParams();
    if (params?.search) sp.set('search', params.search);
    if (params?.access_level) sp.set('access_level', params.access_level);
    if (params?.page) sp.set('page', String(params.page));
    return fetchApi<PaginatedResponse<KnowledgeRecord>>(`/knowledge?${sp}`);
  },

  createKnowledge: (data: Partial<KnowledgeRecord>) =>
    fetchApi<KnowledgeRecord>('/knowledge', { method: 'POST', body: JSON.stringify(data) }),

  updateKnowledge: (id: string, data: Partial<KnowledgeRecord>) =>
    fetchApi<KnowledgeRecord>(`/knowledge/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  getAnalytics: (days = 30) => fetchApi<AnalyticsData>(`/analytics?days=${days}`),

  getHealth: () => fetchApi<SystemHealth>('/health'),
};

const CAMPAIGN_API_BASE = '/api/v1/campaigns';
async function fetchCampaignsApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${CAMPAIGN_API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Campaign {
  id: string;
  name: string;
  status: string;
  objective: string | null;
  voice_agent_instructions: string | null;
  timezone: string;
  max_concurrent_calls: number;
  max_attempts_per_customer: number;
  retry_delay_minutes: number;
  scheduled_start_at: string | null;
  started_at: string | null;
  paused_at: string | null;
  stopped_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface CampaignContact {
  id: string;
  campaign_id: string;
  customer_id: string;
  status: string;
  priority: number;
  attempt_count: number;
  next_attempt_at: string | null;
  last_attempt_at: string | null;
  completed_at: string | null;
  last_outcome: string | null;
  last_error: string | null;
}

export interface CampaignActivity {
  id: string;
  event_type: string;
  message: string | null;
  created_at: string;
}

export const campaignsApi = {
  listCampaigns: () => fetchCampaignsApi<Campaign[]>(''),
  getCampaign: (id: string) => fetchCampaignsApi<Campaign>(`/${id}`),
  createCampaign: (data: Partial<Campaign>) => fetchCampaignsApi<Campaign>('', { method: 'POST', body: JSON.stringify(data) }),
  updateCampaign: (id: string, data: Partial<Campaign>) => fetchCampaignsApi<Campaign>(`/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCampaign: (id: string) => fetchCampaignsApi<{status: string}>(`/${id}`, { method: 'DELETE' }),
  validateCampaign: (id: string) => fetchCampaignsApi<{valid: boolean; errors?: string[]; valid_contacts_count?: number}>(`/${id}/validate`, { method: 'POST' }),
  startCampaign: (id: string) => fetchCampaignsApi<{status: string}>(`/${id}/start`, { method: 'POST' }),
  pauseCampaign: (id: string) => fetchCampaignsApi<{status: string}>(`/${id}/pause`, { method: 'POST' }),
  stopCampaign: (id: string) => fetchCampaignsApi<{status: string}>(`/${id}/stop`, { method: 'POST' }),
  addContacts: (id: string, customer_ids: string[]) => fetchCampaignsApi<{status: string}>(`/${id}/contacts`, { method: 'POST', body: JSON.stringify({ customer_ids }) }),
  getProgress: (id: string) => fetchCampaignsApi<Record<string, number>>(`/${id}/progress`),
  getActivity: (id: string) => fetchCampaignsApi<CampaignActivity[]>(`/${id}/activity`),
  uploadAudiencePreview: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${CAMPAIGN_API_BASE}/${id}/audience/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },
  importAudience: async (id: string, file: File, mapping: Record<string, string>) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('mapping', JSON.stringify(mapping));
    const res = await fetch(`${CAMPAIGN_API_BASE}/${id}/audience/import`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Import failed');
    return res.json();
  },
  getAudience: (id: string) => fetchCampaignsApi<any[]>(`/${id}/audience`),
  deleteAudienceMember: (id: string, contactId: string) => fetchCampaignsApi<{status: string}>(`/${id}/audience/${contactId}`, { method: 'DELETE' }),
};
