import axios from 'axios';
import { Chat, Message, MessageRequest, MessageResponse, LoginRequest, Token, RegisterRequest, UserResponse, ChatResponse, Folder, CreateFolderRequest, UpdateFolderRequest, MoveChatRequest, Business, BusinessCreate, BusinessUpdate, WBKeyRequest, WBPnLResponse } from '../types';

// Настройка axios для работы с backend API
// В Docker используем относительный путь /api (через nginx proxy)
// Локально используем http://localhost:8000/api (gateway имеет префикс /api)
// По умолчанию используем /api для работы через nginx proxy в Docker
const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Добавляем interceptor для автоматической подстановки токена
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Устанавливаем Content-Type только если это не FormData
    // Для FormData axios автоматически установит multipart/form-data с boundary
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    } else {
      // Для FormData удаляем Content-Type, если он был установлен где-то еще
      // axios сам установит правильный заголовок с boundary
      delete config.headers['Content-Type'];
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor для обработки ошибок авторизации
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Если получили 401 и это не повторный запрос
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          // Используем API_BASE_URL для refresh токена
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', newRefreshToken);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Если обновление токена не удалось, выходим из системы
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    return Promise.reject(error);
  }
);

// === УСТАРЕВШИЙ КОД - ОФЛАЙН ЗАГЛУШКИ (оставляем для совместимости) ===

type Ticket = {
  user_id: string;
  telegram_chat_id: number;
  title: string;
  first_message: string;
  status: 'pending' | 'assigned' | 'closed';
  created_at: string;
  assigned_to?: string;
  assigned_at?: string;
  main_category?: string;
  subcategory?: string;
  chat_id?: string;
};

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

const storage = {
  get<T>(key: string, fallback: T): T {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : fallback;
    } catch {
      return fallback;
    }
  },
  set<T>(key: string, value: T) {
    localStorage.setItem(key, JSON.stringify(value));
  },
  remove(key: string) {
    localStorage.removeItem(key);
  }
};

// Инициализация мок-данных при первом запуске
function ensureMockDataSeeded() {
  if (!localStorage.getItem('mock_seeded')) {
    const now = new Date();
    const mkTicket = (idx: number): Ticket => ({
      user_id: `user-${idx}-${Date.now()}`,
      telegram_chat_id: 100000 + idx,
      title: `Вопрос по продукту #${idx}`,
      first_message: 'Здравствуйте! Нужна помощь с настройками.',
      status: idx % 2 === 0 ? 'pending' : 'assigned',
      created_at: new Date(now.getTime() - idx * 3600_000).toISOString(),
      assigned_to: idx % 2 ? 'mock-operator' : undefined,
      assigned_at: idx % 2 ? new Date(now.getTime() - (idx - 1) * 1800_000).toISOString() : undefined,
      main_category: 'общие',
      subcategory: idx % 2 ? 'настройка' : 'вопрос',
      chat_id: `chat-${idx}`
    });

    const pending = [mkTicket(1), mkTicket(3)].filter(t => t.status === 'pending');
    const assigned = [mkTicket(2), mkTicket(4)].filter(t => t.status === 'assigned');
    storage.set('mock_pending_tickets', pending);
    storage.set('mock_assigned_tickets', assigned);
    storage.set('mock_chats', [] as Chat[]);
    localStorage.setItem('mock_seeded', '1');
  }
}

ensureMockDataSeeded();

