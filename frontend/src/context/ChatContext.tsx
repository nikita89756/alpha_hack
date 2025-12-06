import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { chatService } from '../services/api';
import { Chat, Message, MessageRequest } from '../types';
import { getFileType } from '../utils/fileUtils';

interface ChatContextType {
  chats: Chat[];
  currentChat: Chat | null;
  isLoading: boolean;
  error: string | null;
  isTyping: boolean;
  uploadingPhotos: boolean;
  uploadingDocuments: boolean;
  selectedBusinessId: string | null;
  setSelectedBusinessId: (businessId: string | null) => void;
  sendMessage: (message: string, photoData?: { description?: string; imageUrl?: string }, documentData?: { text: string; filename: string }, chatType?: 'support' | 'contract') => Promise<void>;
  selectChat: (chatId: string) => Promise<void>;
  createNewChat: () => void;
  deleteChat: (chatId: string) => Promise<void>;
  refreshChats: () => Promise<void>;
  uploadPhotoForAnalysis: (photo: File) => Promise<void>;
  addMessageToCurrentChat: (message: Message) => void;
  closeTicket: (userId: string, comment?: string) => Promise<void>;
  markChatAsClosing: (chatId: string, delayMs: number) => void;
  updateChatTitle: (chatId: string, newTitle: string) => void;
  uploadPhoto: (file: File) => Promise<{ description: string; image_url: string }>;
  uploadDocument: (file: File) => Promise<{ text: string; filename: string; text_length: number }>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

interface ChatProviderProps {
  children: ReactNode;
}

export const ChatProvider: React.FC<ChatProviderProps> = ({ children }) => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [currentChat, setCurrentChat] = useState<Chat | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [uploadingPhotos, setUploadingPhotos] = useState<boolean>(false);
  const [uploadingDocuments, setUploadingDocuments] = useState<boolean>(false);
  const [initialLoadDone, setInitialLoadDone] = useState<boolean>(false);
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(() => {
    // Загружаем из localStorage при инициализации
    return localStorage.getItem('selectedBusinessId');
  });

