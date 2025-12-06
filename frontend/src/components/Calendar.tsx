import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { calendarService, folderService, chatService } from '../services/api';
import { Folder, Chat } from '../types';
import { useChat } from '../context/ChatContext';

interface Event {
  id?: string; // Для совместимости с фронтендом
  event_id?: string; // То, что приходит с бэкенда
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

interface CalendarProps {
  onSwitchToChat?: () => void;
}

const Calendar: React.FC<CalendarProps> = ({ onSwitchToChat }) => {
  const navigate = useNavigate();
  const { selectChat } = useChat();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<Event[]>([]);
  const [view, setView] = useState<'week' | 'day'>('week');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedTimeSlot, setSelectedTimeSlot] = useState<{ date: Date; hour: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [showViewModal, setShowViewModal] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [showMobileButtons, setShowMobileButtons] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Для привязки чатов
  const [folders, setFolders] = useState<Folder[]>([]);
  const [chats, setChats] = useState<Chat[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [loadingChats, setLoadingChats] = useState(false);
  
  // Для drag and drop
  const [draggedEvent, setDraggedEvent] = useState<Event | null>(null);
  const [dragOverSlot, setDragOverSlot] = useState<{ date: Date; hour: number } | null>(null);

  // Форма для создания/редактирования события
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_date: '',
    end_date: '',
    category: '',
    color: '#3b82f6',
    is_all_day: false,
    burnout_prevention: false,
    linked_chat_id: null as string | null,
    linked_folder_id: null as string | null
  });

  // Предустановленные цвета как в Google Calendar
  const colorPalette = [
    '#3b82f6', // Синий
    '#ef4444', // Красный
    '#10b981', // Зеленый
    '#f59e0b', // Оранжевый
    '#8b5cf6', // Фиолетовый
    '#ec4899', // Розовый
    '#06b6d4', // Голубой
    '#84cc16', // Лайм
    '#f97316', // Темно-оранжевый
    '#6366f1', // Индиго
  ];

  useEffect(() => {
    loadEvents();
    loadFolders();
  }, [currentDate, view]);