export const authService = {
  async login(data: LoginRequest): Promise<Token & { user: UserResponse }> {
    // Backend ожидает form-data для login (используем email как username)
    const formData = new FormData();
    formData.append('username', data.email);
    formData.append('password', data.password);
    
    const response = await api.post<Token>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    const { access_token, refresh_token, token_type } = response.data;
    
    // Сохраняем токены
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('token_type', token_type);
    
    console.log('Tokens saved:', { 
      access_token: access_token.substring(0, 20) + '...', 
      refresh_token: refresh_token.substring(0, 20) + '...' 
    });
    
    // Получаем данные пользователя
    const userResponse = await api.get<UserResponse>('/auth/profile');
    const user = userResponse.data;
    
    // Сохраняем данные пользователя
    localStorage.setItem('user', JSON.stringify({
      id: user.user_id,
      name: user.full_name || user.username,
      email: user.email
    }));
    
    return { ...response.data, user };
  },

  async register(data: RegisterRequest): Promise<UserResponse> {
    const response = await api.post<UserResponse>('/auth/register', {
      username: data.username,
      email: data.email,
      password: data.password,
      full_name: data.full_name
    });
    
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token_type');
    localStorage.removeItem('user');
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },

  async getCurrentUser() {
    try {
      const response = await api.get<UserResponse>('/auth/profile');
      const user = response.data;
      
      // Преобразуем в формат User
      return {
        id: user.user_id,
        name: user.full_name || user.username,
        email: user.email
      };
    } catch (error) {
      // Если не удалось получить пользователя, пытаемся взять из localStorage
      const storedUser = localStorage.getItem('user');
      if (storedUser) {
        return JSON.parse(storedUser);
      }
      throw error;
    }
  }
};

function chatsFromAssigned(assigned: Ticket[]): Chat[] {
  return assigned.map((t) => ({
    id: t.user_id,
    title: t.title || `Заявка #${t.user_id.substring(0, 8)}`,
    messages: [],
    createdAt: t.created_at,
    updatedAt: t.assigned_at || t.created_at,
    chat_id: t.chat_id,
    telegram_chat_id: t.telegram_chat_id
  }));
}

