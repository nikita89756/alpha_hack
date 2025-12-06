export interface User {
  id: string;
  name: string;
  email: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_type?: 'user' | 'bot'; // Тип сообщения из backend
  imageUrl?: string;
  serverImageUrl?: string;
  timestamp?: string;
  fileName?: string; // Имя файла для документов
  fileType?: 'pdf' | 'doc' | 'docx' | 'txt'; // Тип файла
  source?: string; // Источник ответа (например, "llm-only", "kb", "ltm")
  source_links?: string[]; // Ссылки на источники
  next_action?: string; // Следующее действие (например, "continue", "exit")
}

export interface Chat {
  id: string; // chat_id из backend
  user_id?: string;
  title?: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  message_count?: number;
  is_active?: boolean;
  folder_id?: string | null; // ID папки, где находится чат
  is_closing?: boolean; // Индикатор что чат закрывается
  closing_at?: number; // Timestamp когда чат будет удален
  // Legacy поля для совместимости
  chat_id?: string;
  telegram_chat_id?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  user_id: string;
  username: string;
  email: string;
  full_name?: string;
  created_at: string;
  is_active: boolean;
}

export interface MessageRequest {
  message: string;
  chat_id: string;
  chat_type: 'support' | 'contract';
  is_first: boolean;
  photos?: File[];
  photo_description?: string;
  photo_url?: string;
  business_id?: string | null;
}

export interface MessageResponse {
  message_id: string;
  user_id: string;
  chat_id: string;
  message: string;
  timestamp: string;
  status: string;
}

export interface ChatResponse {
  chat_id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_active: boolean;
  folder_id?: string | null;
}

export interface ErrorResponse {
  error: string;
}

// Новые типы для работы с фотографиями
export interface PhotoAnalysisRequest {
  photo: File;
  chat_id?: string;
  chat_status: 'new' | 'existing';
}

export interface PhotoAnalysisResponse {
  chatId: string;
  response: string;
  chatTitle?: string;
}

export interface Folder {
  folder_id: string;
  user_id: string;
  name: string;
  description?: string;
  target_date?: string | null;
  chat_count: number;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface CreateFolderRequest {
  name: string;
  description?: string;
  target_date?: string | null;
}

export interface UpdateFolderRequest {
  name?: string;
  description?: string;
}

export interface MoveChatRequest {
  folder_id: string | null;
}

// Calendar types
export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  category?: string;
  color?: string;
  reminder_minutes?: number;
  is_all_day: boolean;
  burnout_prevention: boolean;
  linked_chat_id?: string | null;
  linked_folder_id?: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarEventCreate {
  title: string;
  description?: string;
  start_date: string;
  end_date: string;
  category?: string;
  color?: string;
  reminder_minutes?: number;
  is_all_day: boolean;
  burnout_prevention: boolean;
  linked_chat_id?: string | null;
  linked_folder_id?: string | null;
}

export interface CalendarEventUpdate {
  title?: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  category?: string;
  color?: string;
  reminder_minutes?: number;
  is_all_day?: boolean;
  burnout_prevention?: boolean;
  linked_chat_id?: string | null;
  linked_folder_id?: string | null;
}

export interface Business {
  id: string;
  user_id: string;
  name: string;
  description: string;
  industry?: string | null;
}

export interface BusinessCreate {
  name: string;
  description: string;
  industry?: string | null;
}

export interface BusinessUpdate {
  name?: string;
  description?: string;
  industry?: string | null;
}

// WB P&L types
export interface WBKeyRequest {
  business_id: string;
  api_key?: string | null;
}

export interface WBPnLData {
  gmv: number;
  marginality: number;
  number_of_sales: number;
  coef_returns: number;
  top_5_sku: Record<string, number>;
  bot_5_sku: Record<string, number>;
  cost_logistic: number;
  cost_saving: number;
  cost_marketplace: number;
  wb_ad_cost: number;
}

export interface WBPnLResponse {
  status: string;
  user_id: string;
  business_id: string;
  key_source?: string;
  source?: string;
  data: WBPnLData;
}

declare global {
  interface Window {
    uploadPhotoForAnalysis?: (file: File) => void;
  }
}
