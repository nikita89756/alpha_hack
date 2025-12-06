import React, { useEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import ChatSidebar from '../components/ChatSidebar';
import ChatMessages from '../components/ChatMessages';
import Dashboard from '../components/Dashboard';
import Calendar from '../components/Calendar';
import PLDashboard from '../components/PLDashboard';
import { useChat } from '../context/ChatContext';
import { useWebSocket } from '../hooks/useWebSocket';
import { Message } from '../types';
import { isDocumentFile, isImageFile, getFileInfo, renderFileIcon } from '../utils/fileUtils';

// Типы для Speech Recognition API
interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

declare var SpeechRecognition: {
  new (): SpeechRecognition;
};

declare var webkitSpeechRecognition: {
  new (): SpeechRecognition;
};

const ChatPage: React.FC = () => {
  const location = useLocation();
  const { currentChat, sendMessage, isLoading, isTyping, uploadingPhotos, uploadingDocuments, selectChat, refreshChats, createNewChat, uploadPhotoForAnalysis, addMessageToCurrentChat, deleteChat, markChatAsClosing, chats, updateChatTitle, uploadPhoto, uploadDocument } = useChat();
  const [error, setError] = useState<string | null>(null);
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [uploadedPhotos, setUploadedPhotos] = useState<{ file: File; previewUrl: string; description?: string; imageUrl?: string; uploading: boolean }[]>([]);
  const [uploadedDocuments, setUploadedDocuments] = useState<{ file: File; filename: string; text?: string; uploading: boolean }[]>([]);
  const chatLoadedFromStateRef = useRef(false);
  const [titleUpdateAnimation, setTitleUpdateAnimation] = useState(false);
  const [incomingMessages, setIncomingMessages] = useState<Message[]>([]);
  const [connectedChatId, setConnectedChatId] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'chat' | 'focus-week' | 'pl-wb' | 'calendar'>('chat');
  const [mobileTabMenuOpen, setMobileTabMenuOpen] = useState(false);
  const [chatMode, setChatMode] = useState<'support' | 'contract'>('support');
  const [hoveredMode, setHoveredMode] = useState<'support' | 'contract' | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingSpeech, setIsProcessingSpeech] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Обновляем connectedChatId только когда меняется ID чата, а не объект
  useEffect(() => {
    const newChatId = currentChat?.id || null;
    console.log('📍 ChatPage: currentChat?.id changed:', newChatId, 'current connectedChatId:', connectedChatId);
    if (newChatId !== connectedChatId) {
      console.log('✅ Chat ID changed, updating WebSocket connection from', connectedChatId, 'to', newChatId);
      setConnectedChatId(newChatId);
    } else {
      console.log('⏭️ Chat ID unchanged, skipping WebSocket reconnection');
    }
  }, [currentChat?.id, connectedChatId]); // Зависимость только от ID, а не всего объекта

  // WebSocket подключение для получения сообщений в реальном времени
  useWebSocket(connectedChatId, {
    onMessage: (data) => {
      console.log('=== WEBSOCKET MESSAGE RECEIVED ===');
      console.log('Full data:', data);
      
      // Обработка события обновления заголовка чата
      if (data.type === 'title_updated') {
        console.log('✅ Chat title update received:', data.title);
        
        // Анимация обновления
        setTitleUpdateAnimation(true);
        setTimeout(() => setTitleUpdateAnimation(false), 1000);
        
        // Мгновенно обновляем заголовок локально
        updateChatTitle(data.chat_id, data.title);
        
        return;
      }
      
      // Обработка события закрытия чата
      if (data.type === 'chat_closed') {
        console.log('✅ Chat close event received');
        
        // Добавляем финальное сообщение от бота
        const finalMessage: Message = {
          id: `close-${Date.now()}`,
          role: 'user', // bot messages отображаются как 'user' в UI
          content: data.message || 'Чат завершен. Спасибо за обращение!',
          timestamp: data.timestamp || new Date().toISOString(),
          message_type: 'bot'
        };
        
        setIncomingMessages(prev => [...prev, finalMessage]);
        
        // Отмечаем чат как закрывающийся (для визуальной индикации)
        const deleteDelay = 15000; // 15 секунд
        markChatAsClosing(data.chat_id, deleteDelay);
        
        // Автоматически удаляем чат через 15 секунд и переключаемся на другой чат
        setTimeout(() => {
          console.log('Auto-removing closed chat:', data.chat_id);
          
          // Если это текущий чат, переключаемся на другой
          if (currentChat?.id === data.chat_id) {
            const otherChats = chats.filter(chat => chat.id !== data.chat_id);
            if (otherChats.length > 0) {
              selectChat(otherChats[0].id);
            }
          }
          
          // Удаляем чат
          deleteChat(data.chat_id);
        }, deleteDelay);
        
        return;
      }
      
      // Проверяем что это сообщение от бота (bot response)
      // Backend может отправить как message+message_type, так и bot_response
      const botMessage = data.bot_response || data.message;
      const messageType = data.message_type || (data.bot_response ? 'bot' : null);
      
      if (botMessage && (messageType === 'bot' || data.bot_response)) {
        console.log('✅ Message from bot, adding to chat');
        const newMessage: Message = {
          id: data.message_id || data.id,
          role: 'user', // bot messages отображаются как 'user' в UI
          content: botMessage,
          timestamp: data.timestamp,
          message_type: 'bot',
          source: data.source,
          source_links: data.source_links,
          next_action: data.next_action
        };
        
        // Добавляем сообщение в список входящих
        setIncomingMessages(prev => [...prev, newMessage]);
      } else {
        console.log('❌ Message ignored - data:', data);
      }
    },
    onOpen: () => {
      console.log('WebSocket connected');
    },
    onClose: () => {
      console.log('WebSocket disconnected');
    },
    onError: (error) => {
      console.error('WebSocket error:', error);
    }
  });

  // Добавляем входящие сообщения в текущий чат
  useEffect(() => {
    if (incomingMessages.length > 0 && currentChat) {
      console.log('New incoming messages:', incomingMessages);
      
      // Добавляем каждое сообщение в текущий чат через ChatContext
      incomingMessages.forEach(message => {
        addMessageToCurrentChat(message);
      });
      
      // Очищаем список входящих
      setIncomingMessages([]);
    }
  }, [incomingMessages, currentChat, addMessageToCurrentChat]);
  
  // Отключаем индикатор "печатает" при получении сообщения от бота
  useEffect(() => {
    if (incomingMessages.length > 0 && incomingMessages.some(msg => msg.message_type === 'bot') && isTyping) {
      console.log('Bot message received, stopping typing indicator');
      // Индикатор будет выключен автоматически через ChatContext
    }
  }, [incomingMessages, isTyping]);

  // Добавлено логирование текущего чата при его изменении
  useEffect(() => {
    console.log('Current chat updated:', currentChat);
    // Сбрасываем ошибку при смене чата
    setError(null);
    // Сбрасываем входящие сообщения при смене чата
    setIncomingMessages([]);
  }, [currentChat]);

  // Обработка вставки сообщения из sessionStorage при переключении на вкладку чата
  useEffect(() => {
    if (selectedTab === 'chat' && currentChat) {
      const insertPendingMessage = () => {
        const pendingMessage = sessionStorage.getItem('pendingMessage');
        if (pendingMessage) {
          const textarea = document.querySelector('textarea[data-component-name="ChatInput"]') as HTMLTextAreaElement;
          if (textarea) {
            textarea.value = pendingMessage;
            textarea.focus();
            // Триггерим событие input для обновления высоты
            const event = new Event('input', { bubbles: true });
            textarea.dispatchEvent(event);
            sessionStorage.removeItem('pendingMessage');
          } else {
            // Если поле ввода еще не готово, повторяем попытку
            setTimeout(insertPendingMessage, 100);
          }
        }
      };
      
      // Пробуем вставить сообщение через небольшую задержку
      setTimeout(insertPendingMessage, 300);
    }
  }, [selectedTab, currentChat]);

  // Проверяем, есть ли chat_id в state навигации
  useEffect(() => {
    const state = location.state as { chat_id?: string } | null;
    
    console.log('ChatPage - location.state:', state);
    console.log('ChatPage - chatLoadedFromStateRef.current:', chatLoadedFromStateRef.current);
    
    if (state?.chat_id && !chatLoadedFromStateRef.current) {
      console.log('Loading chat from navigation state:', state.chat_id);
      selectChat(state.chat_id).catch(error => {
        console.error('Error loading chat:', error);
      });
      chatLoadedFromStateRef.current = true;
    }
  }, [location.state, selectChat]);

  // Обработчик отправки сообщения с обработкой ошибок
  const handleSendMessage = async (message: string, mode?: 'support' | 'contract') => {
    const effectiveMode = mode || chatMode;
    try {
      // Проверяем что все фото и документы загружены
      const hasUploadingPhotos = uploadedPhotos.some(photo => photo.uploading);
      const hasUploadingDocuments = uploadedDocuments.some(doc => doc.uploading);
      
      if (hasUploadingPhotos) {
        setError('Дождитесь загрузки фотографий');
        return;
      }
      
      if (hasUploadingDocuments) {
        setError('Дождитесь загрузки документов');
        return;
      }

      console.log('ChatPage - handleSendMessage:', message, 'photos:', uploadedPhotos.length, 'documents:', uploadedDocuments.length);
      setError(null);
      
      // Преобразуем данные фото для отправки
      const photoData = uploadedPhotos.length > 0 ? {
        description: uploadedPhotos[0].description,
        imageUrl: uploadedPhotos[0].imageUrl
      } : undefined;
      
      // Преобразуем данные документа для отправки
      const documentData = uploadedDocuments.length > 0 ? {
        text: uploadedDocuments[0].text || '',
        filename: uploadedDocuments[0].filename
      } : undefined;
      
      await sendMessage(message, photoData, documentData, effectiveMode);
    } catch (err: any) {
      console.error('Error sending message:', err);
      setError(err.message || 'Ошибка при отправке сообщения');
      // Обновляем список чатов в случае ошибки, чтобы убедиться, что UI синхронизирован
      refreshChats();
    }
  };

  // Обработчик выбора фото
  const handlePhotoSelect = async (file: File) => {
    // Создаем временный URL для превью
    const previewUrl = URL.createObjectURL(file);
    
    // Добавляем фото с индикатором загрузки
    const photoIndex = uploadedPhotos.length;
    setUploadedPhotos(prev => [...prev, { 
      file, 
      previewUrl, 
      uploading: true 
    }]);
    
    // Загружаем фото на сервер и получаем описание
    try {
      const result = await uploadPhoto(file);
      
      // Обновляем фото с полученными данными
      setUploadedPhotos(prev => prev.map((photo, idx) => 
        idx === photoIndex 
          ? { ...photo, description: result.description, imageUrl: result.image_url, uploading: false }
          : photo
      ));
      
      console.log('Photo uploaded and analyzed:', result);
    } catch (error) {
      console.error('Failed to upload photo:', error);
      // Оставляем фото но убираем индикатор загрузки
      setUploadedPhotos(prev => prev.map((photo, idx) => 
        idx === photoIndex 
          ? { ...photo, uploading: false }
          : photo
      ));
      setError('Не удалось загрузить фото');
    }
  };

  // Обработчик выбора документа
  const handleDocumentSelect = async (file: File) => {
    // Добавляем документ с индикатором загрузки
    const docIndex = uploadedDocuments.length;
    setUploadedDocuments(prev => [...prev, { 
      file, 
      filename: file.name,
      uploading: true 
    }]);
    
    // Парсим документ на сервере
    try {
      const result = await uploadDocument(file);
      
      // Обновляем документ с полученным текстом
      setUploadedDocuments(prev => prev.map((doc, idx) => 
        idx === docIndex 
          ? { ...doc, text: result.text, uploading: false }
          : doc
      ));
      
      console.log('Document uploaded and parsed:', result);
    } catch (error) {
      console.error('Failed to parse document:', error);
      // Оставляем документ но убираем индикатор загрузки
      setUploadedDocuments(prev => prev.map((doc, idx) => 
        idx === docIndex 
          ? { ...doc, uploading: false }
          : doc
      ));
      setError('Не удалось распарсить документ');
    }
  };

  // Обработчик выбора файла (фото или документ)
  const handleFileSelect = (file: File) => {
    if (isImageFile(file.name)) {
      handlePhotoSelect(file);
    } else if (isDocumentFile(file.name)) {
      handleDocumentSelect(file);
    } else {
      setError('Неподдерживаемый тип файла. Поддерживаются: PDF, DOC, DOCX, TXT и изображения');
    }
  };

  // Удаление конкретного фото по индексу
  const handleRemovePhoto = (index: number) => {
    // Освобождаем URL
    const photo = uploadedPhotos[index];
    if (photo?.previewUrl) {
      URL.revokeObjectURL(photo.previewUrl);
    }
    
    // Удаляем фото из массива
    setUploadedPhotos(prev => prev.filter((_, i) => i !== index));
  };

  // Удаление конкретного документа по индексу
  const handleRemoveDocument = (index: number) => {
    // Удаляем документ из массива
    setUploadedDocuments(prev => prev.filter((_, i) => i !== index));
  };

  // Очистка всех фото и документов
  const handleClearAllFiles = () => {
    // Освобождаем все URL
    uploadedPhotos.forEach(photo => {
      if (photo.previewUrl) {
        URL.revokeObjectURL(photo.previewUrl);
      }
    });
    
    setUploadedPhotos([]);
    setUploadedDocuments([]);
  };

  // Инициализация Speech Recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognitionClass = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognitionClass) {
        const recognition = new SpeechRecognitionClass();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'ru-RU';

        recognition.onstart = () => {
          setIsRecording(true);
        };

        recognition.onresult = (event: any) => {
          const transcript = Array.from(event.results)
            .map((result: any) => result[0].transcript)
            .join('');
          
          setIsProcessingSpeech(true);
          setIsRecording(false);
          
          // Вставляем текст в поле ввода
          const textarea = textareaRef.current || document.querySelector('textarea[data-component-name="ChatInput"]') as HTMLTextAreaElement;
          if (textarea) {
            const currentText = textarea.value;
            const newText = currentText ? `${currentText} ${transcript}` : transcript;
            textarea.value = newText;
            
            // Триггерим событие input для обновления высоты
            const inputEvent = new Event('input', { bubbles: true });
            textarea.dispatchEvent(inputEvent);
            
            // Фокусируем поле ввода
            textarea.focus();
          }
          
          // Завершаем обработку через небольшую задержку
          setTimeout(() => {
            setIsProcessingSpeech(false);
          }, 500);
        };

        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          setIsRecording(false);
          setIsProcessingSpeech(false);
          if (event.error === 'not-allowed') {
            setError('Разрешите доступ к микрофону в настройках браузера');
          } else {
            setError('Ошибка распознавания речи');
          }
        };

        recognition.onend = () => {
          setIsRecording(false);
        };

        recognitionRef.current = recognition;
      }
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // Обработчик нажатия на кнопку микрофона
  const handleMicrophoneClick = () => {
    if (!recognitionRef.current) {
      setError('Распознавание речи не поддерживается в вашем браузере');
      return;
    }

    if (isRecording) {
      // Останавливаем запись
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      // Начинаем запись
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error('Error starting recognition:', error);
        setError('Не удалось начать запись');
      }
    }
  };

  // Обновляем позицию кнопок при изменении превью файлов
  useEffect(() => {
    const updateButtonsPosition = () => {
      const textarea = document.querySelector('textarea[data-component-name="ChatInput"]') as HTMLTextAreaElement;
      const filePreview = document.querySelector('.px-3.pt-2.pb-2.border-b, .px-5.pt-2.pb-2.border-b') as HTMLElement;
      const buttonsContainer = document.querySelector('div[data-component-name="ChatPage"]') as HTMLElement;
      
      if (textarea && buttonsContainer) {
        const textareaExtraHeight = Math.max(0, textarea.clientHeight - 44);
        const fileHeight = filePreview ? filePreview.clientHeight : 0;
        const totalExtraHeight = textareaExtraHeight + fileHeight;
        const sidebarOffset = sidebarVisible && window.innerWidth >= 640 ? '16rem' : '0';
        const bottomOffset = window.innerWidth < 640 ? '4rem' : '6rem';
        
        buttonsContainer.style.left = sidebarOffset;
        buttonsContainer.style.bottom = `calc(${bottomOffset} + ${totalExtraHeight}px)`;
      }
    };

    // Небольшая задержка чтобы DOM успел обновиться
    const timer = setTimeout(updateButtonsPosition, 50);
    // Также обновляем при изменении размера окна
    window.addEventListener('resize', updateButtonsPosition);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', updateButtonsPosition);
    };
  }, [uploadedPhotos, uploadedDocuments, sidebarVisible]);

  return (
    <div className="flex h-screen bg-dark-primary text-dark-text overflow-hidden">
      {/* Sidebar - скрыт на мобильных по умолчанию, показывается как overlay, занимает весь экран на мобильных */}
      <div 
        className={`fixed sm:relative z-50 sm:z-auto h-full transition-all duration-300 ease-in-out ${
          sidebarVisible 
            ? 'w-full sm:w-64 opacity-100' 
            : 'w-0 sm:w-0 opacity-0 overflow-hidden'
        }`}
      >
        <ChatSidebar onClose={() => setSidebarVisible(false)} />
      </div>
      
      {/* Overlay для мобильных устройств */}
      {sidebarVisible && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 sm:hidden"
          onClick={() => setSidebarVisible(false)}
        />
      )}
      
      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b border-dark-border/20 p-3 sm:p-4 flex items-center relative">
          <div className="absolute left-2 sm:left-4 z-10">
            <button 
              onClick={() => {
                console.log('Toggle sidebar clicked, current state:', sidebarVisible);
                setSidebarVisible(!sidebarVisible);
              }}
              className="text-dark-text hover:text-custom-blue focus:outline-none p-2 hover:bg-dark-accent/30 rounded-lg transition-all"
              title={sidebarVisible ? 'Скрыть панель' : 'Показать панель'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                {sidebarVisible ? (
                  <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 10.5a.75.75 0 01.75-.75h7.5a.75.75 0 010 1.5h-7.5a.75.75 0 01-.75-.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10z" clipRule="evenodd" />
                ) : (
                  <path fillRule="evenodd" d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" clipRule="evenodd" />
                )}
              </svg>
            </button>
          </div>
          
          <div className="w-full flex justify-center items-center relative pointer-events-none px-10 sm:px-0">
            <div className="max-w-[48rem] w-full text-center pointer-events-auto">
              <h2 
                className={`text-base sm:text-lg font-medium transition-all duration-500 ${
                  titleUpdateAnimation 
                    ? 'scale-105 text-custom-blue' 
                    : 'scale-100'
                }`}
                data-component-name="ChatPage"
              >
                {selectedTab === 'focus-week' 
                  ? 'Планирование' 
                  : selectedTab === 'pl-wb'
                    ? 'P&L по WB'
                    : selectedTab === 'calendar'
                      ? 'Календарь'
                      : currentChat 
                        ? (currentChat.title || `Заявка #${currentChat.id.substring(0, 8)}`) 
                        : 'Помощник по микробизнесу'}
                {titleUpdateAnimation && (
                  <span className="ml-2 inline-block text-custom-blue">✨</span>
                )}
              </h2>
            </div>
          </div>
          
          {/* Меню табов в правой части панели */}
          <div className="absolute right-2 sm:right-4 z-10 pointer-events-auto">
            {/* Мобильная версия - меню с тремя линиями */}
            <div className="sm:hidden relative">
              <button
                onClick={() => setMobileTabMenuOpen(!mobileTabMenuOpen)}
                className="text-dark-text/70 hover:text-dark-text hover:bg-dark-accent/30 p-2 rounded-lg transition-all"
                title="Меню"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              
              {/* Выпадающее меню для мобильных */}
              {mobileTabMenuOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setMobileTabMenuOpen(false)}
                  />
                  <div 
                    className="absolute right-0 top-full mt-2 w-48 bg-dark-secondary border border-dark-border/50 rounded-lg shadow-lg z-50 overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <button
                      onClick={() => {
                        setSelectedTab('chat');
                        setMobileTabMenuOpen(false);
                      }}
                      className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center justify-between"
                    >
                      <span>Чат</span>
                      {selectedTab === 'chat' && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                    
                    <button
                      onClick={() => {
                        setSelectedTab('focus-week');
                        setMobileTabMenuOpen(false);
                      }}
                      className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center justify-between border-t border-dark-border/30"
                    >
                      <span>Планирование</span>
                      {selectedTab === 'focus-week' && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                    
                    <button
                      onClick={() => {
                        setSelectedTab('pl-wb');
                        setMobileTabMenuOpen(false);
                      }}
                      className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center justify-between border-t border-dark-border/30"
                    >
                      <span>P&L по WB</span>
                      {selectedTab === 'pl-wb' && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                    
                    <button
                      onClick={() => {
                        setSelectedTab('calendar');
                        setMobileTabMenuOpen(false);
                      }}
                      className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center justify-between border-t border-dark-border/30"
                    >
                      <span>Календарь</span>
                      {selectedTab === 'calendar' && (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                  </div>
                </>
              )}
            </div>
            
            {/* Десктопная версия - четыре кнопки */}
            <div className="hidden sm:flex bg-dark-accent/60 rounded-lg p-0.5 sm:p-1 gap-0.5 sm:gap-1">
              <button
                onClick={() => setSelectedTab('chat')}
                className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  selectedTab === 'chat'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
                title="Чат"
              >
                Чат
              </button>
              <button
                onClick={() => setSelectedTab('focus-week')}
                className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  selectedTab === 'focus-week'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
                title="Планирование"
              >
                Планирование
              </button>
              <button
                onClick={() => setSelectedTab('pl-wb')}
                className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  selectedTab === 'pl-wb'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
                title="P&L по WB"
              >
                P&L по WB
              </button>
              <button
                onClick={() => setSelectedTab('calendar')}
                className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  selectedTab === 'calendar'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
                title="Календарь"
              >
                Календарь
              </button>
            </div>
          </div>
          
          {/* Удален блок аккаунта, так как он перенесен в боковую панель */}
        </div>
        
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-2">
            <p>{error}</p>
          </div>
        )}
        
        {selectedTab === 'focus-week' ? (
          <Dashboard onChatSelect={(chatId) => {
            selectChat(chatId);
            setSelectedTab('chat');
          }} />
        ) : selectedTab === 'pl-wb' ? (
          <PLDashboard onSwitchToChat={() => {
            console.log('ChatPage: Switching to chat tab from PLDashboard');
            setSelectedTab('chat');
          }} />
        ) : selectedTab === 'calendar' ? (
          <Calendar onSwitchToChat={() => setSelectedTab('chat')} />
        ) : (
          <ChatMessages 
            messages={currentChat?.messages || []} 
            isLoading={isLoading}
            isTyping={isTyping}
            hasActiveChat={!!currentChat}
            onSendMessage={handleSendMessage}
            onCreateNewChat={createNewChat}
            chatId={currentChat?.id}
          />
        )}
        
        {currentChat && selectedTab === 'chat' && <div className="mb-4" />}
        
        {currentChat && selectedTab === 'chat' && (
        <div 
          className="fixed left-0 right-0 flex justify-center gap-2 px-2 sm:px-4 transition-all duration-300 ease-in-out z-30"
          style={{ 
            left: sidebarVisible && window.innerWidth >= 640 ? '16rem' : '0',
            bottom: window.innerWidth < 640 
              ? `calc(4rem + ${(document.querySelector('textarea[data-component-name="ChatInput"]')?.clientHeight || 44) - 44}px)`
              : `calc(6rem + ${(document.querySelector('textarea[data-component-name="ChatInput"]')?.clientHeight || 44) - 44}px)`
          }}
          data-component-name="ChatPage"
        >
          <div className="flex gap-2 w-full max-w-[48rem] justify-between items-center">
            {/* Левая группа кнопок - переключатель режимов с подложкой */}
            <div className="flex bg-dark-secondary/50 border border-custom-border/20 rounded-lg p-0.5 gap-0.5">
              {/* Кнопка "Микробизнес" */}
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setChatMode('support');
                  }}
                  onMouseEnter={() => setHoveredMode('support')}
                  onMouseLeave={() => setHoveredMode(null)}
                  disabled={isLoading}
                  className={`flex items-center gap-1.5 p-2 px-2.5 text-xs text-dark-text rounded-lg focus:outline-none disabled:opacity-50 transition-all duration-300 ${
                    chatMode === 'support'
                      ? 'bg-custom-blue/20 border border-custom-blue/30'
                      : 'hover:bg-dark-accent/30 border border-transparent'
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </button>
                
                {/* Кастомный тултип */}
                {hoveredMode === 'support' && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-dark-secondary border border-custom-border/50 rounded-lg shadow-lg whitespace-nowrap pointer-events-none z-50">
                    <div className="text-xs font-bold text-white mb-0.5">Помощник по микробизнесу</div>
                    <div className="text-xs text-gray-400">Помогает с вопросами по бизнесу,<br />финансам и развитию</div>
                    <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
                      <div className="border-4 border-transparent border-t-dark-secondary"></div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Кнопка "Документы" */}
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setChatMode('contract');
                  }}
                  onMouseEnter={() => setHoveredMode('contract')}
                  onMouseLeave={() => setHoveredMode(null)}
                  disabled={isLoading}
                  className={`flex items-center gap-1.5 p-2 px-2.5 text-xs text-dark-text rounded-lg focus:outline-none disabled:opacity-50 transition-all duration-300 ${
                    chatMode === 'contract'
                      ? 'bg-custom-blue/20 border border-custom-blue/30'
                      : 'hover:bg-dark-accent/30 border border-transparent'
                  }`}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </button>
                
                {/* Кастомный тултип */}
                {hoveredMode === 'contract' && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-dark-secondary border border-custom-border/50 rounded-lg shadow-lg whitespace-nowrap pointer-events-none z-50">
                    <div className="text-xs font-bold text-white mb-0.5">Помощник по документам</div>
                    <div className="text-xs text-gray-400">Анализирует договоры, соглашения<br />и юридические документы</div>
                    <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
                      <div className="border-4 border-transparent border-t-dark-secondary"></div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Центральная группа кнопок - новый чат и добавить файл */}
            <div className="flex gap-2 absolute left-1/2 -translate-x-1/2">
              <button
                onClick={() => !isLoading && createNewChat()}
                disabled={isLoading}
                className="flex items-center gap-1.5 px-3 py-2 text-xs text-dark-text border border-dark-border rounded-lg bg-dark-accent/90 hover:bg-dark-accent focus:outline-none focus:ring-2 focus:ring-custom-blue disabled:opacity-50 shadow-sm hover:shadow-md transition-all duration-300"
                title="Создать новую заявку"
                data-component-name="ChatPage"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <span className="whitespace-nowrap">новый чат</span>
              </button>
              
              <button
                onClick={() => {
                  if (isLoading) return;
                  
                  // Создаем скрытый input для выбора файла
                  const fileInput = document.createElement('input');
                  fileInput.type = 'file';
                  fileInput.accept = 'image/*,.pdf,.doc,.docx,.txt,.md';
                  fileInput.style.display = 'none';
                  
                  // Обработчик выбора файла
                  fileInput.onchange = (e) => {
                    const target = e.target as HTMLInputElement;
                    if (target.files && target.files.length > 0) {
                      const file = target.files[0];
                      handleFileSelect(file);
                    }
                  };
                  
                  // Добавляем input в DOM и имитируем клик
                  document.body.appendChild(fileInput);
                  fileInput.click();
                  
                  // Удаляем input из DOM после имитации клика
                  setTimeout(() => {
                    document.body.removeChild(fileInput);
                  }, 1000);
                }}
                disabled={isLoading || uploadingPhotos || uploadingDocuments}
                className="flex items-center gap-1.5 px-3 py-2 text-xs text-dark-text border border-dark-border rounded-lg bg-dark-accent/90 hover:bg-dark-accent focus:outline-none focus:ring-2 focus:ring-custom-blue disabled:opacity-50 shadow-sm hover:shadow-md transition-all duration-300"
                title="Добавить файл (фото или документ)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M4 5a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V7a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293l-1.121-1.121A2 2 0 0011.172 3H8.828a2 2 0 00-1.414.586L6.293 4.707A1 1 0 015.586 5H4zm6 9a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                </svg>
                <span className="whitespace-nowrap">добавить файл</span>
              </button>
            </div>
          </div>
        </div>
        )}
        
        {currentChat && selectedTab === 'chat' && (
        <form 
          onSubmit={(e) => {
            e.preventDefault();
            const textarea = document.querySelector('textarea[data-component-name="ChatInput"]') as HTMLTextAreaElement;
            const hasUploadingPhotos = uploadedPhotos.some(p => p.uploading);
            const hasUploadingDocuments = uploadedDocuments.some(d => d.uploading);
            if (textarea && (textarea.value.trim() || uploadedPhotos.length > 0 || uploadedDocuments.length > 0) && !isLoading && !hasUploadingPhotos && !hasUploadingDocuments) {
              console.log('Sending message:', textarea.value, 'with photos:', uploadedPhotos.length, 'with documents:', uploadedDocuments.length);
              // Отправляем сообщение с файлами на сервер
              handleSendMessage(textarea.value);
              textarea.value = '';
              // Сбрасываем высоту после отправки
              textarea.style.height = 'auto';
              // Очищаем все файлы после отправки
              handleClearAllFiles();
            }
          }} 
          className="fixed bottom-2 sm:bottom-10 left-0 right-0 flex justify-center px-2 sm:px-4 transition-all duration-300 ease-in-out z-20"
          style={{ left: sidebarVisible && window.innerWidth >= 640 ? '16rem' : '0' }}
          data-component-name="ChatPage"
        >
          <div 
            className="flex flex-col rounded-lg sm:rounded-xl border border-dark-border overflow-hidden shadow-md bg-dark-accent/90 hover:bg-dark-accent transition-all duration-300 w-full max-w-[48rem] focus-within:bg-dark-accent relative"
          >
            {/* Превью загруженных фото и документов */}
            {(uploadedPhotos.length > 0 || uploadedDocuments.length > 0) && (
              <div className="px-3 sm:px-5 pt-2 pb-2 border-b border-dark-border/30">
                <div className="flex flex-wrap gap-2">
                  {/* Превью фото */}
                  {uploadedPhotos.map((photo, index) => (
                    <div key={`photo-${index}`} className="relative inline-block">
                      <img 
                        src={photo.previewUrl} 
                        alt={`Preview ${index + 1}`} 
                        className="w-12 h-12 object-cover rounded-md border border-dark-border/50"
                      />
                      
                      {/* Индикатор загрузки */}
                      {photo.uploading && (
                        <div className="absolute inset-0 bg-black/50 rounded-md flex items-center justify-center">
                          <div className="w-5 h-5 border-2 border-custom-blue border-t-transparent rounded-full animate-spin"></div>
                        </div>
                      )}
                      
                      {/* Кнопка удаления */}
                      {!photo.uploading && (
                        <button
                          type="button"
                          onClick={() => handleRemovePhoto(index)}
                          className="absolute -top-1 -right-1 w-4 h-4 bg-dark-secondary/90 hover:bg-dark-accent text-gray-400 hover:text-white rounded-full flex items-center justify-center transition-colors border border-dark-border/50"
                          title="Удалить фото"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-2.5 w-2.5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}
                  
                  {/* Превью документов */}
                  {uploadedDocuments.map((doc, index) => {
                    const fileInfo = getFileInfo(doc.filename);
                    return (
                      <div key={`doc-${index}`} className="relative inline-block">
                        <div className="w-12 h-12 rounded-md border border-dark-border/50 bg-dark-secondary/50 flex items-center justify-center">
                          {renderFileIcon(fileInfo.iconName, `h-6 w-6 ${fileInfo.color}`)}
                        </div>
                        
                        {/* Индикатор загрузки */}
                        {doc.uploading && (
                          <div className="absolute inset-0 bg-black/50 rounded-md flex items-center justify-center">
                            <div className="w-5 h-5 border-2 border-custom-blue border-t-transparent rounded-full animate-spin"></div>
                          </div>
                        )}
                        
                        {/* Кнопка удаления */}
                        {!doc.uploading && (
                          <button
                            type="button"
                            onClick={() => handleRemoveDocument(index)}
                            className="absolute -top-1 -right-1 w-4 h-4 bg-dark-secondary/90 hover:bg-dark-accent text-gray-400 hover:text-white rounded-full flex items-center justify-center transition-colors border border-dark-border/50"
                            title={`Удалить ${doc.filename}`}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-2.5 w-2.5" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div className="flex items-center">
              <textarea
              ref={textareaRef}
              placeholder="Введите сообщение..."
              disabled={isLoading || isProcessingSpeech}
              className="flex-1 px-3 sm:px-5 py-2 sm:py-[0.875rem] bg-transparent text-sm sm:text-base text-dark-text focus:outline-none disabled:opacity-50 resize-none min-h-[2.5rem] sm:min-h-[2.75rem] max-h-32 hide-scrollbar bg-dark-accent/90"
              style={{ 
                scrollbarWidth: 'none', 
                msOverflowStyle: 'none', 
                WebkitAppearance: 'none',
                transition: 'height 150ms ease-in-out, background-color 150ms ease-in-out'
              }}

              data-component-name="ChatInput"
              rows={1}
              onInput={(e) => {
                const textarea = e.target as HTMLTextAreaElement;
                
                // Если текст превышает максимальную высоту, включаем скролл
                // Сначала скрываем оверфлоу, чтобы избежать мерцания
                textarea.style.overflow = 'hidden';
                
                if (textarea.scrollHeight > 128) {
                  // Фиксируем максимальную высоту
                  textarea.style.height = '128px';
                  // Добавляем небольшую задержку перед включением скролла
                  setTimeout(() => {
                    textarea.style.overflow = 'auto';
                    textarea.classList.add('hide-scrollbar');
                  }, 50);
                } else {
                  textarea.style.height = 'auto';
                  textarea.style.height = `${textarea.scrollHeight}px`;
                }
                
                // Обновляем позицию кнопок с небольшой задержкой, чтобы DOM успел обновиться
                setTimeout(() => {
                  const filePreview = document.querySelector('.px-3.pt-2.pb-2.border-b, .px-5.pt-2.pb-2.border-b') as HTMLElement;
                  const buttonsContainer = document.querySelector('div[data-component-name="ChatPage"]') as HTMLElement;
                  
                  if (textarea && buttonsContainer) {
                    const textareaExtraHeight = Math.max(0, textarea.clientHeight - 44);
                    const fileHeight = filePreview ? filePreview.clientHeight : 0;
                    const totalExtraHeight = textareaExtraHeight + fileHeight;
                    const sidebarOffset = sidebarVisible && window.innerWidth >= 640 ? '16rem' : '0';
                    const bottomOffset = window.innerWidth < 640 ? '4rem' : '6rem';
                    
                    buttonsContainer.style.left = sidebarOffset;
                    buttonsContainer.style.bottom = `calc(${bottomOffset} + ${totalExtraHeight}px)`;
                  }
                }, 10);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  const textarea = e.target as HTMLTextAreaElement;
                  const hasUploadingPhotos = uploadedPhotos.some(p => p.uploading);
                  const hasUploadingDocuments = uploadedDocuments.some(d => d.uploading);
                  if ((textarea.value.trim() || uploadedPhotos.length > 0 || uploadedDocuments.length > 0) && !isLoading && !hasUploadingPhotos && !hasUploadingDocuments) {
                    console.log('Sending message via Enter key:', textarea.value, 'with photos:', uploadedPhotos.length, 'with documents:', uploadedDocuments.length);
                    // Отправляем сообщение с файлами на сервер
                    handleSendMessage(textarea.value);
                    textarea.value = '';
                    // Сбрасываем высоту после отправки
                    textarea.style.height = 'auto';
                    // Очищаем все файлы после отправки
                    handleClearAllFiles();
                  }
                }
              }}
            />
            <button
              type="button"
              onClick={handleMicrophoneClick}
              disabled={isLoading || isProcessingSpeech || uploadedPhotos.some(p => p.uploading) || uploadedDocuments.some(d => d.uploading)}
              className={`h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center text-dark-text bg-dark-accent/90 hover:bg-dark-accent focus:outline-none focus:ring-1 focus:ring-custom-blue disabled:opacity-50 rounded-lg sm:rounded-xl transition-all duration-300 relative z-10 ${
                isRecording ? 'animate-pulse bg-custom-blue/20' : ''
              }`}
              title={isRecording ? 'Остановить запись' : 'Начать голосовой ввод'}
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                className={`h-[15px] w-[15px] sm:h-[18px] sm:w-[18px] transition-all duration-300 ${isRecording ? 'text-red-500 scale-110' : 'text-white'}`} 
                viewBox="0 0 20 20" 
                fill="currentColor"
              >
                {isRecording ? (
                  <path fillRule="evenodd" d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4zm4 10.93A7.001 7.001 0 0017 8a1 1 0 10-2 0A5 5 0 015 8a1 1 0 00-2 0 7.001 7.001 0 006 6.93V17H6a1 1 0 100 2h8a1 1 0 100-2h-3v-2.07z" clipRule="evenodd" />
                ) : (
                  <>
                    <path d="M7 4a3 3 0 016 0v4a3 3 0 11-6 0V4z" />
                    <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5H10.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
                  </>
                )}
              </svg>
            </button>
            <button
              type="submit"
              disabled={isLoading || isProcessingSpeech || uploadedPhotos.some(p => p.uploading) || uploadedDocuments.some(d => d.uploading)}
              className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center text-dark-text bg-dark-accent/90 hover:bg-dark-accent focus:outline-none focus:ring-2 focus:ring-custom-blue disabled:opacity-50 rounded-lg sm:rounded-xl mr-1 transition-all duration-300"
              title="Отправить сообщение"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 sm:h-5 sm:w-5" viewBox="0 0 20 20" fill="currentColor" data-component-name="ChatPage">
                <path fillRule="evenodd" d="M10.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L12.586 11H5a1 1 0 110-2h7.586l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" data-component-name="ChatPage" />
              </svg>
            </button>
            </div>
          </div>
        </form>
        )}
      </div>
    </div>
  );
};

export default ChatPage;