export const chatService = {
  async createChat(): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/chats/create');
    return response.data;
  },

  async getChats(limit: number = 20, skip: number = 0): Promise<Chat[]> {
    const response = await api.get<ChatResponse[]>('/chats/list', {
      params: { limit, skip }
    });
    
    // Преобразуем ChatResponse в Chat (только чаты без папки)
    return response.data
      .filter((chatResp: ChatResponse) => !chatResp.folder_id)
      .map((chatResp: ChatResponse) => ({
        id: chatResp.chat_id,
        user_id: chatResp.user_id,
        title: chatResp.title || undefined,
        messages: [],
        createdAt: chatResp.created_at,
        updatedAt: chatResp.updated_at,
        message_count: chatResp.message_count,
        is_active: chatResp.is_active,
        folder_id: chatResp.folder_id || null
      }));
  },

  async getChat(chatId: string): Promise<Chat> {
    const response = await api.get<ChatResponse>(`/chats/${chatId}`);
    const chatResp = response.data;
    
    return {
      id: chatResp.chat_id,
      user_id: chatResp.user_id,
      title: chatResp.title || undefined,
      messages: [],
      createdAt: chatResp.created_at,
      updatedAt: chatResp.updated_at,
      message_count: chatResp.message_count,
      is_active: chatResp.is_active,
      folder_id: chatResp.folder_id || null
    };
  },

  async getChatHistory(chatId: string, limit: number = 50): Promise<{ messages: Message[]; title?: string; createdAt?: string; updatedAt?: string; chat_id?: string; count?: number }> {
    const response = await api.get(`/messages/history/${chatId}`, {
      params: { limit }
    });
    
    const data = response.data;
    
    // Функция для извлечения информации о файле из текста сообщения
    const extractFileInfo = (text: string): { hasFile: boolean; fileName?: string; fileType?: 'pdf' | 'doc' | 'docx' | 'txt'; userText?: string } => {
      // Новый паттерн с именем файла в квадратных скобках: "пользователь отправил файл [имя.файла] с содержанием:"
      const filePatternWithName = /пользователь отправил файл \[([^\]]+)\] с содержанием:/i;
      // Старый паттерн без имени файла (для совместимости со старыми сообщениями)
      const filePatternOld = /пользователь отправил файл с содержанием:/i;
      
      let fileNameFromText: string | undefined = undefined;
      let userTextBeforeFile = '';
      let contentAfterPrefix = '';
      
      // Сначала проверяем новый формат с именем файла
      const matchWithName = text.match(filePatternWithName);
      if (matchWithName) {
        fileNameFromText = matchWithName[1]; // Имя файла из квадратных скобок
        const parts = text.split(filePatternWithName);
        userTextBeforeFile = parts[0]?.trim() || '';
        contentAfterPrefix = parts[parts.length - 1]?.trim() || '';
      } else if (filePatternOld.test(text)) {
        // Старый формат без имени файла
        const parts = text.split(filePatternOld);
        userTextBeforeFile = parts[0]?.trim() || '';
        contentAfterPrefix = parts[1]?.trim() || '';
      } else {
        return { hasFile: false };
      }
      
      // Определяем тип файла
      let fileType: 'pdf' | 'doc' | 'docx' | 'txt' | undefined = undefined;
      
      // Если имя файла есть, определяем тип по расширению
      if (fileNameFromText) {
        const lowerFileName = fileNameFromText.toLowerCase();
        if (lowerFileName.endsWith('.pdf')) fileType = 'pdf';
        else if (lowerFileName.endsWith('.docx')) fileType = 'docx';
        else if (lowerFileName.endsWith('.doc')) fileType = 'doc';
        else if (lowerFileName.endsWith('.txt') || lowerFileName.endsWith('.md')) fileType = 'txt';
      }
      
      // Если тип не найден, пытаемся найти расширение в тексте
      if (!fileType) {
        const pdfMatch = text.match(/\.pdf/i);
        const docxMatch = text.match(/\.docx/i);
        const docMatch = text.match(/\.doc\b/i);
        const txtMatch = text.match(/\.txt/i);
        
        if (pdfMatch) fileType = 'pdf';
        else if (docxMatch) fileType = 'docx';
        else if (docMatch) fileType = 'doc';
        else if (txtMatch) fileType = 'txt';
      }
      
      // Если тип все еще не найден, пытаемся определить по содержимому
      if (!fileType && contentAfterPrefix.length > 0) {
        // Простая эвристика - если содержимое очень короткое, скорее всего txt
        if (contentAfterPrefix.length < 100) {
          fileType = 'txt';
        }
      }
      
      // Используем реальное имя файла если есть, иначе генерируем
      const finalFileName = fileNameFromText || (fileType ? `document.${fileType}` : 'document.file');
      
      return {
        hasFile: true,
        fileName: finalFileName,
        fileType,
        userText: userTextBeforeFile // Сохраняем текст пользователя который был до префикса
      };
    };
    
    // Преобразуем сообщения из backend формата в наш формат
    const messages = data.messages.map((msg: any) => {
      // Сохраняем оригинальный текст сообщения пользователя (если есть)
      const userMessageText = msg.message || '';
      const photoUrl = msg.photo_url || '';
      
      // Проверяем, это файл (имя файла в photo_url) или фото (URL в photo_url)
      const isFile = photoUrl && !photoUrl.startsWith('/storage/') && !photoUrl.startsWith('http://') && !photoUrl.startsWith('https://') && !photoUrl.startsWith('blob:');
      
      // Если это файл, определяем тип по расширению имени файла
      let fileType: 'pdf' | 'doc' | 'docx' | 'txt' | undefined = undefined;
      let fileName: string | undefined = undefined;
      
      if (isFile && photoUrl) {
        fileName = photoUrl;
        const lowerFileName = photoUrl.toLowerCase();
        if (lowerFileName.endsWith('.pdf')) fileType = 'pdf';
        else if (lowerFileName.endsWith('.docx')) fileType = 'docx';
        else if (lowerFileName.endsWith('.doc')) fileType = 'doc';
        else if (lowerFileName.endsWith('.txt') || lowerFileName.endsWith('.md')) fileType = 'txt';
      }
      
      return {
        id: msg.id,
        role: msg.message_type === 'bot' ? 'user' : 'assistant',
        content: userMessageText || '', // Текст сообщения пользователя
        timestamp: msg.timestamp,
        message_type: msg.message_type,
        imageUrl: photoUrl, // Для файлов - имя файла, для фото - URL
        fileName: fileName,
        fileType: fileType,
        source: msg.source,
        source_links: msg.source_links,
        next_action: msg.next_action
      };
    });
    
    return {
      messages,
      chat_id: data.chat_id,
      count: data.count
    };
  },

  async sendMessage(request: MessageRequest): Promise<MessageResponse> {
    const response = await api.post<MessageResponse>('/messages/send', {
      message: request.message,
      chat_id: request.chat_id,
      chat_type: request.chat_type,
      is_first: request.is_first,
      photo_description: request.photo_description,
      photo_url: request.photo_url,
      business_id: request.business_id || null
    });
    
    return response.data;
  },

  async uploadPhoto(file: File): Promise<{ description: string; image_url: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    // Interceptor автоматически определит FormData и не установит Content-Type
    // axios сам установит правильный multipart/form-data с boundary
    const response = await api.post<{ description: string; image_url: string }>('/process-image', formData);
    
    return response.data;
  },

  async parseDocument(file: File): Promise<{ text: string; filename: string; text_length: number }> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post<{ text: string; filename: string; content_type?: string; text_length: number }>('/parse', formData);
    
    return response.data;
  },

  async deleteChat(chatId: string): Promise<void> {
    await api.delete(`/chats/${chatId}`);
  },

  async exportChat(chatId: string, format: string = 'pdf'): Promise<Blob> {
    const response = await api.get(`/chats/${chatId}/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  async exportMessage(messageId: string, format: string = 'pdf'): Promise<Blob> {
    const response = await api.get(`/messages/${messageId}/export`, {
      params: { format },
      responseType: 'blob'
    });
    return response.data;
  },

  async deleteAllChats(): Promise<void> {
    // Получаем все чаты и удаляем их по одному
    const chats = await chatService.getChats();
    await Promise.all(chats.map(chat => chatService.deleteChat(chat.id)));
  },

  // === Временные заглушки для функций без backend API ===
  
  async getPendingChats(): Promise<Ticket[]> {
    await delay(150);
    return storage.get<Ticket[]>('mock_pending_tickets', []);
  },

  async getAssignedChats(): Promise<Ticket[]> {
    await delay(150);
    return storage.get<Ticket[]>('mock_assigned_tickets', []);
  },

  async assignOperator(chatId: string, operatorId: string): Promise<Ticket> {
    await delay(150);
    const pending = storage.get<Ticket[]>('mock_pending_tickets', []);
    const assigned = storage.get<Ticket[]>('mock_assigned_tickets', []);
    const found = pending.find(t => t.user_id === chatId);
    if (found) {
      const moved: Ticket = {
        ...found,
        status: 'assigned',
        assigned_to: operatorId,
        assigned_at: new Date().toISOString()
      };
      storage.set('mock_pending_tickets', pending.filter(t => t.user_id !== chatId));
      storage.set('mock_assigned_tickets', [moved, ...assigned]);
      return moved;
    }
    const already = assigned.find(t => t.user_id === chatId);
    if (already) return already;
    const created: Ticket = {
      user_id: chatId,
      telegram_chat_id: Math.floor(Math.random() * 10_000_000),
      title: `Заявка #${chatId.substring(0, 8)}`,
      first_message: 'Создано локально',
      status: 'assigned',
      created_at: new Date().toISOString(),
      assigned_to: operatorId,
      assigned_at: new Date().toISOString()
    };
    storage.set('mock_assigned_tickets', [created, ...assigned]);
    return created;
  },

  async analyzePhoto(photo: File, chatId?: string): Promise<{ analysis: string; imageUrl: string; chatId: string; parsingResults?: string }> {
    await delay(400);
    const mockImageUrl = URL.createObjectURL(photo);
    const mockChatId = chatId || 'mock-photo-chat-' + Date.now();
    return {
      analysis: `Это mock анализ изображения "${photo.name}".`,
      imageUrl: mockImageUrl,
      chatId: mockChatId,
      parsingResults: 'Mock результаты парсинга'
    };
  },

  async getMessagesByTelegramChatId(_telegramChatId: number, limit: number = 50): Promise<Message[]> {
    await delay(100);
    return storage.get<Message[]>('mock_last_messages', []).slice(-limit);
  },

  async closeTicket(userId: string, _comment?: string): Promise<void> {
    await delay(150);
    const assigned = storage.get<Ticket[]>('mock_assigned_tickets', []);
    storage.set('mock_assigned_tickets', assigned.filter(t => t.user_id !== userId));
    const closed = storage.get<Ticket[]>('mock_closed_tickets', []);
    const ticket = assigned.find(t => t.user_id === userId);
    if (ticket) {
      storage.set('mock_closed_tickets', [{ ...ticket, status: 'closed' }, ...closed]);
    }
  },

  async getAiHints(_messageId: string): Promise<any> {
    await delay(200);
    return {
      hints: [
        'Попросите уточнить детали проблемы',
        'Предложите проверить настройки в разделе Профиль',
        'Рекомендуйте перезапустить приложение'
      ]
    };
  },

  async getLatestReviews(_operatorId: string): Promise<any[]> {
    await delay(150);
    return [
      { rating: 5, comment: 'Быстро помогли, спасибо!', closed_at: new Date().toISOString() },
      { rating: 4, comment: 'Все ок', closed_at: new Date(Date.now() - 86_400_000).toISOString() }
    ];
  },

  async getOperatorStats(_operatorId: string): Promise<{ operator_id: string; total_stats: number; average_rating: number | null; rating_distribution: Record<string, number>; }> {
    await delay(150);
    const distribution = { '5': 12, '4': 6, '3': 2, '2': 1, '1': 0 } as Record<string, number>;
    const total = Object.values(distribution).reduce((a, b) => a + b, 0);
    const avg = total > 0 ? (5*distribution['5'] + 4*distribution['4'] + 3*distribution['3'] + 2*distribution['2'] + 1*distribution['1']) / total : null;
    return {
      operator_id: _operatorId,
      total_stats: total,
      average_rating: avg,
      rating_distribution: distribution
    };
  }
};

