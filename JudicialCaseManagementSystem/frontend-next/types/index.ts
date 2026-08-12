/** Shared TypeScript types for the JCM frontend. */

export type Role = 'admin' | 'judge' | 'lawyer' | 'guest';

export interface User {
  id: string;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  professional_id?: string | null;
  phone_number?: string | null;
  is_verified: boolean;
}

export interface AuthResponse {
  user: User;
  access: string;
  refresh: string;
}

export interface Case {
  id: string;
  case_number: string;
  cnr_number?: string | null;
  title: string;
  description?: string;
  status: string;
  priority: string;
  case_type: string;
  court_name?: string;
  court?: string | null;
  courtroom?: string | null;
  filing_date: string;
  registration_date?: string | null;
  next_hearing_date?: string | null;
  plaintiff_name?: string;
  defendant_name?: string;
  judge_name?: string;
  assigned_judge?: string | null;
  assigned_lawyer?: string | null;
  subject?: string;
  category?: string;
  disposal_date?: string | null;
  disposal_reason?: string;
  is_public: boolean;
  is_bookmarked?: boolean;
  created_at: string;
  updated_at: string;
}

export interface Hearing {
  id: string;
  case: string;
  hearing_number: number;
  date: string;
  start_time?: string | null;
  end_time?: string | null;
  courtroom?: string | null;
  judge?: string | null;
  hearing_type: string;
  purpose?: string;
  status: string;
  adjournment_reason?: string | null;
  adjournment_note?: string;
  next_hearing_date?: string | null;
  is_public: boolean;
  participants?: HearingParticipant[];
  proceedings?: HearingProceeding[];
}

export interface HearingParticipant {
  id: string;
  name?: string;
  role: string;
  status: string;
  notes?: string;
}

export interface HearingProceeding {
  id: string;
  summary?: string;
  notes?: string;
  submissions?: string;
  directions?: string;
  next_action?: string;
  next_hearing_date?: string | null;
  is_public: boolean;
}

export interface CaseDocument {
  id: string;
  case: string;
  hearing?: string | null;
  document_type: string;
  file_name: string;
  file_size: number;
  mime_type?: string;
  processing_state: string;
  visibility: string;
  description?: string;
  uploaded_at: string;
  extraction?: { extracted_text: string; page_metadata: any } | null;
  file_url?: string;
  download_url?: string;
}

export interface Order {
  id: string;
  case: string;
  order_number?: string;
  order_type: string;
  title: string;
  summary?: string;
  date: string;
  status: string;
  visibility: string;
  is_public: boolean;
  document?: string | null;
  versions?: OrderVersion[];
}

export interface OrderVersion {
  id: string;
  version_number: number;
  reason?: string;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  case?: string | null;
  assigned_to?: string;
  priority: string;
  status: string;
  due_date?: string | null;
  created_at: string;
}

export interface NotificationItem {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  is_read: boolean;
  action_url?: string;
  created_at: string;
}

export interface Citation {
  source_type: string;
  source_id: string;
  source_label: string;
  page_number?: number | null;
  chunk_index?: number | null;
  excerpt?: string;
  url?: string;
}

export interface AIResponse {
  success: boolean;
  answer?: string;
  summary?: string;
  explanation?: string;
  citations?: Citation[];
  sources?: { doc_id: string; label: string }[];
  warnings?: string[];
  not_configured?: boolean;
}

export interface CaseEvent {
  id: string;
  event_type: string;
  title: string;
  description?: string;
  event_date: string;
  related_entity?: string;
}

export interface CauseListItem extends Hearing {}
