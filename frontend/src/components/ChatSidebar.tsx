import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useChat } from '../context/ChatContext';
import { useAuth } from '../context/AuthContext';
import { Chat, Business, BusinessCreate, Folder } from '../types';
import { folderService, businessService, onboardingService } from '../services/api';
import OnboardingSteps, { OnboardingData } from './OnboardingSteps';

// Компонент обратного отсчета
const ClosingCountdown: React.FC<{ closingAt: number }> = ({ closingAt }) => {
  const [timeLeft, setTimeLeft] = useState(Math.max(0, Math.floor((closingAt - Date.now()) / 1000)));

  useEffect(() => {
    const interval = setInterval(() => {
      const newTimeLeft = Math.max(0, Math.floor((closingAt - Date.now()) / 1000));
      setTimeLeft(newTimeLeft);
      
      if (newTimeLeft <= 0) {
        clearInterval(interval);
      }
    }, 100);

    return () => clearInterval(interval);
  }, [closingAt]);

  return (
    <span className="text-xs text-gray-400">
      удаление через {timeLeft}с
    </span>
  );
};

interface ChatSidebarProps {
  onClose?: () => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({ onClose }) => {
  const navigate = useNavigate();
  const { chats, currentChat, selectChat, createNewChat, deleteChat, isLoading, refreshChats, selectedBusinessId, setSelectedBusinessId } = useChat();
  const { user, logout } = useAuth();
  const [showAccountDropdown, setShowAccountDropdown] = useState(false);
  const [showBusinessDropdown, setShowBusinessDropdown] = useState(false);
  const [showFolderDropdown, setShowFolderDropdown] = useState(false);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loadingBusinesses, setLoadingBusinesses] = useState(false);
  const [loadingFolders, setLoadingFolders] = useState(false);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [folderChats, setFolderChats] = useState<Chat[]>([]);
  const [loadingFolderChats, setLoadingFolderChats] = useState(false);
  const [showCreateBusinessModal, setShowCreateBusinessModal] = useState(false);
  const [isCreatingBusiness, setIsCreatingBusiness] = useState(false);
  const [currentBusinessId, setCurrentBusinessId] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingData, setOnboardingData] = useState<Partial<OnboardingData>>({});
  const [isCompletingOnboarding, setIsCompletingOnboarding] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const businessDropdownRef = useRef<HTMLDivElement>(null);
  const folderDropdownRef = useRef<HTMLDivElement>(null);
  
  // Для мобильного drag and drop
  const [selectedChatForMove, setSelectedChatForMove] = useState<Chat | null>(null);
  const [longPressTimer, setLongPressTimer] = useState<NodeJS.Timeout | null>(null);

  // Загрузка бизнесов при монтировании
  useEffect(() => {
    const loadBusinesses = async () => {
      try {
        setLoadingBusinesses(true);
        const userBusinesses = await businessService.getBusinesses();
        setBusinesses(userBusinesses);
        
        // Загружаем сохраненный выбор из localStorage
        const savedBusinessId = localStorage.getItem('selectedBusinessId');
        if (savedBusinessId && userBusinesses.some(b => b.id === savedBusinessId)) {
          setSelectedBusinessId(savedBusinessId);
        }
      } catch (error) {
        console.error('Failed to load businesses:', error);
      } finally {
        setLoadingBusinesses(false);
      }
    };
    
    loadBusinesses();
  }, []);

  // Функция загрузки папок (используется повторно)
  const loadFolders = async () => {
    try {
      setLoadingFolders(true);
      const userFolders = await folderService.getFolders(100, 0);
      setFolders(userFolders);
      
      // Загружаем сохраненный выбор из localStorage
      const savedFolderId = localStorage.getItem('selectedFolderId');
      if (savedFolderId === 'all' || savedFolderId === null) {
        setSelectedFolderId(null);
      } else if (savedFolderId && userFolders.some(f => f.folder_id === savedFolderId)) {
        setSelectedFolderId(savedFolderId);
      } else {
        setSelectedFolderId(null);
        localStorage.setItem('selectedFolderId', 'all');
      }
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoadingFolders(false);
    }
  };

  // Загрузка папок при монтировании
  useEffect(() => {
    loadFolders();
  }, []);

  // Обработка события создания новой папки в Dashboard
  useEffect(() => {
    const handleFolderCreated = () => {
      // Перезагружаем список папок
      const reloadFolders = async () => {
        try {
          const userFolders = await folderService.getFolders(100, 0);
          setFolders(userFolders);
        } catch (error) {
          console.error('Failed to reload folders:', error);
        }
      };
      reloadFolders();
    };

    const handleFolderUpdated = (event: CustomEvent<{ folderId: string; name: string }>) => {
      const { folderId, name } = event.detail;
      // Обновляем название папки в локальном состоянии
      setFolders(prev => prev.map(f => 
        f.folder_id === folderId ? { ...f, name } : f
      ));
    };

    window.addEventListener('folderCreated', handleFolderCreated);
    window.addEventListener('folderUpdated', handleFolderUpdated as EventListener);
    return () => {
      window.removeEventListener('folderCreated', handleFolderCreated);
      window.removeEventListener('folderUpdated', handleFolderUpdated as EventListener);
    };
  }, []);

  // Сохраняем выбранный бизнес в localStorage
  useEffect(() => {
    if (selectedBusinessId) {
      localStorage.setItem('selectedBusinessId', selectedBusinessId);
    } else {
      localStorage.removeItem('selectedBusinessId');
    }
  }, [selectedBusinessId]);

  // Сохраняем выбранную папку в localStorage
  useEffect(() => {
    if (selectedFolderId === null) {
      localStorage.setItem('selectedFolderId', 'all');
    } else {
      localStorage.setItem('selectedFolderId', selectedFolderId);
    }
  }, [selectedFolderId]);

  // Закрываем выпадающие меню при клике вне их
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowAccountDropdown(false);
      }
      if (businessDropdownRef.current && !businessDropdownRef.current.contains(event.target as Node)) {
        setShowBusinessDropdown(false);
      }
      if (folderDropdownRef.current && !folderDropdownRef.current.contains(event.target as Node)) {
        setShowFolderDropdown(false);
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelectChat = (chatId: string) => {
    if (!isLoading) {
      selectChat(chatId);
      // Если мы не на странице чата, переходим на неё
      if (window.location.pathname !== '/chat') {
        navigate('/chat');
      }
      // Закрываем сайдбар на мобильных устройствах
      if (onClose && window.innerWidth < 640) {
        onClose();
      }
    }
  };

  const handleCreateNewChat = () => {
    if (!isLoading) {
      createNewChat();
      // Если мы не на странице чата, переходим на неё
      if (window.location.pathname !== '/chat') {
        navigate('/chat');
      }
    }
  };

  const handleDeleteChat = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    if (!isLoading) {
      deleteChat(chatId);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    // Разрешаем drop только когда выбрано "Все" (selectedFolderId === null)
    if (selectedFolderId !== null) {
      return;
    }
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleBusinessFormComplete = async (data: OnboardingData) => {
    setFormError(null);

    if (!data.business_name.trim()) {
      setFormError('Название бизнеса обязательно');
      return;
    }

    if (!data.business_type.trim()) {
      setFormError('Тип бизнеса обязателен');
      return;
    }

    if (!data.business_description.trim()) {
      setFormError('Описание бизнеса обязательно');
      return;
    }

    setIsCreatingBusiness(true);
    try {
      // Создаем новый бизнес
      const business = await businessService.createBusiness({
        name: data.business_name,
        description: data.business_description,
        industry: data.business_type || null,
      });
      setCurrentBusinessId(business.id);
      
      // Сохраняем данные для следующих этапов
      setOnboardingData(data);
      
      // Переходим к следующему этапу онбординга
      setShowOnboarding(true);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.response?.data?.error || 'Ошибка при сохранении бизнеса');
      setIsCreatingBusiness(false);
    }
  };

  const handleOnboardingComplete = async (data: OnboardingData) => {
    if (!currentBusinessId) {
      setFormError('ID бизнеса не найден');
      return;
    }

    setIsCompletingOnboarding(true);
    setFormError(null);
    try {
      // Отправляем данные онбординга в память
      await onboardingService.completeOnboarding(
        currentBusinessId, 
        {
          business_type: data.business_type,
          business_name: data.business_name,
          city: data.city,
          business_goals: data.business_goals,
          business_description: data.business_goals_description,
          daily_tasks: data.daily_tasks,
          daily_routine_description: data.daily_routine_description,
          primary_pain_point: data.primary_pain_point,
          pain_description: data.pain_description,
        }
      );
      
      // Обновляем список бизнесов
      const updatedBusinesses = await businessService.getBusinesses();
      setBusinesses(updatedBusinesses);
      setSelectedBusinessId(currentBusinessId);
      localStorage.setItem('selectedBusinessId', currentBusinessId);
      
      // Очищаем состояние
      setShowCreateBusinessModal(false);
      setShowOnboarding(false);
      setCurrentBusinessId(null);
      setOnboardingData({});
      setFormError(null);
      
      // Очищаем localStorage
      localStorage.removeItem('onboardingData');
    } catch (err: any) {
      console.error('Onboarding complete error:', err);
      const errorMessage = err.response?.data?.detail || err.response?.data?.error || err.message || 'Ошибка при сохранении данных онбординга';
      setFormError(errorMessage);
      setIsCompletingOnboarding(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    // Разрешаем drop только когда выбрано "Все" (selectedFolderId === null)
    if (selectedFolderId !== null) {
      return;
    }
    
    e.preventDefault();
    
    try {
      const chatData = e.dataTransfer.getData('application/json');
      if (!chatData) return;
      
      const chat: Chat & { fromDashboard?: boolean } = JSON.parse(chatData);
      
      // Если чат из дэшборда, возвращаем его в корень (folder_id = null)
      if (chat.fromDashboard) {
        await folderService.moveChatToFolder(chat.id, null);
        // Обновляем список чатов
        await refreshChats();
        // Отправляем событие для обновления дэшборда
        window.dispatchEvent(new CustomEvent('chatMovedFromDashboard', { detail: { chatId: chat.id } }));
      }
    } catch (error) {
      console.error('Failed to handle drop:', error);
    }
  };

  // Обработчики для мобильного long press
  const handleTouchStart = (chat: Chat) => {
    if (selectedFolderId !== null) return; // Только для "Вне папок"
    
    const timer = setTimeout(() => {
      setSelectedChatForMove(chat);
      // Вибрация при долгом нажатии (если поддерживается)
      if (navigator.vibrate) {
        navigator.vibrate(50);
      }
    }, 500); // 500ms для долгого нажатия
    
    setLongPressTimer(timer);
  };

  const handleTouchEnd = () => {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }
  };

  const handleMoveToFolder = async (folderId: string | null) => {
    if (!selectedChatForMove) return;
    
    try {
      await folderService.moveChatToFolder(selectedChatForMove.id, folderId);
      
      // Обновляем список чатов
      await refreshChats();
      
      // Обновляем папки если перемещаем В папку
      if (folderId) {
        await loadFolders();
        // Отправляем событие для обновления дэшборда
        window.dispatchEvent(new CustomEvent('chatMovedFromDashboard', { detail: { chatId: selectedChatForMove.id } }));
      }
      
      setSelectedChatForMove(null);
    } catch (error) {
      console.error('Failed to move chat:', error);
      setSelectedChatForMove(null);
    }
  };

  // Форматирование даты для заголовка группы
  const formatGroupDate = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Сегодня';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Вчера';
    } else {
      return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
    }
  };

  // Форматирование относительного времени
  const getRelativeTime = (dateString: string) => {
    const now = new Date().getTime();
    const date = new Date(dateString).getTime();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'только что';
    if (diffMins < 60) return `${diffMins} мин. назад`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} ч. назад`;
    
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'вчера';
    if (diffDays === 2) return 'позавчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;
    if (diffDays < 30) {
      const weeks = Math.floor(diffDays / 7);
      return `${weeks} нед. назад`;
    }
    
    const diffMonths = Math.floor(diffDays / 30);
    return `${diffMonths} мес. назад`;
  };

  // Получение текста превью для чата
  const getPreviewText = (chat: Chat) => {
    if (chat.messages && chat.messages.length > 0) {
      const lastMessage = chat.messages[chat.messages.length - 1];
      return lastMessage.content.substring(0, 50) + (lastMessage.content.length > 50 ? '...' : '');
    }
    // Если сообщений нет, не показываем ничего
    return "";
  };

  // Группировка чатов по дате создания
  const groupChatsByDate = (chats: Chat[]) => {
    const groups: { [key: string]: Chat[] } = {};
    
    // Сортировка чатов по дате создания (от новых к старым)
    const sortedChats = [...chats].sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
    
    sortedChats.forEach(chat => {
      const date = new Date(chat.createdAt);
      const dateKey = date.toDateString(); // Используем toDateString как ключ для группировки
      
      if (!groups[dateKey]) {
        groups[dateKey] = [];
      }
      
      groups[dateKey].push(chat);
    });
    
    return groups;
  };

  // Загрузка чатов из выбранной папки
  useEffect(() => {
    const loadFolderChats = async () => {
      if (selectedFolderId === null) {
        setFolderChats([]);
        return;
      }
      
      try {
        setLoadingFolderChats(true);
        const chatsFromFolder = await folderService.getFolderChats(selectedFolderId, 100, 0);
        setFolderChats(chatsFromFolder);
      } catch (error) {
        console.error('Failed to load folder chats:', error);
        setFolderChats([]);
      } finally {
        setLoadingFolderChats(false);
      }
    };
    
    loadFolderChats();
  }, [selectedFolderId]);

  // Фильтруем чаты по выбранной папке
  const filteredChats = selectedFolderId === null 
    ? chats.filter(chat => !chat.folder_id) // Показываем только чаты без папки при выборе "Вне папок"
    : folderChats; // Показываем чаты из выбранной папки

  // Группируем чаты по дате
  const chatGroups = groupChatsByDate(filteredChats);
  
  return (
    <div className="h-full w-full sm:w-64 bg-dark-primary border-r border-dark-border/20 flex flex-col">
      <div className="px-3 sm:px-4 h-14 sm:h-16 flex justify-between sm:justify-center items-center border-b border-dark-border/20">
        <a href="https://alfabank.ru/alfafuture/" target="_blank" rel="noopener noreferrer" className="cursor-pointer flex-1 sm:flex-none">
          <div className="px-3 sm:px-4 py-1.5 bg-dark-secondary/60 rounded-lg hover:bg-dark-secondary/80 transition-all">
            <img src="Без названия.avif" alt="AlfaBank Logo" className="h-7 sm:h-8 w-auto" />
          </div>
        </a>
        {/* Кнопка закрытия для мобильных */}
        {onClose && (
          <button
            onClick={onClose}
            className="sm:hidden text-dark-text hover:text-custom-blue p-2 rounded-lg hover:bg-dark-accent/30 transition-all"
            title="Закрыть"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
      
      {/* Селектор бизнеса */}
      <div className="px-3 sm:px-4 pt-3 pb-2 border-b border-dark-border/20">
        <div className="relative" ref={businessDropdownRef}>
          <label className="block text-xs font-medium text-gray-400 mb-2">Бизнес:</label>
          <button
            type="button"
            onClick={() => setShowBusinessDropdown(!showBusinessDropdown)}
            className="w-full px-3 py-2 text-sm text-dark-text bg-dark-accent/60 border border-dark-border/30 rounded-lg hover:bg-dark-accent/80 focus:outline-none focus:ring-2 focus:ring-custom-blue/50 transition-all flex items-center justify-between"
          >
            <span className="truncate">
              {loadingBusinesses ? (
                'Загрузка...'
              ) : selectedBusinessId && businesses.length > 0 ? (
                businesses.find(b => b.id === selectedBusinessId)?.name || 'Выберите бизнес'
              ) : businesses.length === 0 ? (
                'Нет бизнесов'
              ) : (
                'Выберите бизнес'
              )}
            </span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`h-4 w-4 text-gray-400 transition-transform ${showBusinessDropdown ? 'transform rotate-180' : ''}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
          
          {showBusinessDropdown && (
            <div className="absolute z-50 w-full mt-1 bg-dark-secondary border border-dark-border rounded-lg shadow-lg max-h-60 overflow-y-auto custom-scrollbar">
              {businesses.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-400 text-center">
                  Нет бизнесов
                </div>
              ) : (
                businesses.map((business) => (
                  <button
                    key={business.id}
                    type="button"
                    onClick={() => {
                      setSelectedBusinessId(business.id);
                      localStorage.setItem('selectedBusinessId', business.id);
                      setShowBusinessDropdown(false);
                    }}
                    className="w-full px-3 py-2 text-sm text-left hover:bg-dark-accent/60 transition-colors text-dark-text"
                  >
                    <div className="font-medium truncate">{business.name}</div>
                    {business.description && (
                      <div className="text-xs text-gray-400 truncate mt-0.5">{business.description}</div>
                    )}
                  </button>
                ))
              )}
              {/* Кнопка создания нового бизнеса */}
              <div className="border-t border-dark-border/30">
                <button
                  type="button"
                  onClick={() => {
                    setShowBusinessDropdown(false);
                    setShowCreateBusinessModal(true);
                  }}
                  className="w-full px-3 py-2 text-sm text-left hover:bg-dark-accent/60 transition-colors text-custom-blue flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                  </svg>
                  <span>Создать новый</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Селектор папок */}
      <div className="px-3 sm:px-4 pt-2 pb-3 border-b border-dark-border/20">
        <div className="relative" ref={folderDropdownRef}>
          <label className="block text-xs font-medium text-gray-400 mb-2">Папка:</label>
          <button
            type="button"
            onClick={() => setShowFolderDropdown(!showFolderDropdown)}
            className="w-full px-3 py-2 text-sm text-dark-text bg-dark-accent/60 border border-dark-border/30 rounded-lg hover:bg-dark-accent/80 focus:outline-none focus:ring-2 focus:ring-custom-blue/50 transition-all flex items-center justify-between"
          >
            <span className="truncate">
              {loadingFolders ? (
                'Загрузка...'
              ) : selectedFolderId === null ? (
                'Вне папок'
              ) : folders.find(f => f.folder_id === selectedFolderId)?.name || 'Вне папок'
              }
            </span>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className={`h-4 w-4 text-gray-400 transition-transform ${showFolderDropdown ? 'transform rotate-180' : ''}`}
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
          
          {showFolderDropdown && (
            <div className="absolute z-50 w-full mt-1 bg-dark-secondary border border-dark-border rounded-lg shadow-lg max-h-60 overflow-y-auto custom-scrollbar">
              {/* Опция "Вне папок" */}
              <button
                type="button"
                onClick={() => {
                  setSelectedFolderId(null);
                  localStorage.setItem('selectedFolderId', 'all');
                  setShowFolderDropdown(false);
                }}
                className="w-full px-3 py-2 text-sm text-left hover:bg-dark-accent/60 transition-colors text-dark-text"
              >
                <div className="font-medium truncate">Вне папок</div>
              </button>
              
              {folders.length > 0 && (
                <>
                  <div className="border-t border-dark-border/30 my-1"></div>
                  {folders.map((folder) => (
                    <button
                      key={folder.folder_id}
                      type="button"
                      onClick={() => {
                        setSelectedFolderId(folder.folder_id);
                        localStorage.setItem('selectedFolderId', folder.folder_id);
                        setShowFolderDropdown(false);
                      }}
                      className="w-full px-3 py-2 text-sm text-left hover:bg-dark-accent/60 transition-colors text-dark-text"
                    >
                      <div className="font-medium truncate">{folder.name}</div>
                      {folder.description && (
                        <div className="text-xs text-gray-400 truncate mt-0.5">{folder.description}</div>
                      )}
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      </div>
      
      <div 
        className="flex-1 overflow-y-auto custom-scrollbar"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="p-3 sm:p-4 space-y-4 sm:space-y-5">
          {Object.keys(chatGroups).length === 0 ? (
            <div className="text-center py-8 text-dark-text opacity-70 flex flex-col items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-gray-500 mb-2 opacity-50" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
              </svg>
                     <p>У вас пока нет заявок</p>
                     <p className="text-sm mt-1">Создайте новую заявку, чтобы начать работу</p>
            </div>
          ) : (
            Object.entries(chatGroups).map(([dateKey, chatsInGroup]) => (
              <div key={dateKey} className="mb-6 last:mb-0">
                <h3 className="text-xs uppercase text-gray-500 mb-2 px-2">{formatGroupDate(dateKey)}</h3>
                
                {chatsInGroup.map(chat => (
                  <div 
                    key={chat.id}
                    draggable={selectedFolderId === null}
                    onDragStart={(e) => {
                      if (selectedFolderId !== null) {
                        e.preventDefault();
                        return;
                      }
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('application/json', JSON.stringify(chat));
                    }}
                    onTouchStart={() => handleTouchStart(chat)}
                    onTouchEnd={handleTouchEnd}
                    onTouchMove={handleTouchEnd}
                    onClick={() => {
                      if (selectedChatForMove) {
                        setSelectedChatForMove(null);
                      } else {
                        handleSelectChat(chat.id);
                      }
                    }}
                    className={`p-2.5 sm:p-3 rounded-md cursor-pointer transition-all duration-300 group ${
                      selectedChatForMove && selectedChatForMove.id === chat.id
                        ? 'bg-custom-blue/40 ring-2 ring-custom-blue'
                        : currentChat && currentChat.id === chat.id 
                          ? 'bg-custom-blue/20' 
                          : 'hover:bg-dark-accent/30'
                    }`}
                    data-component-name="ChatSidebar"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1 min-w-0" data-component-name="ChatSidebar">
                               <p className="text-xs sm:text-sm truncate flex items-center text-white" data-component-name="ChatSidebar">
                                 <span className="truncate">{chat.title || `Заявка #${chat.id.substring(0, 8)}`}</span>
                               </p>
                        <p className="text-[10px] sm:text-xs truncate mt-1 text-gray-300">
                          {chat.is_closing && chat.closing_at ? (
                            <ClosingCountdown closingAt={chat.closing_at} />
                          ) : (
                            getPreviewText(chat)
                          )}
                        </p>
                      </div>
                      <button 
                        className="ml-2 p-1.5 text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-500 hover:bg-red-500/10 rounded-full transition-all duration-200 focus:outline-none"
                        onClick={(e) => handleDeleteChat(e, chat.id)}
                               title="Удалить заявку"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Дополнительные кнопки действий */}
      <div className="mt-auto px-3 sm:px-4 py-2 sm:py-3 border-t border-dark-border/20 space-y-2">
        <button 
          onClick={handleCreateNewChat}
          className="w-full py-2 px-3 text-xs sm:text-sm text-dark-text hover:text-white bg-dark-accent/30 hover:bg-dark-accent/50 rounded-lg transition-colors flex items-center justify-start gap-2"
          title="Новый чат"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 sm:h-4 sm:w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M10 3a1 1 0 00-1 1v5H4a1 1 0 100 2h5v5a1 1 0 102 0v-5h5a1 1 0 100-2h-5V4a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Новый чат
        </button>
      </div>
      
      {/* Блок аккаунта в самом низу боковой панели */}
      <div className="p-3 sm:p-4 border-t border-dark-border/20 relative" ref={dropdownRef}>
        <div 
          className="flex items-center cursor-pointer"
          onClick={() => setShowAccountDropdown(!showAccountDropdown)}
        >
          <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-dark-accent flex items-center justify-center text-white shadow-md relative mr-2 sm:mr-3 border border-dark-border/50 hover:border-custom-blue/30 transition-colors">
            <span className="text-base sm:text-lg font-medium">{user?.name ? user.name.charAt(0).toUpperCase() : 'U'}</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs sm:text-sm font-medium text-dark-text truncate">{user?.name || 'Пользователь'}</p>
            <p className="text-[10px] sm:text-xs text-gray-400 truncate">{user?.email || 'email@example.com'}</p>
          </div>
          <div className="ml-2">
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              className={`h-4 w-4 text-gray-400 transition-transform ${showAccountDropdown ? 'rotate-180' : ''}`} 
              viewBox="0 0 20 20" 
              fill="currentColor"
            >
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </div>
        </div>
        
        {/* Выпадающее меню аккаунта */}
        {showAccountDropdown && (
          <div className="absolute bottom-full left-0 right-0 mx-auto w-56 bg-dark-secondary border border-dark-border/50 rounded-lg shadow-xl overflow-hidden animate-fade-in z-10 mb-2">
            <div className="p-3">
              <div className="flex items-center mb-3 pb-3 border-b border-dark-border/30">
                <div className="w-10 h-10 rounded-lg bg-dark-accent flex items-center justify-center text-white shadow-md">
                  <span className="text-lg font-medium">{user?.name ? user.name.charAt(0).toUpperCase() : 'U'}</span>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-white">{user?.name || 'Пользователь'}</p>
                  <p className="text-xs text-gray-400 truncate max-w-[160px]">{user?.email || 'email@example.com'}</p>
                </div>
              </div>
              
              <div className="space-y-1">
                <button 
                  onClick={() => {
                    setShowAccountDropdown(false);
                    logout();
                  }}
                  className="w-full text-left py-2.5 px-3 rounded-md hover:bg-dark-accent/30 flex items-center text-gray-200 transition-colors duration-200"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-3 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                    <polyline points="16 17 21 12 16 7"></polyline>
                    <line x1="21" y1="12" x2="9" y2="12"></line>
                  </svg>
                  <span className="text-sm">Выйти</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Модальное окно для создания бизнеса */}
      {showCreateBusinessModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-3 sm:p-4 overflow-y-auto"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowCreateBusinessModal(false);
              setShowOnboarding(false);
              setCurrentBusinessId(null);
              setOnboardingData({});
              setFormError(null);
            }
          }}
        >
          <div 
            className="bg-dark-secondary rounded-lg sm:rounded-xl border border-dark-border/50 shadow-2xl w-full max-w-2xl my-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-5 sm:p-6 lg:p-8">
              <div className="flex items-center justify-end mb-4">
                <button
                  onClick={() => {
                    setShowCreateBusinessModal(false);
                    setShowOnboarding(false);
                    setCurrentBusinessId(null);
                    setOnboardingData({});
                    setFormError(null);
                  }}
                  className="text-gray-400 hover:text-white transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
              {!showOnboarding ? (
                <OnboardingSteps
                  key="business-modal-step-0"
                  initialData={onboardingData}
                  onComplete={handleBusinessFormComplete}
                  onBack={() => {
                    setShowCreateBusinessModal(false);
                    setOnboardingData({});
                  }}
                  startStep={0}
                />
              ) : (
                <OnboardingSteps
                  key="business-modal-onboarding"
                  initialData={onboardingData}
                  onComplete={handleOnboardingComplete}
                  onBack={() => setShowOnboarding(false)}
                  startStep={1}
                />
              )}
              {formError && (
                <div className="mt-4 p-4 text-sm text-red-500 bg-dark-accent/50 rounded-lg border border-red-500/50 animate-fade-in backdrop-blur-sm">
                  <div className="flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <span>{formError}</span>
                  </div>
                </div>
              )}
              {isCompletingOnboarding && (
                <div className="mt-4 text-center text-gray-400">
                  Сохранение данных...
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Панель перемещения для мобильных устройств */}
      {selectedChatForMove && (
        <div className="fixed inset-x-0 bottom-0 z-50 bg-dark-secondary border-t border-dark-border/50 p-4 shadow-2xl animate-slide-up sm:hidden">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-dark-text">Переместить в папку</h3>
            <button
              onClick={() => setSelectedChatForMove(null)}
              className="text-dark-text/70 hover:text-dark-text p-1 rounded-lg hover:bg-dark-accent/30 transition-all"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
          
          <div className="space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
            {/* Опция "Вне папок" */}
            <button
              onClick={() => handleMoveToFolder(null)}
              className="w-full px-4 py-3 text-left text-sm bg-dark-accent/60 hover:bg-dark-accent/80 rounded-lg transition-colors flex items-center gap-3"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              <span className="text-dark-text">Вне папок</span>
            </button>
            
            {/* Папки */}
            {folders.map((folder) => (
              <button
                key={folder.folder_id}
                onClick={() => handleMoveToFolder(folder.folder_id)}
                className="w-full px-4 py-3 text-left text-sm bg-dark-accent/60 hover:bg-dark-accent/80 rounded-lg transition-colors flex items-center gap-3"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span className="text-dark-text truncate">{folder.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Оверлей для закрытия панели */}
      {selectedChatForMove && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 sm:hidden"
          onClick={() => setSelectedChatForMove(null)}
        />
      )}
    </div>
  );
};

export default ChatSidebar;