export const folderService = {
  async createFolder(request: CreateFolderRequest): Promise<Folder> {
    const response = await api.post<Folder>('/folders/create', request);
    return response.data;
  },

  async getFolders(limit: number = 20, skip: number = 0): Promise<Folder[]> {
    const response = await api.get<Folder[]>('/folders/list', {
      params: { limit, skip }
    });
    return response.data;
  },

  async getFolder(folderId: string): Promise<Folder> {
    const response = await api.get<Folder>(`/folders/${folderId}`);
    return response.data;
  },

  async getFolderChats(folderId: string, limit: number = 20, skip: number = 0): Promise<Chat[]> {
    const response = await api.get<ChatResponse[]>(`/folders/${folderId}/chats`, {
      params: { limit, skip }
    });
    
    // Преобразуем ChatResponse в Chat
    return response.data.map((chatResp: ChatResponse) => ({
      id: chatResp.chat_id,
      user_id: chatResp.user_id,
      title: chatResp.title || undefined,
      messages: [],
      createdAt: chatResp.created_at,
      updatedAt: chatResp.updated_at,
      message_count: chatResp.message_count,
      is_active: chatResp.is_active
    }));
  },

  async updateFolder(folderId: string, request: UpdateFolderRequest): Promise<Folder> {
    const response = await api.put<Folder>(`/folders/${folderId}`, request);
    return response.data;
  },

  async deleteFolder(folderId: string): Promise<void> {
    await api.delete(`/folders/${folderId}`);
  },

  async moveChatToFolder(chatId: string, folderId: string | null): Promise<ChatResponse> {
    const response = await api.put<{ chat: ChatResponse }>(`/chats/${chatId}/move`, {
      folder_id: folderId
    });
    return response.data.chat;
  }
};