  // Мемоизируем функцию refreshChats, чтобы избежать бесконечных вызовов
  const refreshChats = useCallback(async () => {
    if (isLoading) return; // Предотвращаем параллельные вызовы
    
    console.log('ChatContext - refreshChats called');
    setIsLoading(true);
    setError(null);
    try {
      const fetchedChats = await chatService.getChats();
      console.log('ChatContext - Fetched chats from server:', fetchedChats);
      // Проверяем, что fetchedChats является массивом, если нет - создаем пустой массив
      setChats(Array.isArray(fetchedChats) ? fetchedChats : []);
      console.log('ChatContext - Chats state updated');
    } catch (err: any) {
      console.error('ChatContext - Error fetching chats:', err);
      setError(err.response?.data?.error || 'Ошибка при загрузке чатов');
      setChats([]); // В случае ошибки устанавливаем пустой массив
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  // Загрузка списка чатов при монтировании компонента - только один раз
  useEffect(() => {
    // Создаем функцию загрузки чатов, чтобы избежать зависимостей от refreshChats
    const loadChats = async () => {
      try {
        if (localStorage.getItem('access_token') && !initialLoadDone) {
          console.log('ChatContext - Initial load of chats triggered');
          // Используем функцию загрузки чатов напрямую, без вызова refreshChats
          setIsLoading(true);
          setError(null);
          try {
            const fetchedChats = await chatService.getChats();
            console.log('ChatContext - Initial load fetched chats:', fetchedChats);
            setChats(Array.isArray(fetchedChats) ? fetchedChats : []);
            setInitialLoadDone(true);
          } catch (err: any) {
            console.error('ChatContext - Error in initial load:', err);
            setError(err.response?.data?.error || 'Ошибка при загрузке чатов');
            setChats([]);
          } finally {
            setIsLoading(false);
          }
        }
      } catch (err) {
        console.error('Failed to load chats:', err);
      }
    };

    loadChats();
    // Удаляем все зависимости, чтобы избежать повторных вызовов
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Добавляем эффект для отслеживания изменений токена
  useEffect(() => {
    const handleStorageChange = () => {
      const token = localStorage.getItem('access_token');
      if (token && !initialLoadDone) {
        console.log('ChatContext - Token detected, triggering chat load');
        refreshChats();
        setInitialLoadDone(true);
      }
    };

    // Обработчик события выхода из системы
    const handleLogout = () => {
      console.log('ChatContext - Logout event detected, clearing chats');
      setChats([]);
      setCurrentChat(null);
      setInitialLoadDone(false);
    };

    // Проверяем токен при монтировании
    handleStorageChange();

    // Добавляем слушатели событий
    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('logout', handleLogout);
    
    // Очистка при размонтировании
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('logout', handleLogout);
    };
  }, [refreshChats, initialLoadDone]);

  const selectChat = useCallback(async (chatId: string) => {
    console.log(`Selecting chat with ID: ${chatId}`);
    
    // Проверяем, что chatId является валидным ID
    if (!chatId || chatId === 'undefined' || chatId === 'null' || chatId === '000000000000000000000000') {
      console.log('Invalid chat ID, not selecting:', chatId);
      return;
    }

    // Проверяем, не выбран ли уже этот чат
    let alreadySelected = false;
    setCurrentChat(prev => {
      if (prev && prev.id === chatId) {
        console.log('Chat already selected, skipping');
        alreadySelected = true;
      }
      return prev;
    });
    
    if (alreadySelected) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Используем функциональное обновление для получения актуального списка чатов
      let existingChat: Chat | undefined;
      setChats(prev => {
        existingChat = prev.find(chat => chat.id === chatId);
        return prev;
      });
      
      if (existingChat) {
        console.log('Found chat in local list, setting as current');
        
        try {
          // Загружаем актуальную информацию о чате для получения title
          const chatInfo = await chatService.getChat(chatId);
          
          // Загружаем историю чата с сервера
          console.log('Fetching chat history from server');
          const history = await chatService.getChatHistory(chatId);
          console.log('Received chat history:', history);
          
          // Устанавливаем чат с актуальным title и историей
          if (history && Array.isArray(history.messages) && history.messages.length > 0) {
            // Обновляем чат с полученной историей и актуальным title
            setCurrentChat({
              ...existingChat,
              title: chatInfo.title || existingChat.title,
              messages: history.messages,
              chat_id: history.chat_id,
              updatedAt: chatInfo.updatedAt,
              createdAt: chatInfo.createdAt,
              message_count: chatInfo.message_count,
              folder_id: chatInfo.folder_id || existingChat.folder_id || null
            });
          } else {
            // Если история пуста, сбрасываем сообщения в чате, но сохраняем title
            setCurrentChat({
              ...existingChat,
              title: chatInfo.title || existingChat.title,
              messages: [],
              chat_id: history?.chat_id || chatId,
              updatedAt: chatInfo.updatedAt,
              createdAt: chatInfo.createdAt,
              message_count: chatInfo.message_count,
              folder_id: chatInfo.folder_id || existingChat.folder_id || null
            });
          }
          
          // Обновляем title и folder_id в списке чатов тоже
          setChats(prev => prev.map(chat => 
            chat.id === chatId 
              ? { ...chat, title: chatInfo.title || chat.title, folder_id: chatInfo.folder_id || chat.folder_id || null }
              : chat
          ));
        } catch (error) {
          console.error('Failed to load chat info, using existing chat data:', error);
          // Если не удалось загрузить chatInfo, используем существующий чат и загружаем только историю
          const history = await chatService.getChatHistory(chatId);
          
          if (history && Array.isArray(history.messages) && history.messages.length > 0) {
            setCurrentChat({
              ...existingChat,
              messages: history.messages,
              chat_id: history.chat_id
            });
          } else {
            setCurrentChat({
              ...existingChat,
              messages: [],
              chat_id: history?.chat_id || chatId
            });
          }
        }
      } else {
        console.log('Chat not found in local list, fetching from server');
        // Если чата нет в локальном списке, загружаем его с сервера
        try {
          // Загружаем информацию о чате для получения title
          const chatInfo = await chatService.getChat(chatId);
          const history = await chatService.getChatHistory(chatId);
          
          if (history && history.messages) {
            // Создаем новый чат и добавляем его в список
            const newChat = {
              id: chatId,
              messages: history.messages,
              createdAt: chatInfo.createdAt || history.createdAt || new Date().toISOString(),
              updatedAt: chatInfo.updatedAt || history.updatedAt || new Date().toISOString(),
              title: chatInfo.title || history.title,
              chat_id: history.chat_id,
              message_count: chatInfo.message_count,
              is_active: chatInfo.is_active,
              folder_id: chatInfo.folder_id || null
            };
            
            setCurrentChat(newChat);
            // Проверяем, нет ли уже чата с таким ID перед добавлением
            // Если у чата есть folder_id, НЕ добавляем его в общий список chats
            setChats(prev => {
              const exists = prev.some(chat => chat.id === chatId);
              if (exists) {
                console.log('Chat already exists in list, not adding duplicate');
                return prev;
              }
              // Не добавляем чаты из папок в общий список
              if (newChat.folder_id) {
                console.log('Chat belongs to a folder, not adding to main list');
                return prev;
              }
              return [...prev, newChat];
            });
          } else {
            // История пуста, но чат существует - создаем чат с заголовком из chatInfo
            const newChat = {
              id: chatId,
              messages: [],
              createdAt: chatInfo.createdAt || new Date().toISOString(),
              updatedAt: chatInfo.updatedAt || new Date().toISOString(),
              title: chatInfo.title,
              chat_id: chatId,
              message_count: chatInfo.message_count,
              is_active: chatInfo.is_active,
              folder_id: chatInfo.folder_id || null
            };
            
            setCurrentChat(newChat);
            // Добавляем в список чатов если еще не там
            // Если у чата есть folder_id, НЕ добавляем его в общий список chats
            setChats(prev => {
              const exists = prev.some(chat => chat.id === chatId);
              if (exists) {
                return prev.map(chat => chat.id === chatId ? newChat : chat);
              }
              // Не добавляем чаты из папок в общий список
              if (newChat.folder_id) {
                console.log('Chat belongs to a folder, not adding to main list');
                return prev;
              }
              return [...prev, newChat];
            });
          }
        } catch (error) {
          console.log('Chat not found on server, creating new chat with provided ID');
          // Если чат не найден на сервере, создаем новый чат с переданным ID
          const newChat: Chat = {
            id: chatId,
            title: `Заявка #${chatId.substring(0, 8)}`,
            messages: [{
              role: 'user' as const,
              content: 'Новая заявка от пользователя',
              timestamp: new Date().toISOString(),
            }],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          
          setCurrentChat(newChat);
          // Проверяем, нет ли уже чата с таким ID перед добавлением
          setChats(prev => {
            const exists = prev.some(chat => chat.id === chatId);
            if (exists) {
              console.log('Chat already exists in list, not adding duplicate');
              return prev;
            }
            return [...prev, newChat];
          });
        }
      }
    } catch (err: any) {
      console.error('Error selecting chat:', err);
      setError(err.response?.data?.error || 'Ошибка при загрузке чата');
      // В случае ошибки не меняем текущий чат
    } finally {
      setIsLoading(false);
    }
  }, []); // Убираем зависимости, так как используем функциональное обновление состояния

  // Используем useCallback для функции createNewChat
  const createNewChat = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Создаем новый чат через API
      const response = await chatService.createChat();
      
      // Создаем объект чата
      const newChat: Chat = {
        id: response.chat_id,
        user_id: response.user_id,
        title: response.title || 'Новый чат',
        messages: [],
        createdAt: response.created_at,
        updatedAt: response.updated_at,
        message_count: response.message_count,
        is_active: response.is_active
      };
      
      // Добавляем новый чат в список
      setChats(prevChats => [newChat, ...prevChats]);
      
      // Устанавливаем новый чат как текущий
      setCurrentChat(newChat);
      
      console.log('New chat created:', newChat);
      
      // Загружаем историю чата с сервера (включая приветственное сообщение)
      try {
        const history = await chatService.getChatHistory(response.chat_id);
        if (history && Array.isArray(history.messages)) {
          setCurrentChat(prev => prev ? {
            ...prev,
            messages: history.messages
          } : null);
        }
      } catch (historyErr) {
        console.error('Error loading chat history:', historyErr);
      }
    } catch (err: any) {
      console.error('Error creating new chat:', err);
      setError(err.response?.data?.detail || 'Ошибка при создании чата');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const uploadPhoto = useCallback(async (file: File): Promise<{ description: string; image_url: string }> => {
    setUploadingPhotos(true);
    try {
      console.log('Uploading photo:', file.name, file.type, file.size);
      const result = await chatService.uploadPhoto(file);
      console.log('Upload result:', result);
      return result;
    } catch (error: any) {
      console.error('Failed to upload photo:', error);
      console.error('Error response:', error.response?.data);
      setError(error.response?.data?.detail || error.response?.data?.error || 'Ошибка при загрузке фото');
      throw error;
    } finally {
      setUploadingPhotos(false);
    }
  }, []);

  const uploadDocument = useCallback(async (file: File): Promise<{ text: string; filename: string; text_length: number }> => {
    setUploadingDocuments(true);
    try {
      console.log('Uploading document:', file.name, file.type, file.size);
      const result = await chatService.parseDocument(file);
      console.log('Document parse result:', result);
      return result;
    } catch (error: any) {
      console.error('Failed to parse document:', error);
      console.error('Error response:', error.response?.data);
      setError(error.response?.data?.detail || error.response?.data?.error || 'Ошибка при парсинге документа');
      throw error;
    } finally {
      setUploadingDocuments(false);
    }
  }, []);

  const sendMessage = async (message: string, photoData?: { description?: string; imageUrl?: string }, documentData?: { text: string; filename: string }, chatType: 'support' | 'contract' = 'support') => {
    if (!message.trim() && !photoData && !documentData) {
      console.error('Cannot send empty message without content, photo or document');
      return;
    }

    console.log('Sending message:', message, 'with photoData:', photoData, 'with documentData:', documentData);

    try {
      // Проверяем наличие активного чата
      if (!currentChat) {
        console.error('No active chat selected');
        setError('Создайте чат для отправки сообщения');
        return;
      }

      // Определяем тип файла если есть документ
      const fileType = documentData ? getFileType(documentData.filename) : undefined;
      const validFileType = (fileType === 'pdf' || fileType === 'doc' || fileType === 'docx' || fileType === 'txt') 
        ? fileType as 'pdf' | 'doc' | 'docx' | 'txt' 
        : undefined;

      // Создаем сообщение пользователя для UI
      // Для файлов: imageUrl содержит имя файла (для определения типа отображения)
      // Для фото: imageUrl содержит URL фото
      const userMessage: Message = {
        role: 'assistant',
        content: message.trim() || '', // Всегда сохраняем текст сообщения, если он был введен
        timestamp: new Date().toISOString(),
        imageUrl: documentData ? documentData.filename : photoData?.imageUrl, // Для файлов - имя файла, для фото - URL
        fileName: documentData?.filename,
        fileType: validFileType,
      };
      
      console.log('Creating user message for UI:', {
        content: userMessage.content,
        imageUrl: userMessage.imageUrl,
        fileName: userMessage.fileName,
        hasContent: !!userMessage.content?.trim()
      });

      // Оптимистично добавляем сообщение в UI
      setCurrentChat(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: [...prev.messages, userMessage],
          updatedAt: new Date().toISOString()
        };
      });

      // Определяем, первое ли это сообщение в чате
      const isFirstMessage = currentChat.messages.length === 0;

      // Подготавливаем запрос к API
      // Для файлов: photo_description содержит текст файла, photo_url содержит имя файла
      // Для фото: photo_description содержит описание фото, photo_url содержит URL фото
      // message всегда содержит текст пользователя (если он был введен), даже если есть файл или фото
      const request: MessageRequest = {
        message: message.trim() || '', // Всегда отправляем текст пользователя, даже если он пустой
        chat_id: currentChat.id,
        chat_type: chatType,
        is_first: isFirstMessage,
        photo_description: documentData ? documentData.text : photoData?.description,
        photo_url: documentData ? documentData.filename : photoData?.imageUrl,
        business_id: selectedBusinessId || null,
      };

      console.log('Sending to API:', request);

      // Отправляем сообщение
      const response = await chatService.sendMessage(request);
      console.log('Message sent, response:', response);

      // Обновляем время последнего сообщения в списке чатов
      setChats(prevChats => {
        return prevChats.map(chat => {
          if (chat.id === currentChat.id) {
            return {
              ...chat,
              updatedAt: new Date().toISOString(),
              message_count: (chat.message_count || 0) + 1
            };
          }
          return chat;
        });
      });

      // Показываем индикатор "печатает..." (ответ придет через WebSocket)
      setIsTyping(true);

    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      // Удаляем оптимистично добавленное сообщение при ошибке
      setCurrentChat(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: prev.messages.slice(0, -1)
        };
      });
      
      setError(error.response?.data?.detail || 'Ошибка при отправке сообщения');
    }
  };