  // Загрузка папок
  const loadFolders = async () => {
    try {
      const foldersList = await folderService.getFolders();
      setFolders(foldersList);
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };

  // Загрузка чатов по выбранной папке
  const loadChats = async (folderId: string | null) => {
    try {
      setLoadingChats(true);
      let chatsList: Chat[];
      
      if (folderId === null || folderId === 'null') {
        // Загружаем чаты вне папок
        const allChats = await chatService.getChats();
        chatsList = allChats.filter(chat => !chat.folder_id || chat.folder_id === null);
      } else {
        // Загружаем чаты из конкретной папки
        chatsList = await folderService.getFolderChats(folderId);
      }
      
      setChats(chatsList);
    } catch (error) {
      console.error('Failed to load chats:', error);
    } finally {
      setLoadingChats(false);
    }
  };

  // Загрузка чатов при изменении выбранной папки
  useEffect(() => {
    if (selectedFolder !== null || formData.linked_folder_id !== null) {
      loadChats(selectedFolder || formData.linked_folder_id);
    }
  }, [selectedFolder, formData.linked_folder_id]);

  // Отслеживание прокрутки для скрытия кнопок на мобилке
  useEffect(() => {
    const scrollContainer = scrollContainerRef.current;
    if (!scrollContainer) return;

    const handleScroll = () => {
      // Проверяем размер экрана (только для мобилки)
      if (window.innerWidth >= 640) return;

      const currentScrollY = scrollContainer.scrollTop;
      
      if (currentScrollY > lastScrollY && currentScrollY > 10) {
        // Прокручиваем вниз - скрываем кнопки (порог всего 10px)
        setShowMobileButtons(false);
      } else if (currentScrollY < lastScrollY) {
        // Прокручиваем вверх - показываем кнопки
        setShowMobileButtons(true);
      }
      
      setLastScrollY(currentScrollY);
    };

    scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
    
    return () => {
      scrollContainer.removeEventListener('scroll', handleScroll);
    };
  }, [lastScrollY]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const startOfPeriod = getStartOfPeriod();
      const endOfPeriod = getEndOfPeriod();
      
      const eventsList = await calendarService.getEvents(
        startOfPeriod.toISOString(),
        endOfPeriod.toISOString()
      );
      
      // Нормализуем события: event_id -> id
      // Важно: start_date и end_date приходят в UTC формате от бэкенда
      // JavaScript автоматически конвертирует их в локальное время при создании new Date()
      const normalizedEvents = eventsList.map((event: any) => ({
        ...event,
        id: event.event_id || event.id,
        // Убеждаемся, что start_date и end_date в правильном формате
        start_date: event.start_date ? (event.start_date.endsWith('Z') ? event.start_date : event.start_date + 'Z') : event.start_date,
        end_date: event.end_date ? (event.end_date.endsWith('Z') ? event.end_date : event.end_date + 'Z') : event.end_date,
      }));
      
      setEvents(normalizedEvents);
    } catch (error) {
      console.error('Failed to load events:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStartOfPeriod = () => {
    if (view === 'week') {
      const start = new Date(currentDate);
      const day = start.getDay();
      const diff = start.getDate() - day + (day === 0 ? -6 : 1);
      start.setDate(diff);
      start.setHours(0, 0, 0, 0);
      return start;
    } else {
      const start = new Date(currentDate);
      start.setHours(0, 0, 0, 0);
      return start;
    }
  };

  const getEndOfPeriod = () => {
    if (view === 'week') {
      const end = new Date(getStartOfPeriod());
      end.setDate(end.getDate() + 7);
      return end;
    } else {
      const end = new Date(currentDate);
      end.setHours(23, 59, 59, 999);
      return end;
    }
  };

  const handleCreateEvent = async () => {
    if (!formData.title || !formData.start_date || !formData.end_date) {
      alert('Заполните обязательные поля');
      return;
    }

    try {
      // Преобразуем локальное время пользователя в UTC для отправки на сервер
      // formData.start_date имеет формат "YYYY-MM-DDTHH:mm" (локальное время)
      // Создаем Date объект из этой строки (JS интерпретирует как локальное время)
      const startDate = new Date(formData.start_date);
      const endDate = new Date(formData.end_date);
      
      // toISOString() конвертирует в UTC и добавляет 'Z'
      // Например: локальное 08:00 (UTC+3) -> 05:00Z в UTC
      const eventData = {
        ...formData,
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      };
      
      if (selectedEvent) {
        const eventId = selectedEvent.id || selectedEvent.event_id;
        if (!eventId) {
          alert('Ошибка: ID события не найден');
          return;
        }
        await calendarService.updateEvent(eventId, eventData);
      } else {
        await calendarService.createEvent(eventData);
      }
      
      setShowCreateModal(false);
      setSelectedEvent(null);
      resetForm();
      loadEvents();
    } catch (error: any) {
      console.error('Failed to create/update event:', error);
      alert(error.response?.data?.detail || 'Ошибка при сохранении события');
    }
  };

  const handleDeleteEvent = async (eventId: string | undefined) => {
    if (!eventId) {
      alert('Ошибка: ID события не найден');
      return;
    }

    if (!window.confirm('Вы уверены, что хотите удалить это событие?')) {
      return;
    }

    try {
      await calendarService.deleteEvent(eventId);
      setShowCreateModal(false);
      setSelectedEvent(null);
      loadEvents();
    } catch (error) {
      console.error('Failed to delete event:', error);
      alert('Ошибка при удалении события');
    }
  };

  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      start_date: '',
      end_date: '',
      category: '',
      color: '#3b82f6',
      is_all_day: false,
      burnout_prevention: false,
      linked_chat_id: null,
      linked_folder_id: null
    });
    setSelectedFolder(null);
    setChats([]);
  };

  const openCreateModal = (date?: Date, hour?: number) => {
    resetForm();
    setSelectedEvent(null);
    
    if (date && hour !== undefined) {
      // Используем локальную дату без конвертации в UTC
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const dateStr = `${year}-${month}-${day}`;
      
      const startHour = hour.toString().padStart(2, '0');
      const endHour = (hour + 1).toString().padStart(2, '0');
      setFormData(prev => ({
        ...prev,
        start_date: `${dateStr}T${startHour}:00`,
        end_date: `${dateStr}T${endHour}:00`
      }));
    }
    
    setShowCreateModal(true);
  };

  const openViewModal = (event: Event) => {
    setSelectedEvent(event);
    setIsEditMode(false);
    setShowViewModal(true);
    
    // Загружаем чаты если есть привязанная папка
    if (event.linked_folder_id) {
      loadChats(event.linked_folder_id);
    }
  };

  const openEditModal = (event: Event) => {
    setSelectedEvent(event);
    setIsEditMode(true);
    
    // Конвертируем UTC время в локальное для отображения в форме
    // event.start_date приходит в формате "2025-12-04T05:00:00.000Z" (UTC)
    // Нужно конвертировать в локальное время и форматировать как "YYYY-MM-DDTHH:mm"
    const startDate = new Date(event.start_date);
    const endDate = new Date(event.end_date);
    
    // Функция для форматирования даты в формат datetime-local (YYYY-MM-DDTHH:mm)
    const formatDateTimeLocal = (date: Date) => {
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    };
    
    setFormData({
      title: event.title,
      description: event.description || '',
      start_date: formatDateTimeLocal(startDate),
      end_date: formatDateTimeLocal(endDate),
      category: event.category || '',
      color: event.color || '#3b82f6',
      is_all_day: event.is_all_day,
      burnout_prevention: event.burnout_prevention,
      linked_chat_id: event.linked_chat_id || null,
      linked_folder_id: event.linked_folder_id || null
    });
    
    // Загружаем чаты если есть привязанная папка
    if (event.linked_folder_id) {
      setSelectedFolder(event.linked_folder_id);
      loadChats(event.linked_folder_id);
    }
    
    setShowViewModal(false);
    setShowCreateModal(true);
  };
  
  const handleOpenLinkedChat = (chatId: string) => {
    if (!chatId) {
      console.error('Chat ID is missing');
      return;
    }
    // Выбираем чат через context и закрываем модальное окно
    setShowViewModal(false);
    selectChat(chatId);
    
    // Переключаемся на вкладку "Чат" если функция передана
    if (onSwitchToChat) {
      onSwitchToChat();
    }
    
    // Если не на странице чата, переходим на неё
    if (window.location.pathname !== '/chat') {
      navigate('/chat');
    }
  };

  // Drag and Drop handlers
  const handleEventDragStart = (e: React.DragEvent, event: Event) => {
    setDraggedEvent(event);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', ''); // Для совместимости
  };

  const handleEventDragEnd = (e: React.DragEvent) => {
    // Очищаем состояние только если drop не произошел
    // (если drop произошел, состояние очистится в handleTimeSlotDrop)
    if (e.dataTransfer.dropEffect === 'none') {
      setDraggedEvent(null);
      setDragOverSlot(null);
    }
  };

  const handleTimeSlotDragOver = (e: React.DragEvent, date: Date, hour: number) => {
    if (!draggedEvent) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverSlot({ date, hour });
  };

  const handleTimeSlotDragLeave = () => {
    setDragOverSlot(null);
  };

  const handleTimeSlotDrop = async (e: React.DragEvent, date: Date, hour: number) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverSlot(null);
    
    if (!draggedEvent) return;

    const eventId = draggedEvent.id || draggedEvent.event_id;
    if (!eventId) {
      console.error('Event ID is missing');
      setDraggedEvent(null);
      return;
    }

    // Вычисляем новое время
    // date - это локальная дата (создана через new Date() и setHours(0,0,0,0))
    // hour - это локальный час (0-23), который пользователь видит на экране
    
    // Создаем новую дату в локальном времени пользователя
    const newStartDate = new Date(date);
    newStartDate.setHours(hour, 0, 0, 0);

    // Вычисляем длительность события (в миллисекундах)
    const oldStartDate = new Date(draggedEvent.start_date);
    const oldEndDate = new Date(draggedEvent.end_date);
    const durationMs = oldEndDate.getTime() - oldStartDate.getTime();
    const newEndDate = new Date(newStartDate.getTime() + durationMs);

    // Формируем ISO строку в UTC
    // toISOString() автоматически конвертирует локальное время в UTC
    // Если пользователь в UTC+3 и устанавливает 07:00 локальное,
    // то toISOString() вернет 04:00 UTC (07:00 - 3 часа = 04:00 UTC)
    // При чтении из БД 04:00 UTC автоматически конвертируется обратно в 07:00 локальное
    const newStartISO = newStartDate.toISOString();
    const newEndISO = newEndDate.toISOString();

    // Сохраняем оригинальное событие для отката
    const originalEvent = { ...draggedEvent };
    const eventToUpdate = draggedEvent;
    
    // Очищаем состояние перетаскивания
    setDraggedEvent(null);

    try {
      // Обновляем событие через API
      await calendarService.updateEvent(eventId, {
        title: eventToUpdate.title,
        description: eventToUpdate.description || '',
        start_date: newStartISO,
        end_date: newEndISO,
        category: eventToUpdate.category || '',
        color: eventToUpdate.color || '#3b82f6',
        is_all_day: eventToUpdate.is_all_day || false,
        burnout_prevention: eventToUpdate.burnout_prevention || false,
        linked_chat_id: eventToUpdate.linked_chat_id || null,
        linked_folder_id: eventToUpdate.linked_folder_id || null,
      });

      // Оптимистично обновляем событие в локальном состоянии
      setEvents(prevEvents => 
        prevEvents.map(event => {
          const currentEventId = event.id || event.event_id;
          if (currentEventId === eventId) {
            return {
              ...event,
              start_date: newStartISO,
              end_date: newEndISO,
            };
          }
          return event;
        })
      );

      // Перезагружаем события для синхронизации с сервером
      // Используем setTimeout чтобы дать время UI обновиться
      setTimeout(async () => {
        await loadEvents();
      }, 100);
    } catch (error) {
      console.error('Failed to move event:', error);
      // Откатываем изменения при ошибке
      await loadEvents();
      alert('Ошибка при перемещении события');
    }
  };

  // Навигация
  const goToPrevious = () => {
    const newDate = new Date(currentDate);
    if (view === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setDate(newDate.getDate() - 1);
    }
    setCurrentDate(newDate);
  };

  const goToNext = () => {
    const newDate = new Date(currentDate);
    if (view === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setDate(newDate.getDate() + 1);
    }
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Получение дней для отображения
  const getDaysToDisplay = (): Date[] => {
    if (view === 'week') {
      const days: Date[] = [];
      const start = getStartOfPeriod();
      for (let i = 0; i < 7; i++) {
        const day = new Date(start);
        day.setDate(start.getDate() + i);
        days.push(day);
      }
      return days;
    } else {
      return [new Date(currentDate)];
    }
  };

  // Часы для отображения (0-23)
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Получение событий для конкретного дня
  const getEventsForDay = (date: Date): Event[] => {
    const dateStr = date.toDateString();
    return events.filter(event => {
      if (!event.start_date) return false;
      // event.start_date приходит в UTC формате (например, "2025-12-02T23:00:00.000+00:00")
      // new Date() автоматически конвертирует UTC в локальное время
      const eventDate = new Date(event.start_date);
      // toDateString() использует локальное время, что правильно для сравнения
      return eventDate.toDateString() === dateStr;
    });
  };

  // Расчет позиции и высоты события
  const getEventStyle = (event: Event, dayEvents: Event[]) => {
    // start_date приходит в UTC формате (например, "2025-12-02T23:00:00.000+00:00")
    // new Date() автоматически конвертирует UTC в локальное время браузера
    const startDate = new Date(event.start_date);
    const endDate = new Date(event.end_date);
    
    // getHours() и getMinutes() возвращают локальные часы и минуты
    // Это правильно, так как мы отображаем события в локальном времени пользователя
    const startMinutes = startDate.getHours() * 60 + startDate.getMinutes();
    const endMinutes = endDate.getHours() * 60 + endDate.getMinutes();
    
    const top = (startMinutes / 60) * 48; // 48px на час
    const height = Math.max(((endMinutes - startMinutes) / 60) * 48, 24); // минимум 24px
    
    // Определяем перекрывающиеся события
    const overlapping = dayEvents.filter(e => {
      if (e.id === event.id) return false;
      const eStart = new Date(e.start_date);
      const eEnd = new Date(e.end_date);
      return (startDate < eEnd && endDate > eStart);
    });
    
    const eventId = event.id || event.event_id || '';
    const index = overlapping.findIndex(e => {
      const eId = e.id || e.event_id || '';
      return eId < eventId;
    });
    const totalOverlapping = overlapping.length + 1;
    
    const width = 100 / totalOverlapping;
    const left = (index + 1) * width;
    
    return {
      top: `${top}px`,
      height: `${height}px`,
      left: `${left}%`,
      width: `${width}%`,
      backgroundColor: event.color || '#3b82f6',
      borderLeft: `4px solid ${event.color || '#3b82f6'}`
    };
  };

  const formatDateHeader = () => {
    if (view === 'week') {
      const start = getStartOfPeriod();
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      return `${start.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })} - ${end.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}`;
    } else {
      return currentDate.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
    }
  };

  const isToday = (date: Date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  const isInCurrentWeek = (date: Date) => {
    const today = new Date();
    const todayWeekStart = new Date(today);
    const day = todayWeekStart.getDay();
    const diff = todayWeekStart.getDate() - day + (day === 0 ? -6 : 1);
    todayWeekStart.setDate(diff);
    todayWeekStart.setHours(0, 0, 0, 0);
    
    const weekStart = getStartOfPeriod();
    return weekStart.getTime() === todayWeekStart.getTime();
  };

  const daysToDisplay = getDaysToDisplay();

  return (
    <div className="flex-1 flex flex-col bg-dark-primary overflow-hidden">
      {/* Заголовок календаря */}
      <div className="border-b border-dark-border/20 p-4">
        {/* Десктоп версия - grid с 3 колонками */}
        <div className="hidden sm:grid grid-cols-3 items-center gap-4">
          {/* Переключатель вида - слева */}
          <div className="flex items-center gap-1 bg-dark-accent/60 rounded-lg p-0.5 sm:p-1 justify-self-start">
            <button
              onClick={() => setView('day')}
              className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                view === 'day'
                  ? 'bg-custom-blue text-dark-primary shadow-sm'
                  : 'text-dark-text/70 hover:text-dark-text bg-transparent'
              }`}
            >
              День
            </button>
            <button
              onClick={() => setView('week')}
              className={`px-3 px-4 py-1.5 text-xs md:text-sm font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                view === 'week'
                  ? 'bg-custom-blue text-dark-primary shadow-sm'
                  : 'text-dark-text/70 hover:text-dark-text bg-transparent'
              }`}
            >
              Неделя
            </button>
          </div>

          {/* Навигация по датам - по центру с подложкой */}
          <div className="flex justify-center">
            <div className="bg-dark-accent/80 rounded-lg border border-dark-border/30 px-4 py-2 flex items-center gap-3 shadow-lg">
              <button
                onClick={goToPrevious}
                className="text-dark-text/70 hover:text-dark-text p-1"
                title={view === 'week' ? 'Предыдущая неделя' : 'Предыдущий день'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-sm font-medium text-dark-text px-3 whitespace-nowrap">
                {formatDateHeader()}
              </span>
              <button
                onClick={goToNext}
                className="text-dark-text/70 hover:text-dark-text p-1"
                title={view === 'week' ? 'Следующая неделя' : 'Следующий день'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              {(() => {
                const today = new Date();
                const isTodayDisplayed = view === 'week' 
                  ? isInCurrentWeek(today)
                  : today.toDateString() === currentDate.toDateString();
                
                if (!isTodayDisplayed) {
                  return (
                    <button
                      onClick={goToToday}
                      className="ml-2 text-xs text-custom-blue hover:underline whitespace-nowrap"
                      title="Текущая дата"
                    >
                      Сегодня
                    </button>
                  );
                }
                return null;
              })()}
            </div>
          </div>

          {/* Кнопка создать - справа */}
          <div className="flex justify-end">
            <button
              onClick={() => openCreateModal()}
              className="px-3 px-4 py-1.5 text-xs md:text-sm font-medium bg-custom-blue text-dark-primary rounded-md hover:bg-custom-blue/90 transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Создать
            </button>
          </div>
        </div>

        {/* Мобильная версия - кнопки сверху, навигация снизу */}
        <div className="flex sm:hidden flex-col gap-3">
          {/* Кнопки управления - сверху (скрываются при прокрутке вниз) */}
          <div 
            className={`flex items-center justify-between gap-2 transition-all duration-300 ${
              showMobileButtons 
                ? 'opacity-100 max-h-20' 
                : 'opacity-0 max-h-0 overflow-hidden'
            }`}
          >
            {/* Переключатель вида - слева */}
            <div className="flex items-center gap-1 bg-dark-accent/60 rounded-lg p-0.5">
              <button
                onClick={() => setView('day')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  view === 'day'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
              >
                День
              </button>
              <button
                onClick={() => setView('week')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 whitespace-nowrap ${
                  view === 'week'
                    ? 'bg-custom-blue text-dark-primary shadow-sm'
                    : 'text-dark-text/70 hover:text-dark-text bg-transparent'
                }`}
              >
                Неделя
              </button>
            </div>

            {/* Кнопка создать - справа */}
            <button
              onClick={() => openCreateModal()}
              className="px-3 py-1.5 text-xs font-medium bg-custom-blue text-dark-primary rounded-md hover:bg-custom-blue/90 transition-colors flex items-center justify-center gap-1.5 whitespace-nowrap"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Создать
            </button>
          </div>

          {/* Навигация по датам - снизу, на всю ширину с небольшими отступами */}
          <div className="px-2">
            <div className="bg-dark-accent/80 rounded-lg border border-dark-border/30 px-4 py-2 flex items-center justify-between shadow-lg w-full">
              <button
                onClick={goToPrevious}
                className="text-dark-text/70 hover:text-dark-text p-1 flex-shrink-0"
                title={view === 'week' ? 'Предыдущая неделя' : 'Предыдущий день'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-sm font-medium text-dark-text px-3 whitespace-nowrap flex-1 text-center">
                {formatDateHeader()}
              </span>
              <button
                onClick={goToNext}
                className="text-dark-text/70 hover:text-dark-text p-1 flex-shrink-0"
                title={view === 'week' ? 'Следующая неделя' : 'Следующий день'}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
              {(() => {
                const today = new Date();
                const isTodayDisplayed = view === 'week' 
                  ? isInCurrentWeek(today)
                  : today.toDateString() === currentDate.toDateString();
                
                if (!isTodayDisplayed) {
                  return (
                    <button
                      onClick={goToToday}
                      className="ml-2 text-xs text-custom-blue hover:underline whitespace-nowrap flex-shrink-0"
                      title="Текущая дата"
                    >
                      Сегодня
                    </button>
                  );
                }
                return null;
              })()}
            </div>
          </div>
        </div>
      </div>

      {/* Календарь с временной сеткой */}
      <div ref={scrollContainerRef} className="flex-1 overflow-auto custom-scrollbar">
        <div className="flex">
          {/* Колонка с часами */}
          <div className="w-16 flex-shrink-0 border-r border-dark-border/20 bg-dark-accent/20">
            <div className="h-10 border-b border-dark-border/20"></div>
            {hours.map(hour => (
              <div
                key={hour}
                className="h-[48px] border-b border-dark-border/10 px-2 text-xs text-dark-text/60 pt-1"
              >
                {hour.toString().padStart(2, '0')}:00
              </div>
            ))}
          </div>

          {/* Колонки с днями */}
          <div className="flex-1 flex">
            {daysToDisplay.map((date, dayIndex) => {
              const dayEvents = getEventsForDay(date);
              
              return (
                <div key={dayIndex} className="flex-1 border-r border-dark-border/20 last:border-r-0 min-w-[120px]">
                  {/* Заголовок дня */}
                  <div className={`h-10 border-b border-dark-border/20 flex flex-col items-center justify-center ${
                    isToday(date) ? 'bg-custom-blue/20' : 'bg-dark-accent/20'
                  }`}>
                    <div className="text-[10px] text-dark-text/60 uppercase">
                      {date.toLocaleDateString('ru-RU', { weekday: 'short' })}
                    </div>
                    <div className={`text-base font-semibold ${
                      isToday(date) ? 'text-custom-blue' : 'text-dark-text'
                    }`}>
                      {date.getDate()}
                    </div>
                  </div>

                  {/* Временные слоты */}
                  <div className="relative">
                    {hours.map(hour => {
                      const isDragOver = dragOverSlot?.date.toDateString() === date.toDateString() && dragOverSlot?.hour === hour;
                      return (
                        <div
                          key={hour}
                          onClick={() => openCreateModal(date, hour)}
                          onDragOver={(e) => handleTimeSlotDragOver(e, date, hour)}
                          onDragLeave={handleTimeSlotDragLeave}
                          onDrop={(e) => handleTimeSlotDrop(e, date, hour)}
                          className={`h-[48px] border-b border-dark-border/10 hover:bg-dark-accent/20 hover:border-2 hover:border-dashed hover:border-custom-blue/50 cursor-pointer transition-all ${
                            isDragOver ? 'bg-custom-blue/20 border-2 border-dashed border-custom-blue' : ''
                          }`}
                        />
                      );
                    })}

                    {/* События */}
                    {dayEvents.map(event => {
                      const isDragging = draggedEvent?.id === event.id || draggedEvent?.event_id === event.event_id;
                      return (
                        <div
                          key={event.id}
                          draggable
                          onDragStart={(e) => handleEventDragStart(e, event)}
                          onDragEnd={handleEventDragEnd}
                          onClick={(e) => {
                            if (!isDragging) {
                              e.stopPropagation();
                              openViewModal(event);
                            }
                          }}
                          className={`absolute rounded-md px-2 py-1 text-xs hover:opacity-90 transition-opacity overflow-hidden shadow-md group ${
                            isDragging ? 'opacity-50 scale-95' : ''
                          }`}
                          style={{
                            ...getEventStyle(event, dayEvents),
                            userSelect: 'none',
                          }}
                        >
                        <div className="flex items-center justify-between gap-1">
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-white truncate">
                              {event.title}
                            </div>
                            <div className="text-white/80 text-[10px]">
                              {new Date(event.start_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                            </div>
                          </div>
                          {/* Индикатор привязанного чата */}
                          {event.linked_chat_id && (
                            <div 
                              className="flex-shrink-0 w-5 h-5 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm group-hover:bg-white/30 transition-colors"
                              title="Привязан чат"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                              </svg>
                            </div>
                          )}
                        </div>
                      </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Модальное окно просмотра события */}
      {showViewModal && selectedEvent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-secondary rounded-lg border border-dark-border/50 shadow-xl max-w-lg w-full max-h-[90vh] overflow-hidden flex flex-col">
            {/* Цветная полоса сверху */}
            <div 
              className="h-1.5"
              style={{ backgroundColor: selectedEvent.color || '#3b82f6' }}
            />
            
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="p-6">
                {/* Заголовок с кнопками действий */}
                <div className="flex items-start justify-between mb-6">
                  <h2 className="text-2xl font-semibold text-dark-text flex-1 pr-4">
                    {selectedEvent.title}
                  </h2>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => openEditModal(selectedEvent)}
                      className="p-2 text-custom-blue hover:bg-custom-blue/10 rounded-lg transition-colors"
                      title="Редактировать"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDeleteEvent(selectedEvent.id || selectedEvent.event_id)}
                      className="p-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                      title="Удалить"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                    <button
                      onClick={() => setShowViewModal(false)}
                      className="p-2 text-dark-text/50 hover:text-dark-text hover:bg-dark-accent/30 rounded-lg transition-colors"
                      title="Закрыть"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Время - карточка */}
                  <div className="bg-dark-accent/40 rounded-lg border border-dark-border/20 p-4">
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center mt-0.5">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-dark-text mb-1">
                          {new Date(selectedEvent.start_date).toLocaleDateString('ru-RU', { 
                            day: 'numeric', 
                            month: 'long', 
                            year: 'numeric' 
                          })}
                        </div>
                        <div className="text-sm text-dark-text/70">
                          {new Date(selectedEvent.start_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                          {' - '}
                          {new Date(selectedEvent.end_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Описание */}
                  {selectedEvent.description && (
                    <div className="bg-dark-accent/40 rounded-lg border border-dark-border/20 p-4">
                      <div className="flex items-start gap-3">
                        <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center mt-0.5">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
                          </svg>
                        </div>
                        <p className="text-sm text-dark-text/80 whitespace-pre-wrap flex-1">
                          {selectedEvent.description}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Категория и антивыгорание в одной строке если есть */}
                  {(selectedEvent.category || selectedEvent.burnout_prevention) && (
                    <div className="bg-dark-accent/40 rounded-lg border border-dark-border/20 p-4">
                      <div className="space-y-3">
                        {selectedEvent.category && (
                          <div className="flex items-center gap-3">
                            <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                              </svg>
                            </div>
                            <span className="text-sm text-dark-text/80">
                              {selectedEvent.category}
                            </span>
                          </div>
                        )}
                        {selectedEvent.burnout_prevention && (
                          <div className="flex items-center gap-3">
                            <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                            <span className="text-sm text-dark-text/80">
                              Антивыгорание (время для отдыха)
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Привязанный чат */}
                  {selectedEvent.linked_chat_id && (
                    <div className="bg-custom-blue/10 rounded-lg border border-custom-blue/30 p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 flex-shrink-0 flex items-center justify-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-dark-text">Привязан чат</div>
                          <div className="text-xs text-dark-text/60">Нажмите для перехода</div>
                        </div>
                        <button
                          onClick={() => handleOpenLinkedChat(selectedEvent.linked_chat_id!)}
                          className="px-4 py-2 bg-custom-blue text-black text-sm font-medium rounded-lg hover:bg-custom-blue/90 transition-colors flex-shrink-0"
                        >
                          Открыть
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно создания/редактирования события */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-dark-secondary rounded-lg shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-xl font-semibold text-dark-text mb-4">
                {selectedEvent ? 'Редактировать событие' : 'Новое событие'}
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-text/70 mb-1">
                    Название*
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                    placeholder="Название события"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-text/70 mb-1">
                    Описание
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                    placeholder="Описание события"
                    rows={3}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-text/70 mb-1">
                      Начало*
                    </label>
                    <input
                      type="datetime-local"
                      value={formData.start_date}
                      onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                      className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50 [color-scheme:dark]"
                      style={{
                        colorScheme: 'dark'
                      }}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-dark-text/70 mb-1">
                      Конец*
                    </label>
                    <input
                      type="datetime-local"
                      value={formData.end_date}
                      onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                      className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50 [color-scheme:dark]"
                      style={{
                        colorScheme: 'dark'
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-text/70 mb-1">
                    Категория
                  </label>
                  <input
                    type="text"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                    placeholder="Работа, Отдых, Встреча..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-text/70 mb-2">
                    Цвет события
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {colorPalette.map(color => (
                      <button
                        key={color}
                        onClick={() => setFormData({ ...formData, color })}
                        className={`w-8 h-8 rounded-full transition-all ${
                          formData.color === color
                            ? 'ring-2 ring-offset-2 ring-custom-blue ring-offset-dark-secondary'
                            : 'hover:scale-110'
                        }`}
                        style={{ backgroundColor: color }}
                        title={color}
                      />
                    ))}
                  </div>
                </div>

                {/* Кастомные чекбоксы */}
                <div className="space-y-3 pt-2">
                  <label className="flex items-center gap-3 cursor-pointer group">
                    <div className="relative">
                      <input
                        type="checkbox"
                        checked={formData.is_all_day}
                        onChange={(e) => setFormData({ ...formData, is_all_day: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-5 h-5 border-2 border-dark-border/50 rounded bg-dark-accent peer-checked:bg-custom-blue peer-checked:border-custom-blue transition-all flex items-center justify-center">
                        {formData.is_all_day && (
                          <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                    </div>
                    <span className="text-sm text-dark-text/70 group-hover:text-dark-text transition-colors">
                      Событие на весь день
                    </span>
                  </label>

                  <label className="flex items-center gap-3 cursor-pointer group">
                    <div className="relative">
                      <input
                        type="checkbox"
                        checked={formData.burnout_prevention}
                        onChange={(e) => setFormData({ ...formData, burnout_prevention: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-5 h-5 border-2 border-dark-border/50 rounded bg-dark-accent peer-checked:bg-custom-blue peer-checked:border-custom-blue transition-all flex items-center justify-center">
                        {formData.burnout_prevention && (
                          <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                    </div>
                    <span className="text-sm text-dark-text/70 group-hover:text-dark-text transition-colors">
                      Антивыгорание (время для отдыха)
                    </span>
                  </label>
                </div>

                {/* Привязка чата */}
                <div className="pt-4 border-t border-dark-border/20">
                  <label className="block text-sm font-medium text-dark-text/70 mb-2">
                    Привязать чат (опционально)
                  </label>
                  
                  {/* Выбор папки */}
                  <div className="mb-3">
                    <select
                      value={formData.linked_folder_id || ''}
                      onChange={(e) => {
                        const folderId = e.target.value || null;
                        setFormData({ 
                          ...formData, 
                          linked_folder_id: folderId,
                          linked_chat_id: null // Сбрасываем выбранный чат
                        });
                        setSelectedFolder(folderId);
                        if (folderId) {
                          loadChats(folderId);
                        } else {
                          setChats([]);
                        }
                      }}
                      className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                    >
                      <option value="">Не привязывать</option>
                      <option value="null">Вне папок</option>
                      {folders.map(folder => (
                        <option key={folder.folder_id} value={folder.folder_id}>
                          {folder.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Выбор чата */}
                  {formData.linked_folder_id && (
                    <div>
                      <select
                        value={formData.linked_chat_id || ''}
                        onChange={(e) => setFormData({ ...formData, linked_chat_id: e.target.value || null })}
                        className="w-full px-3 py-2 bg-dark-accent border border-dark-border/30 rounded-lg text-dark-text focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                        disabled={loadingChats}
                      >
                        <option value="">-- Выберите чат --</option>
                        {chats.map(chat => (
                          <option key={chat.id} value={chat.id}>
                            {chat.title || 'Без названия'}
                          </option>
                        ))}
                      </select>
                      {loadingChats && (
                        <p className="text-xs text-dark-text/50 mt-1">Загрузка чатов...</p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between mt-6 pt-4 border-t border-dark-border/20">
                <div>
                  {selectedEvent && (
                    <button
                      onClick={() => handleDeleteEvent(selectedEvent.id || selectedEvent.event_id)}
                      className="px-4 py-2 text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                    >
                      Удалить
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setSelectedEvent(null);
                      resetForm();
                    }}
                    className="px-4 py-2 text-dark-text/70 hover:bg-dark-accent/50 rounded-lg transition-colors"
                  >
                    Отмена
                  </button>
                  <button
                    onClick={handleCreateEvent}
                    className="px-4 py-2 bg-custom-blue text-dark-primary rounded-lg hover:bg-custom-blue/90 transition-colors"
                  >
                    {selectedEvent ? 'Сохранить' : 'Создать'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Calendar;