export const businessService = {
  async createBusiness(data: BusinessCreate): Promise<Business> {
    const response = await api.post<Business>('/businesses/', data);
    return response.data;
  },

  async getBusinesses(): Promise<Business[]> {
    const response = await api.get<Business[]>('/businesses/');
    return response.data;
  },

  async getBusiness(businessId: string): Promise<Business> {
    const response = await api.get<Business>(`/businesses/${businessId}`);
    return response.data;
  },

  async updateBusiness(businessId: string, data: BusinessUpdate): Promise<Business> {
    const response = await api.patch<Business>(`/businesses/${businessId}`, data);
    return response.data;
  },

  async deleteBusiness(businessId: string): Promise<void> {
    await api.delete(`/businesses/${businessId}`);
  }
};

export const calendarService = {
  async createEvent(eventData: any): Promise<any> {
    const response = await api.post('/calendar/events', eventData);
    return response.data;
  },

  async getEvents(startDate?: string, endDate?: string, category?: string, burnoutPrevention?: boolean): Promise<any[]> {
    const response = await api.get('/calendar/events', {
      params: {
        start_date: startDate,
        end_date: endDate,
        category,
        burnout_prevention: burnoutPrevention
      }
    });
    return response.data;
  },

  async getEvent(eventId: string): Promise<any> {
    const response = await api.get(`/calendar/events/${eventId}`);
    return response.data;
  },

  async updateEvent(eventId: string, updateData: any): Promise<any> {
    const response = await api.put(`/calendar/events/${eventId}`, updateData);
    return response.data;
  },

  async deleteEvent(eventId: string): Promise<void> {
    await api.delete(`/calendar/events/${eventId}`);
  },

  async getBurnoutStats(startDate?: string, endDate?: string): Promise<any> {
    const response = await api.get('/calendar/stats/burnout', {
      params: {
        start_date: startDate,
        end_date: endDate
      }
    });
    return response.data;
  }
};