  const uploadPhotoForAnalysis = useCallback(async (photo: File) => {
    setIsLoading(true);
    setError(null);
    
    try {
      console.log('Uploading photo for analysis...');
      
      // Получаем ID текущего чата
      let currentChatId = currentChat?.id;
      
      // Проверяем, нужно ли создавать новый чат
      if (!currentChatId || currentChatId === '000000000000000000000000' || currentChatId === 'undefined' || currentChatId === 'null') {
        console.log('Will use server-side chat creation for photo analysis');
        currentChatId = undefined; // Устанавливаем undefined, чтобы сервер создал новый чат
        
        // Создаем временный чат для отображения в UI
        if (!currentChat) {
          const tempChat: Chat = {
            id: 'temp-id',
            title: 'Новый анализ',
            messages: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString()
          };
          setCurrentChat(tempChat);
        }
      } else {
        console.log('Using existing chat ID for photo analysis:', currentChatId);
      }
      
      // Добавляем временное сообщение пользователя с изображением в чат
      const imageUrl = URL.createObjectURL(photo);
      
      // Создаем сообщение пользователя
      const userMessage: Message = {
        role: 'user',
        content: 'Анализ изображения',
        imageUrl: imageUrl,
        timestamp: new Date().toISOString()
      };
      
      // Добавляем сообщение пользователя в чат (для всех случаев)
      setCurrentChat(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: [...(prev.messages || []), userMessage]
        };
      });
      
      // Создаем временное сообщение ассистента
      const tempAssistantMessage: Message = {
        role: 'assistant',
        content: 'Обрабатываю фото...',
        timestamp: new Date().toISOString()
      };
      
      // Добавляем временное сообщение ассистента в чат (для всех случаев)
      setCurrentChat(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          messages: [...(prev.messages || []), tempAssistantMessage]
        };
      });
      
      // Формируем полный URL изображения
      const getFullImageUrl = (url: string): string => {
        if (!url) return '';
        
        // Если URL является blob URL, возвращаем его как есть
        if (url.startsWith('blob:')) {
          return url;
        }
        
        // Если URL уже начинается с http, возвращаем его как есть
        if (url.startsWith('http')) {
          return url;
        }
        
        // Иначе добавляем базовый URL
        const baseUrl = 'http://localhost:8080';
        return url.startsWith('/') ? `${baseUrl}${url}` : `${baseUrl}/${url}`;
      };
      
      // Отправляем фото на анализ
      const { analysis, imageUrl: serverImageUrl, chatId, parsingResults } = await chatService.analyzePhoto(
        photo, 
        currentChatId
      );
      
      // Формируем полный URL изображения
      const fullImageUrl = getFullImageUrl(serverImageUrl);
      
      console.log('Получен ответ от сервера:', { analysis, serverImageUrl, fullImageUrl, chatId, parsingResults });
      
      // Если сервер вернул chatId, значит был создан новый чат или использован существующий
      if (chatId) {
        console.log('Получен chatId от сервера:', chatId);
        
        // Обновляем список чатов
        await refreshChats();
        
        // Получаем историю чата с сервера
        const newChat = await chatService.getChatHistory(chatId);
        if (newChat && newChat.messages) {
          setCurrentChat({
            id: chatId,
            messages: newChat.messages,
            title: newChat.title || 'Анализ фотографии',
            createdAt: newChat.createdAt || new Date().toISOString(),
            updatedAt: newChat.updatedAt || new Date().toISOString()
          });
          return; // Выходим из функции, так как чат уже обновлен
        }
      }
      
      // Если не был создан новый чат, обновляем текущий
      setCurrentChat(prev => {
        if (!prev) return prev;
        const updatedMessages = [...(prev.messages || [])];
        
        // Находим сообщение пользователя и обновляем его изображение
        const userMessageIndex = updatedMessages.findIndex(msg => 
          msg.role === 'user' && (msg.imageUrl === imageUrl || msg.content === ''));
        
        if (userMessageIndex !== -1) {
          // Сохраняем исходный URL изображения, если это blob URL
          const originalImageUrl = updatedMessages[userMessageIndex].imageUrl;
          const shouldKeepOriginalUrl = originalImageUrl && originalImageUrl.startsWith('blob:');
          
          updatedMessages[userMessageIndex] = {
            ...updatedMessages[userMessageIndex],
            imageUrl: shouldKeepOriginalUrl ? originalImageUrl : fullImageUrl
          };
          
          // Добавляем серверный URL изображения в отдельное поле
          if (shouldKeepOriginalUrl) {
            updatedMessages[userMessageIndex] = {
              ...updatedMessages[userMessageIndex],
              serverImageUrl: fullImageUrl // Сохраняем серверный URL в отдельном поле
            };
          }
        }
        
        // Находим временное сообщение ассистента и обновляем его содержимое
        const assistantMessageIndex = updatedMessages.findIndex(msg => 
          msg.role === 'assistant' && msg.content === 'Обрабатываю фото...');
        
        if (assistantMessageIndex !== -1) {
          updatedMessages[assistantMessageIndex] = {
            ...updatedMessages[assistantMessageIndex],
            content: analysis
          };
        }
        
        // Если есть результаты парсинга, добавляем их как новое сообщение ассистента
        if (parsingResults) {
          console.log('Добавляем результаты парсинга в чат:', parsingResults);
          
          const parsingMessage: Message = {
            role: 'assistant',
            content: parsingResults,
            timestamp: new Date().toISOString()
          };
          
          updatedMessages.push(parsingMessage);
        }
        
        return {
          ...prev,
          messages: updatedMessages
        };
      });
    } catch (error) {
      console.error('Error uploading photo for analysis:', error);
      setError('Не удалось проанализировать фотографию');
      
      // Удаляем временное сообщение ассистента в случае ошибки
      setCurrentChat(prev => {
        if (!prev) return prev;
        const updatedMessages = [...(prev.messages || [])];
        const tempAssistantIndex = updatedMessages.findIndex(msg => 
          msg.role === 'assistant' && msg.content === 'Обрабатываю фото...');
        
        if (tempAssistantIndex !== -1) {
          updatedMessages.splice(tempAssistantIndex, 1);
        }
        
        return {
          ...prev,
          messages: updatedMessages
        };
      });
    } finally {
      setIsLoading(false);
    }
  }, [currentChat, setIsLoading, setError, setCurrentChat, refreshChats]);

  const deleteChat = async (chatId: string) => {
    // Проверяем, что chatId является валидным ID
    if (!chatId || chatId === 'undefined' || chatId === 'null' || chatId === '000000000000000000000000' || chatId === 'temp-id') {
      console.log('Invalid chat ID, not deleting:', chatId);
      
      // Удаляем чат из локального списка
      setChats(prev => prev.filter(chat => chat.id !== chatId));
      
      // Если удаляемый чат был текущим, сбрасываем текущий чат
      if (currentChat && currentChat.id === chatId) {
        setCurrentChat(null);
      }
      
      return;
    }
    
    setIsLoading(true);
    setError(null);
    try {
      console.log(`Deleting chat ${chatId}...`);
      await chatService.deleteChat(chatId);
      console.log(`Successfully deleted chat ${chatId}`);
      
      // Обновляем список чатов
      setChats(prev => prev.filter(chat => chat.id !== chatId));
      
      // Если удаляемый чат был текущим, сбрасываем текущий чат
      if (currentChat && currentChat.id === chatId) {
        setCurrentChat(null);
      }
    } catch (err: any) {
      console.error('Error deleting chat:', err);
      setError(err.response?.data?.error || 'Ошибка при удалении чата');
      
      // Если чата нет на сервере, удаляем его из локального списка
      if (err.response?.status === 404 || (err.response?.data?.error && err.response.data.error.includes('не найден'))) {
        console.log('Chat not found on server, removing from local state');
        setChats(prev => prev.filter(chat => chat.id !== chatId));
        
        if (currentChat && currentChat.id === chatId) {
          setCurrentChat(null);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Функция для добавления сообщения в текущий чат (для WebSocket)
  const addMessageToCurrentChat = useCallback((message: Message) => {
    console.log('ChatContext - addMessageToCurrentChat called:', message);
    
    // Если это сообщение от бота, отключаем индикатор "печатает"
    if (message.message_type === 'bot') {
      setIsTyping(false);
    }
    
    setCurrentChat(prev => {
      if (!prev) {
        console.log('ChatContext - No current chat, skipping message add');
        return prev;
      }
      
      // Проверяем, нет ли уже такого сообщения (по id или по timestamp и content)
      const isDuplicate = prev.messages.some(m => 
        (m.id && message.id && m.id === message.id) ||
        (m.timestamp === message.timestamp && m.content === message.content)
      );
      
      if (isDuplicate) {
        console.log('ChatContext - Duplicate message detected, skipping');
        return prev;
      }
      
      console.log('ChatContext - Adding message to current chat');
      return {
        ...prev,
        messages: [...prev.messages, message],
        updatedAt: message.timestamp || new Date().toISOString(),
        message_count: (prev.message_count || 0) + 1
      };
    });
    
    // Также обновляем чат в списке чатов
    setChats(prevChats => {
      const updatedChats = prevChats.map(chat => {
        if (currentChat && chat.id === currentChat.id) {
          return {
            ...chat,
            updatedAt: message.timestamp || new Date().toISOString(),
            message_count: (chat.message_count || 0) + 1
          };
        }
        return chat;
      });
      return updatedChats;
    });
  }, [currentChat]);

  // Закрытие тикета
  const closeTicket = async (userId: string, comment?: string) => {
    try {
      setIsLoading(true);
      console.log('Closing ticket for user:', userId);
      
      await chatService.closeTicket(userId, comment);
      
      // После успешного закрытия обновляем список чатов
      await refreshChats();
      
      // Сбрасываем текущий чат
      setCurrentChat(null);
      
      console.log('Ticket closed successfully');
    } catch (err: any) {
      console.error('Error closing ticket:', err);
      setError(err.response?.data?.error || 'Ошибка при закрытии тикета');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  // Отметить чат как закрывающийся
  const markChatAsClosing = useCallback((chatId: string, delayMs: number) => {
    const closingAt = Date.now() + delayMs;
    
    setChats(prevChats => 
      prevChats.map(chat => 
        chat.id === chatId 
          ? { ...chat, is_closing: true, closing_at: closingAt }
          : chat
      )
    );

    // Также обновляем currentChat если это он
    setCurrentChat(prev => 
      prev && prev.id === chatId 
        ? { ...prev, is_closing: true, closing_at: closingAt }
        : prev
    );

    console.log(`Chat ${chatId} marked as closing, will be deleted at ${new Date(closingAt).toLocaleTimeString()}`);
  }, []);

  // Обновить заголовок чата
  const updateChatTitle = useCallback((chatId: string, newTitle: string) => {
    console.log(`Updating chat ${chatId} title to: ${newTitle}`);
    
    setChats(prevChats => 
      prevChats.map(chat => 
        chat.id === chatId 
          ? { ...chat, title: newTitle }
          : chat
      )
    );

    // Также обновляем currentChat если это он
    setCurrentChat(prev => 
      prev && prev.id === chatId 
        ? { ...prev, title: newTitle }
        : prev
    );
  }, []);

  useEffect(() => {
    window.uploadPhotoForAnalysis = uploadPhotoForAnalysis;
    
    // Очистка при размонтировании
    return () => {
      window.uploadPhotoForAnalysis = undefined;
    };
  }, [currentChat, isLoading, uploadPhotoForAnalysis, refreshChats]);

  const value = {
    chats,
    currentChat,
    isLoading,
    error,
    isTyping,
    uploadingPhotos,
    uploadingDocuments,
    selectedBusinessId,
    setSelectedBusinessId,
    sendMessage,
    selectChat,
    createNewChat,
    deleteChat,
    refreshChats,
    uploadPhotoForAnalysis,
    addMessageToCurrentChat,
    closeTicket,
    markChatAsClosing,
    updateChatTitle,
    uploadPhoto,
    uploadDocument,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};
