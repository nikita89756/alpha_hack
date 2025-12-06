import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '../types';
import { chatService } from '../services/api';
import { renderFileIcon, getFileInfo } from '../utils/fileUtils';

interface ChatMessagesProps {
  messages: Message[];
  isLoading?: boolean;
  isTyping?: boolean;
  getFullImageUrl?: (message: Message) => string;
  onSendMessage?: (message: string) => void;
  onCreateNewChat?: () => void;
  hideInput?: boolean;
  hasActiveChat?: boolean;
  chatId?: string;
}

const defaultGetFullImageUrl = (message: Message): string => {
  // Сначала проверяем, есть ли серверный URL
  if (message.serverImageUrl) {
    const imageUrl = message.serverImageUrl;
    
    // Если это blob URL, возвращаем как есть
    if (imageUrl.startsWith('blob:')) {
      return imageUrl;
    }
    
    // Если это относительный путь /storage/..., возвращаем как есть
    if (imageUrl.startsWith('/storage')) {
      return imageUrl;
    }
    
    // Заменяем http://minio:9000 или http://localhost:9000 на /storage
    if (imageUrl.startsWith('http://minio:9000/') || imageUrl.startsWith('http://localhost:9000/')) {
      return imageUrl.replace('http://minio:9000/', '/storage/').replace('http://localhost:9000/', '/storage/');
    }
    
    return imageUrl;
  }
  
  // Если нет серверного URL, используем обычный imageUrl
  const imageUrl = message.imageUrl;
  if (!imageUrl) return '';
  
  // Если URL является blob URL, возвращаем его как есть
  if (imageUrl.startsWith('blob:')) {
    return imageUrl;
  }
  
  // Если это относительный путь /storage/..., возвращаем как есть
  if (imageUrl.startsWith('/storage')) {
    return imageUrl;
  }
  
  // Заменяем http://minio:9000 или http://localhost:9000 на /storage
  if (imageUrl.startsWith('http://minio:9000/') || imageUrl.startsWith('http://localhost:9000/')) {
    return imageUrl.replace('http://minio:9000/', '/storage/').replace('http://localhost:9000/', '/storage/');
  }
  
  // Если это полный URL с http, возвращаем как есть
  if (imageUrl.startsWith('http')) {
    return imageUrl;
  }
  
  // Иначе это относительный путь, возвращаем как есть
  return imageUrl;
};

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, isLoading = false, isTyping = false, getFullImageUrl = defaultGetFullImageUrl, onSendMessage, onCreateNewChat, hasActiveChat = false, chatId }) => {
  const messagesEndRef = React.createRef<HTMLDivElement>();
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null);
  const [aiSuggestionsVisible, setAiSuggestionsVisible] = useState<number | null>(null);
  const [aiSuggestionsLoading, setAiSuggestionsLoading] = useState<number | null>(null);
  const [aiSuggestions, setAiSuggestions] = useState<{[key: number]: {answer: string, actions: string[]}}>({});
  const [aiSuggestionsTab, setAiSuggestionsTab] = useState<{[key: number]: 'answer' | 'actions'}>({});
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string>('');
  const [exportMenuOpen, setExportMenuOpen] = useState<number | null>(null);

  // Автоматическая прокрутка вниз при добавлении новых сообщений
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, messagesEndRef]);

  // Добавляем логирование при изменении сообщений
  useEffect(() => {
    console.log('ChatMessages - messages updated:', JSON.stringify(messages));
    // Добавляем подробное логирование каждого сообщения
    messages.forEach((msg, index) => {
      console.log(`Message ${index}:`, {
        role: msg.role,
        content: msg.content || 'ПУСТОЕ СОДЕРЖИМОЕ',
        timestamp: msg.timestamp,
        imageUrl: msg.imageUrl || 'НЕТ ИЗОБРАЖЕНИЯ'
      });
      
      // Проверяем URL изображения
      if (msg.imageUrl) {
        console.log(`Image URL for message ${index}:`, msg.imageUrl);
        // Проверяем, что URL изображения содержит базовый URL
        if (!msg.imageUrl.startsWith('http')) {
          console.log(`Image URL does not start with http, full URL should be: http://localhost:8080${msg.imageUrl.startsWith('/') ? '' : '/'}${msg.imageUrl}`);
        }
      }
    });
  }, [messages]);

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) {
      console.log('Invalid timestamp:', timestamp);
      return '';
    }
    
    try {
      const date = new Date(timestamp);
      // Проверка на валидность даты
      if (isNaN(date.getTime())) {
        console.log('Invalid timestamp value:', timestamp);
        return '';
      }
      
      return new Intl.DateTimeFormat('ru-RU', {
        hour: '2-digit',
        minute: '2-digit',
      }).format(date);
    } catch (error) {
      console.error('Error formatting timestamp:', error, timestamp);
      return '';
    }
  };

  // Функция для проверки валидности сообщения
  const isValidMessage = (message: any): message is Message => {
    return (
      message &&
      typeof message === 'object' &&
      typeof message.role === 'string' &&
      ['user', 'assistant'].includes(message.role) &&
      (message.content === undefined || message.content === null || typeof message.content === 'string') &&
      (message.imageUrl === undefined || message.imageUrl === null || typeof message.imageUrl === 'string')
    );
  };

  // Используем переданную функцию getFullImageUrl

  // Функция для получения содержимого сообщения
  const getMessageContent = (message: Message) => {
    if (message.content && message.content.trim() !== '') {
      return message.content;
    }
    return 'Пустое сообщение';
  };

  // Функция для определения, содержит ли сообщение результаты парсинга Wildberries
  const isWildberriesParsingResult = (content: string): boolean => {
    // Проверяем наличие заголовка с или без эмодзи
    return content.includes('## Найденные товары на Wildberries') || 
           content.includes('## 🛍️ Найденные товары на Wildberries') || 
           // Проверяем наличие подзаголовков с или без эмодзи
           content.includes('### ') || 
           content.includes('### 🔍') || 
           // Проверяем наличие сообщений об ошибках с или без эмодзи
           content.includes('Не удалось найти похожие товары') || 
           content.includes('### ❌ Не удалось найти похожие товары');
  };

  // Функция для копирования текста в буфер обмена
  const copyMessageToClipboard = async (text: string, groupIndex: number) => {
    try {
      // Пробуем использовать современный Clipboard API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        setCopiedMessageIndex(groupIndex);
        setTimeout(() => {
          setCopiedMessageIndex(null);
        }, 2000);
      } else {
        // Fallback для старых браузеров
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
          const successful = document.execCommand('copy');
          if (successful) {
            setCopiedMessageIndex(groupIndex);
            setTimeout(() => {
              setCopiedMessageIndex(null);
            }, 2000);
          } else {
            console.error('Не удалось скопировать текст через execCommand');
          }
        } catch (err) {
          console.error('Ошибка при копировании через execCommand:', err);
        } finally {
          document.body.removeChild(textArea);
        }
      }
    } catch (err) {
      console.error('Не удалось скопировать текст:', err);
    }
  };

  // Функция для получения AI подсказок
  const getAiSuggestions = async (message: Message, groupIndex: number) => {
    // Если подсказки уже видны, скрываем их
    if (aiSuggestionsVisible === groupIndex) {
      setAiSuggestionsVisible(null);
      return;
    }

    // Проверяем наличие ID сообщения
    if (!message.id) {
      console.error('Message ID is missing, cannot get AI hints');
      // Показываем заглушку если ID отсутствует
      setAiSuggestions(prev => ({
        ...prev,
        [groupIndex]: { answer: 'Не удалось получить подсказки: отсутствует ID сообщения', actions: [] }
      }));
      setAiSuggestionsTab(prev => ({
        ...prev,
        [groupIndex]: 'answer'
      }));
      setAiSuggestionsVisible(groupIndex);
      return;
    }

    // Показываем загрузку
    setAiSuggestionsLoading(groupIndex);
    setAiSuggestionsVisible(groupIndex);

    try {
      // Реальный запрос к ML API через бэкенд
      const response = await chatService.getAiHints(message.id);
      
      console.log('AI hints received:', response);
      
      // Извлекаем подсказки из ответа, разделяя на "Вариант ответа" и "Действия"
      let answerText = '';
      const actions: string[] = [];
      
      // Если есть шаблон ответа - используем его
      if (response.hints?.response_template) {
        answerText = response.hints.response_template;
      }
      // Иначе, если есть relevant_docs, берем самый релевантный
      else if (response.relevant_docs && Array.isArray(response.relevant_docs) && response.relevant_docs.length > 0) {
        const mostRelevant = response.relevant_docs[0];
        if (mostRelevant.payload?.knowledge) {
          answerText = mostRelevant.payload.knowledge;
        }
      }
      
      // Добавляем предложенные действия если есть
      if (response.hints?.suggested_actions && Array.isArray(response.hints.suggested_actions)) {
        response.hints.suggested_actions.forEach((action: any) => {
          if (typeof action === 'string') {
            actions.push(action);
          } else if (action.description) {
            actions.push(action.description);
          }
        });
      }
      
      // Если нет подсказок, показываем сообщение
      if (!answerText && actions.length === 0) {
        answerText = 'AI не смог сгенерировать подсказки для этого сообщения.';
      }
      
      setAiSuggestions(prev => ({
        ...prev,
        [groupIndex]: { answer: answerText, actions }
      }));
      
      // Устанавливаем начальную вкладку (ответ, если есть, иначе действия)
      setAiSuggestionsTab(prev => ({
        ...prev,
        [groupIndex]: answerText ? 'answer' : 'actions'
      }));
      
      setAiSuggestionsLoading(null);
    } catch (error: any) {
      console.error('Error getting AI hints:', error);
      
      let errorMessage = 'Ошибка при получении подсказок.';
      if (error.code === 'ECONNABORTED') {
        errorMessage = 'Превышено время ожидания. ML сервис перегружен, попробуйте позже.';
      }
      
      // Показываем ошибку пользователю
      setAiSuggestions(prev => ({
        ...prev,
        [groupIndex]: { answer: errorMessage, actions: [] }
      }));
      setAiSuggestionsTab(prev => ({
        ...prev,
        [groupIndex]: 'answer'
      }));
      setAiSuggestionsLoading(null);
    }
  };

  return (
    <div 
      className={`flex-1 bg-dark-primary ${messages.length === 0 ? 'flex items-center justify-center' : 'overflow-y-auto custom-scrollbar'}`}
      data-component-name="ChatMessages"
    >
      {messages.length === 0 ? (
        hasActiveChat ? (
          <div className="w-full flex justify-center items-center px-3 sm:px-4">
            <div className="max-w-2xl w-full text-center space-y-2 sm:space-y-3">
              <h2 className="text-xl sm:text-2xl font-semibold text-white">Начните диалог</h2>
              <p className="text-dark-text/70 text-sm sm:text-base max-w-md mx-auto">
                Опишите ваш вопрос или проблему
              </p>
            </div>
          </div>
        ) : (
        <div className="max-w-3xl w-full text-center space-y-6 sm:space-y-8 px-3 sm:px-4">
            {/* Иконка */}
            <div className="flex justify-center">
              <img src="/wwh5l7ed.png" alt="Logo" className="w-16 h-16 sm:w-20 sm:h-20 object-contain rounded-2xl" />
            </div>
            
            {/* Заголовок */}
            <div className="space-y-2 sm:space-y-3">
              <h2 className="text-2xl sm:text-3xl font-bold text-white">Помощник по микробизнесу</h2>
              <p className="text-dark-text/70 text-base sm:text-lg max-w-md mx-auto leading-relaxed">
                Здравствуйте! Я ваш ИИ-ассистент, готовый помочь в развитии вашего микробизнеса.
            </p>
          </div>
            
            {/* Описание возможностей */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 max-w-3xl mx-auto text-left">
              <div className="bg-dark-secondary/50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-dark-border/30">
                <div className="text-custom-blue mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 sm:h-6 sm:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="text-white font-medium mb-1 text-sm sm:text-base">Быстрые ответы</h3>
                <p className="text-xs sm:text-sm text-dark-text/60">Получите мгновенный ответ на ваш вопрос</p>
              </div>
              
              <div className="bg-dark-secondary/50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-dark-border/30">
                <div className="text-custom-blue mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 sm:h-6 sm:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <h3 className="text-white font-medium mb-1 text-sm sm:text-base">Умная помощь</h3>
                <p className="text-xs sm:text-sm text-dark-text/60">ИИ понимает контекст и помогает решить проблему</p>
              </div>
              
              <div className="bg-dark-secondary/50 p-3 sm:p-4 rounded-lg sm:rounded-xl border border-dark-border/30">
                <div className="text-custom-blue mb-2">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 sm:h-6 sm:w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-white font-medium mb-1 text-sm sm:text-base">24/7</h3>
                <p className="text-xs sm:text-sm text-dark-text/60">Мы всегда на связи в любое время</p>
              </div>
            </div>
            
            {/* Кнопка создания чата */}
            <div className="pt-2 sm:pt-4">
              <button
                onClick={onCreateNewChat}
                className="px-6 sm:px-8 py-2.5 sm:py-3 bg-custom-blue hover:bg-custom-blue/90 text-dark-primary font-semibold rounded-lg sm:rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 text-sm sm:text-base"
              >
                Начать новый чат
              </button>
            </div>
        </div>
        )
      ) : (
        // Группируем сообщения по параметру (пользователь + ассистент)
        (() => {
          // Фильтруем невалидные сообщения
          const validMessages = messages.filter(message => isValidMessage(message));
          const messageGroups = [];
          
          // Отображаем сообщения в правильном порядке: пользователь -> ассистент
          // ВАЖНО: сообщения пользователя имеют role: 'assistant' и message_type: 'user'
          // Сообщения бота имеют role: 'user' и message_type: 'bot'
          for (let i = 0; i < validMessages.length; i++) {
            const currentMessage = validMessages[i];
            const nextMessage = validMessages[i + 1];
            
            // Сообщение пользователя (role: 'assistant' или role: 'user' с message_type: 'user')
            if (currentMessage.role === 'assistant' || (currentMessage.role === 'user' && currentMessage.message_type === 'user')) {
              // Проверяем есть ли ответ бота (role: 'user' с message_type: 'bot')
              if (nextMessage && nextMessage.role === 'user' && nextMessage.message_type === 'bot') {
                messageGroups.push({ userMessage: currentMessage, assistantMessage: nextMessage });
                i++; // Пропускаем следующее сообщение бота
              } else {
                messageGroups.push({ userMessage: currentMessage, assistantMessage: null });
              }
            } else if (currentMessage.role === 'user' && currentMessage.message_type === 'bot') {
              // Сообщение от бота без предшествующего сообщения пользователя
              messageGroups.push({ userMessage: null, assistantMessage: currentMessage });
            }
          }
          
          return (
            <div className="px-2 sm:px-4 py-4 sm:py-6 space-y-3 sm:space-y-4">
              {messageGroups.map((group, groupIndex) => (
                <div 
                  key={groupIndex} 
                  className="space-y-2 sm:space-y-3"
                >
                  {group.userMessage && (
                    <div className="flex justify-end">
                        <div className="max-w-[85%] sm:max-w-xs lg:max-w-md xl:max-w-lg">
                        <div className="text-[10px] sm:text-xs text-dark-text/50 mb-1 text-right px-1">
                          Клиент (Вы)
                        </div>
                         <div className="bg-custom-blue/20 text-white rounded-xl sm:rounded-2xl rounded-br-md px-3 sm:px-4 py-2 shadow-lg border border-custom-blue/30">
                          {/* Показываем текст сверху, если есть контент */}
                          {(() => {
                            const hasContent = group.userMessage.content && group.userMessage.content.trim() !== '';
                            console.log('Rendering user message:', {
                              hasContent,
                              content: group.userMessage.content,
                              contentLength: group.userMessage.content?.length,
                              imageUrl: group.userMessage.imageUrl
                            });
                            return hasContent ? (
                            <div className="text-sm leading-relaxed mb-2 prose prose-invert prose-sm max-w-none dark:prose-invert">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-white">{children}</h1>,
                                  h2: ({ children }) => <h2 className="text-base font-bold mb-2 text-white">{children}</h2>,
                                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1 text-white">{children}</h3>,
                                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                                  li: ({ children }) => <li className="ml-2">{children}</li>,
                                  code: ({ children, className }) => {
                                    const isInline = !className;
                                    return isInline ? (
                                      <code className="bg-dark-primary/50 px-1 py-0.5 rounded text-xs font-mono text-custom-blue break-words">{children}</code>
                                    ) : (
                                      <code className="block bg-dark-primary/50 p-2 rounded text-xs font-mono text-custom-blue overflow-x-auto mb-2 whitespace-pre-wrap break-words">{children}</code>
                                    );
                                  },
                                  pre: ({ children }) => <pre className="mb-2 overflow-x-auto">{children}</pre>,
                                  blockquote: ({ children }) => <blockquote className="border-l-4 border-custom-blue/50 pl-3 italic my-2 text-dark-text/80">{children}</blockquote>,
                                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                  em: ({ children }) => <em className="italic">{children}</em>,
                                  a: ({ children, href }) => <a href={href} className="text-custom-blue hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                                  table: ({ children }) => <div className="overflow-x-auto mb-2"><table className="min-w-full border border-dark-border/50">{children}</table></div>,
                                  thead: ({ children }) => <thead className="bg-dark-primary/50">{children}</thead>,
                                  tbody: ({ children }) => <tbody>{children}</tbody>,
                                  tr: ({ children }) => <tr className="border-b border-dark-border/30">{children}</tr>,
                                  th: ({ children }) => <th className="px-3 py-2 text-left text-xs font-semibold text-white border border-dark-border/30">{children}</th>,
                                  td: ({ children }) => <td className="px-3 py-2 text-sm border border-dark-border/30">{children}</td>
                                }}
                              >
                                {getMessageContent(group.userMessage)}
                              </ReactMarkdown>
                            </div>
                            ) : null;
                          })()}
                          {/* Показываем изображение или файл в зависимости от imageUrl */}
                          {group.userMessage.imageUrl && (() => {
                            const imageUrl = group.userMessage.imageUrl || '';
                            // Проверяем, это URL (фото) или имя файла (документ)
                            const isImageUrl = imageUrl.startsWith('/storage/') || 
                                             imageUrl.startsWith('http://') || 
                                             imageUrl.startsWith('https://') ||
                                             imageUrl.startsWith('blob:');
                            
                            if (isImageUrl) {
                              // Это фото - показываем изображение
                              return (
                            <div className="mt-2">
                              <img 
                                src={getFullImageUrl(group.userMessage)} 
                                alt="Uploaded by user" 
                                className="max-w-full h-auto rounded-xl max-h-60 object-cover cursor-pointer hover:opacity-80 transition-opacity"
                                onClick={() => {
                                  setSelectedImage(getFullImageUrl(group.userMessage));
                                  setImageModalOpen(true);
                                }}
                                onError={(e) => {
                                  const url = getFullImageUrl(group.userMessage);
                                  console.error('Error loading image:', {
                                    originalUrl: group.userMessage.imageUrl,
                                    serverUrl: group.userMessage.serverImageUrl,
                                    fullUrl: url,
                                    element: e.currentTarget
                                  });
                                  
                                  if (url.startsWith('blob:')) {
                                    console.log('Not retrying for blob URL');
                                    e.currentTarget.onerror = null;
                                    e.currentTarget.style.display = 'none';
                                    return;
                                  }
                                  
                                  if (url.includes('/api/images/')) {
                                    const imageId = url.split('/api/images/')[1];
                                    console.log('Trying alternative URL format with image ID:', imageId);
                                    e.currentTarget.src = `http://localhost:8080/api/images/${imageId}`;
                                    return;
                                  }
                                  e.currentTarget.onerror = null;
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                                </div>
                              );
                            } else {
                              // Это файл - показываем иконку с названием
                              const fileName = imageUrl; // imageUrl содержит имя файла
                              const fileInfo = getFileInfo(fileName);
                              return (
                                <div className="mt-2 flex items-center gap-2 py-1">
                                  <div className="w-10 h-10 rounded-lg border border-dark-border/50 bg-dark-secondary/50 flex items-center justify-center flex-shrink-0">
                                    {renderFileIcon(fileInfo.iconName, `h-5 w-5 ${fileInfo.color}`)}
                                  </div>
                                  <div className="flex-1">
                                    <div className="text-sm font-medium text-dark-text">{fileName}</div>
                                  </div>
                                </div>
                              );
                            }
                          })()}
                        </div>
                         <div className="text-xs text-white/70 mt-1 text-right px-1">
                           {formatTimestamp(group.userMessage.timestamp)}
                         </div>
                      </div>
                    </div>
                  )}
              
                  {group.assistantMessage && (
                    <div className="flex justify-start">
                      <div className="flex items-start space-x-2 max-w-[85%] sm:max-w-xs lg:max-w-md xl:max-w-lg">
                         <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-dark-accent flex items-center justify-center flex-shrink-0 border border-dark-border/50">
                           <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                             <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                           </svg>
                         </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-[10px] sm:text-xs text-dark-text/50 mb-1 px-1">
                              Ассистент
                          </div>
                         <div className="bg-dark-secondary/80 backdrop-blur-sm text-dark-text rounded-xl sm:rounded-2xl rounded-tl-md px-3 sm:px-4 py-2 shadow-lg border border-dark-border/50">
                          {/* Показываем текст сверху, если есть контент (кроме случаев когда только файл без текста) */}
                          {group.assistantMessage.content?.trim() && !group.assistantMessage.imageUrl && (
                            <div className="text-sm leading-relaxed mb-2 prose prose-invert prose-sm max-w-none dark:prose-invert">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-white">{children}</h1>,
                                  h2: ({ children }) => <h2 className="text-base font-bold mb-2 text-white">{children}</h2>,
                                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1 text-white">{children}</h3>,
                                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                                  li: ({ children }) => <li className="ml-2">{children}</li>,
                                  code: ({ children, className }) => {
                                    const isInline = !className;
                                    return isInline ? (
                                      <code className="bg-dark-primary/50 px-1 py-0.5 rounded text-xs font-mono text-custom-blue break-words">{children}</code>
                                    ) : (
                                      <code className="block bg-dark-primary/50 p-2 rounded text-xs font-mono text-custom-blue overflow-x-auto mb-2 whitespace-pre-wrap break-words">{children}</code>
                                    );
                                  },
                                  pre: ({ children }) => <pre className="mb-2 overflow-x-auto">{children}</pre>,
                                  blockquote: ({ children }) => <blockquote className="border-l-4 border-custom-blue/50 pl-3 italic my-2 text-dark-text/80">{children}</blockquote>,
                                  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                  em: ({ children }) => <em className="italic">{children}</em>,
                                  a: ({ children, href }) => <a href={href} className="text-custom-blue hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                                  table: ({ children }) => <div className="overflow-x-auto mb-2"><table className="min-w-full border border-dark-border/50">{children}</table></div>,
                                  thead: ({ children }) => <thead className="bg-dark-primary/50">{children}</thead>,
                                  tbody: ({ children }) => <tbody>{children}</tbody>,
                                  tr: ({ children }) => <tr className="border-b border-dark-border/30">{children}</tr>,
                                  th: ({ children }) => <th className="px-3 py-2 text-left text-xs font-semibold text-white border border-dark-border/30">{children}</th>,
                                  td: ({ children }) => <td className="px-3 py-2 text-sm border border-dark-border/30">{children}</td>
                                }}
                              >
                                {getMessageContent(group.assistantMessage)}
                              </ReactMarkdown>
                            </div>
                          )}
                          {/* Показываем иконку файла снизу, если есть fileName */}
                          {group.assistantMessage.fileName && (
                            <div className="flex items-center gap-2 py-1">
                              <div className="w-10 h-10 rounded-lg border border-custom-blue/30 bg-custom-blue/10 flex items-center justify-center flex-shrink-0">
                                {renderFileIcon(group.assistantMessage.fileType || getFileInfo(group.assistantMessage.fileName).iconName, `h-5 w-5 ${getFileInfo(group.assistantMessage.fileName).color}`)}
                              </div>
                              <div className="flex-1">
                                <div className="text-sm font-medium text-white">{group.assistantMessage.fileName}</div>
                              </div>
                            </div>
                          )}
                          {/* Показываем изображение если есть imageUrl */}
                          {group.assistantMessage.imageUrl && (
                            <div className="mt-2">
                              <img 
                                src={getFullImageUrl(group.assistantMessage)} 
                                alt="Assistant response" 
                                className="max-w-full h-auto rounded-xl max-h-60 object-cover cursor-pointer hover:opacity-80 transition-opacity"
                                onClick={() => {
                                  setSelectedImage(getFullImageUrl(group.assistantMessage));
                                  setImageModalOpen(true);
                                }}
                                onError={(e) => {
                                  const url = getFullImageUrl(group.assistantMessage);
                                  console.error('Error loading image:', {
                                    originalUrl: group.assistantMessage.imageUrl,
                                    serverUrl: group.assistantMessage.serverImageUrl,
                                    fullUrl: url,
                                    element: e.currentTarget
                                  });
                                  
                                  if (url.startsWith('blob:')) {
                                    console.log('Not retrying for blob URL');
                                    e.currentTarget.onerror = null;
                                    e.currentTarget.style.display = 'none';
                                    return;
                                  }
                                  
                                  if (url.includes('/api/images/')) {
                                    const imageId = url.split('/api/images/')[1];
                                    console.log('Trying alternative URL format with image ID:', imageId);
                                    e.currentTarget.src = `http://localhost:8080/api/images/${imageId}`;
                                    return;
                                  }
                                  
                                  e.currentTarget.onerror = null;
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                            </div>
                          )}
                          <div className="flex justify-between items-center gap-3 mt-1">
                            <div className="flex items-center gap-3">
                              {group.assistantMessage.id && (
                                <>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setExportMenuOpen(exportMenuOpen === groupIndex ? null : groupIndex);
                                    }}
                                    className="opacity-70 hover:opacity-100 transition-opacity duration-200 text-xs text-custom-blue hover:text-custom-blue/80 relative"
                                    title="Экспорт"
                                  >
                                    Экспорт
                                  </button>
                                    

                                  {/* Выпадающее меню экспорта */}
                                  {exportMenuOpen === groupIndex && (
                                    <>
                                      <div 
                                        className="fixed inset-0 z-40" 
                                        onClick={() => setExportMenuOpen(null)}
                                      />
                                      <div 
                                        className="absolute left-0 top-full mt-2 w-48 bg-dark-secondary border border-dark-border/50 rounded-lg shadow-lg z-50 overflow-hidden"
                                        onClick={(e) => e.stopPropagation()}
                                      >
                                        <button
                                          onClick={async (e) => {
                                            e.stopPropagation();
                                            
                                            if (!group.assistantMessage.id) {
                                              console.error('Message ID is missing, cannot export');
                                              setExportMenuOpen(null);
                                              return;
                                            }
                                            
                                            try {
                                              const blob = await chatService.exportMessage(group.assistantMessage.id, 'pdf');
                                              const url = window.URL.createObjectURL(blob);
                                              const a = document.createElement('a');
                                              a.href = url;
                                              a.download = `message_${group.assistantMessage.id}_${new Date().toISOString().split('T')[0]}.pdf`;
                                              document.body.appendChild(a);
                                              a.click();
                                              document.body.removeChild(a);
                                              window.URL.revokeObjectURL(url);
                                              setExportMenuOpen(null);
                                            } catch (error) {
                                              console.error('Error exporting message:', error);
                                              setExportMenuOpen(null);
                                            }
                                          }}
                                          className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center gap-2"
                                        >
                                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                          </svg>
                                          <span>Экспорт сообщения</span>
                                        </button>
                                        
                                        <button
                                          onClick={async (e) => {
                                            e.stopPropagation();
                                            
                                            if (!chatId) {
                                              console.error('Chat ID is missing, cannot export');
                                              setExportMenuOpen(null);
                                              return;
                                            }
                                            
                                            try {
                                              const blob = await chatService.exportChat(chatId, 'pdf');
                                              const url = window.URL.createObjectURL(blob);
                                              const a = document.createElement('a');
                                              a.href = url;
                                              a.download = `chat_${chatId}_${new Date().toISOString().split('T')[0]}.pdf`;
                                              document.body.appendChild(a);
                                              a.click();
                                              document.body.removeChild(a);
                                              window.URL.revokeObjectURL(url);
                                              setExportMenuOpen(null);
                                            } catch (error) {
                                              console.error('Error exporting chat:', error);
                                              setExportMenuOpen(null);
                                            }
                                          }}
                                          className="w-full px-4 py-2.5 text-left text-sm text-dark-text hover:bg-dark-accent/50 transition-colors flex items-center gap-2 border-t border-dark-border/30"
                                        >
                                          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                          </svg>
                                          <span>Экспорт чата</span>
                                        </button>
                                      </div>
                                    </>
                                  )}
                                </>
                              )}
                              <button 
                                onClick={() => copyMessageToClipboard(getMessageContent(group.assistantMessage), groupIndex)}
                                className="opacity-70 hover:opacity-100 transition-opacity duration-200 text-xs text-dark-text/70 hover:text-dark-text"
                                title="Скопировать текст"
                              >
                                {copiedMessageIndex === groupIndex ? (
                                  <span className="text-custom-blue">✓ Скопировано</span>
                                ) : (
                                  'Копировать'
                                )}
                              </button>
                            </div>
                            {group.assistantMessage.source && (() => {
                              const sourceValue = group.assistantMessage.source;
                              if (!sourceValue) return null;
                              
                              const source = String(sourceValue).toLowerCase().trim();
                              let sourceText = '';
                              
                              if (source === 'llm-only' || source === 'llm_only') {
                                sourceText = 'Сгенерированная ИИ*';
                              } else if (source === 'rag' || source === 'kb') {
                                sourceText = 'Информация взята из базы знаний*';
                              } else if (source === 'web-search' || source === 'web_search') {
                                sourceText = 'Информация взята из интернета*';
                              } else if (source === 'ltm') {
                                sourceText = 'Долговременная память*';
                              } else {
                                sourceText = `${sourceValue}*`;
                              }
                              
                              return (
                                <span className="opacity-70 text-xs text-dark-text/70 italic">
                                  {sourceText}
                                </span>
                              );
                            })()}
                          </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          );
        })()
      )}
      
      {/* Индикатор "думает..." */}
      {isTyping && (
        <div className="px-2 sm:px-4 pb-3 sm:pb-4">
          <div className="flex justify-start">
            <div className="flex items-start space-x-2 max-w-[85%] sm:max-w-xs">
              {/* Аватарка ассистента - такая же как у сообщений */}
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-dark-accent flex items-center justify-center flex-shrink-0 border border-dark-border/50">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="text-[10px] sm:text-xs text-dark-text/50 mb-1 px-1">
                  Ассистент
                </div>
                {/* Сообщение с индикатором */}
                <div className="bg-dark-secondary/80 backdrop-blur-sm text-dark-text rounded-xl sm:rounded-2xl rounded-tl-md px-3 sm:px-4 py-2 sm:py-3 shadow-lg border border-dark-border/50">
                  <div className="flex items-center gap-1">
                    <div className="w-1 h-1 bg-custom-blue/80 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-1 h-1 bg-custom-blue/80 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-1 h-1 bg-custom-blue/80 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
      
      {/* Добавляем отступ после последнего сообщения */}
      <div className="h-32" aria-hidden="true"></div>
      
      {/* Модальное окно для просмотра изображения */}
      {imageModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          onClick={() => setImageModalOpen(false)}
        >
          <div className="relative max-w-5xl max-h-[90vh]">
            <button
              onClick={() => setImageModalOpen(false)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300 transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
            <img 
              src={selectedImage} 
              alt="Full size" 
              className="max-w-full max-h-[85vh] object-contain rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}

    </div>
  );
};

export default ChatMessages;