export const onboardingService = {
  async completeOnboarding(
    businessId: string, 
    onboardingData: {
      business_type: string;
      business_name: string;
      city: string;
      business_goals: string[];
      business_description: string;
      daily_tasks: string[];
      daily_routine_description: string;
      primary_pain_point: string[];
      pain_description: string;
    }
  ): Promise<any> {
    const response = await api.post('/onboarding/complete', {
      business_id: businessId,
      business_type: onboardingData.business_type,
      business_name: onboardingData.business_name,
      city: onboardingData.city,
      business_goals: onboardingData.business_goals,
      business_description: onboardingData.business_description,
      daily_tasks: onboardingData.daily_tasks,
      daily_routine_description: onboardingData.daily_routine_description,
      primary_pain_point: onboardingData.primary_pain_point,
      pain_description: onboardingData.pain_description,
    });
    return response.data;
  }
};

export const wbService = {
  async buildPnL(businessId: string, apiKey?: string | null): Promise<WBPnLResponse> {
    const response = await api.post<WBPnLResponse>('/wb/build_pnl', {
      business_id: businessId,
      api_key: apiKey || null
    });
    return response.data;
  },

  async getCachedPnL(businessId: string): Promise<WBPnLResponse> {
    const response = await api.get<WBPnLResponse>(`/wb/get_cached_pnl/${businessId}`);
    return response.data;
  }
};

// Экспортируем api instance по умолчанию
export default api;


