import React, { useState, useEffect, useRef } from 'react';
import { Folder, Chat } from '../types';
import { folderService } from '../services/api';
import { useChat } from '../context/ChatContext';

interface DashboardProps {
  onChatSelect: (chatId: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onChatSelect }) => {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [folderChats, setFolderChats] = useState<Record<string, Chat[]>>({});
  const [loading, setLoading] = useState(false);
  const [draggedChat, setDraggedChat] = useState<Chat | null>(null);
  const [dragOverFolder, setDragOverFolder] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [useCurrentDate, setUseCurrentDate] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);
  const [editingFolderName, setEditingFolderName] = useState('');
  const [selectedWeekStart, setSelectedWeekStart] = useState<Date>(() => {
    // Получаем начало текущей недели (понедельник)
    const now = new Date();
    const day = now.getDay();
    const diff = now.getDate() - day + (day === 0 ? -6 : 1); // Приводим к понедельнику
    const monday = new Date(now);
    monday.setDate(diff);
    monday.setHours(0, 0, 0, 0);
    return monday;
  });
  const { refreshChats } = useChat();
  const containerRef = useRef<HTMLDivElement>(null);

  // Загрузка папок при монтировании
  useEffect(() => {
    loadFolders();
  }, []);

  // Загрузка чатов для каждой папки
  useEffect(() => {
    folders.forEach(folder => {
      loadFolderChats(folder.folder_id);
    });
  }, [folders]);

  // Обработка события перемещения чата из дэшборда обратно в sidebar
  useEffect(() => {
    const handleChatMovedFromDashboard = (event: CustomEvent<{ chatId: string }>) => {
      const { chatId } = event.detail;
      // Удаляем чат из всех папок в локальном состоянии
      setFolderChats(prev => {
        const newState = { ...prev };
        Object.keys(newState).forEach(folderId => {
          newState[folderId] = newState[folderId].filter(chat => chat.id !== chatId);
        });
        return newState;
      });
    };

    window.addEventListener('chatMovedFromDashboard', handleChatMovedFromDashboard as EventListener);
    return () => {
      window.removeEventListener('chatMovedFromDashboard', handleChatMovedFromDashboard as EventListener);
    };
  }, []);

  const loadFolders = async () => {
    try {
      setLoading(true);
      const fetchedFolders = await folderService.getFolders(100, 0);
      setFolders(fetchedFolders);
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFolderChats = async (folderId: string) => {
    try {
      const chats = await folderService.getFolderChats(folderId, 100, 0);
      setFolderChats(prev => ({ ...prev, [folderId]: chats }));
    } catch (error) {
      console.error(`Failed to load chats for folder ${folderId}:`, error);
    }
  };

  const handleCreateFolder = async () => {
    setShowCreateModal(true);
  };

  const handleConfirmCreate = async () => {
    if (!newFolderName || !newFolderName.trim()) {
      return;
    }

    try {
      const targetDate = useCurrentDate 
        ? new Date().toISOString() 
        : selectedDate 
          ? new Date(selectedDate + 'T00:00:00').toISOString()
          : null;

      const newFolder = await folderService.createFolder({
        name: newFolderName.trim(),
        description: '',
        target_date: targetDate
      });
      setFolders(prev => [...prev, newFolder]);
      setFolderChats(prev => ({ ...prev, [newFolder.folder_id]: [] }));
      setNewFolderName('');
      setUseCurrentDate(true);
      setSelectedDate(new Date().toISOString().split('T')[0]);
      setShowCreateModal(false);
      
      // Отправляем событие для обновления списка папок в Sidebar
      window.dispatchEvent(new CustomEvent('folderCreated'));
    } catch (error: any) {
      console.error('Failed to create folder:', error);
      alert(error.response?.data?.detail || 'Ошибка при создании дэшборда');
    }
  };

  const handleCancelCreate = () => {
    setNewFolderName('');
    setUseCurrentDate(true);
    setSelectedDate(new Date().toISOString().split('T')[0]);
    setShowCreateModal(false);
  };

  const formatDateAndDay = (dateString: string | null | undefined) => {
    if (!dateString) return null;
    
    const date = new Date(dateString);
    const dayNames = ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'];
    const dayName = dayNames[date.getDay()];
    const formattedDate = date.toLocaleDateString('ru-RU', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    });
    
    return { date: formattedDate, dayName };
  };

  // Получить начало недели (понедельник) для заданной даты
  const getWeekStart = (date: Date): Date => {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Приводим к понедельнику
    const monday = new Date(d);
    monday.setDate(diff);
    monday.setHours(0, 0, 0, 0);
    return monday;
  };

  // Получить конец недели (воскресенье) для заданной даты
  const getWeekEnd = (weekStart: Date): Date => {
    const sunday = new Date(weekStart);
    sunday.setDate(sunday.getDate() + 6);
    sunday.setHours(23, 59, 59, 999);
    return sunday;
  };

  // Форматирование недели для отображения (например, "24-30 ноября")
  const formatWeekRange = (weekStart: Date): string => {
    const weekEnd = getWeekEnd(weekStart);
    const startDay = weekStart.getDate();
    const endDay = weekEnd.getDate();
    
    // Если оба дня в одном месяце
    if (weekStart.getMonth() === weekEnd.getMonth()) {
      const monthName = weekStart.toLocaleDateString('ru-RU', { month: 'long' });
      return `${startDay}-${endDay} ${monthName}`;
    } else {
      // Если неделя пересекает границу месяца
      const startMonth = weekStart.toLocaleDateString('ru-RU', { month: 'long' });
      const endMonth = weekEnd.toLocaleDateString('ru-RU', { month: 'long' });
      return `${startDay} ${startMonth} - ${endDay} ${endMonth}`;
    }
  };

  // Переключение на предыдущую неделю
  const goToPreviousWeek = () => {
    setSelectedWeekStart(prev => {
      const newDate = new Date(prev);
      newDate.setDate(newDate.getDate() - 7);
      return getWeekStart(newDate);
    });
  };

  // Переключение на следующую неделю
  const goToNextWeek = () => {
    setSelectedWeekStart(prev => {
      const newDate = new Date(prev);
      newDate.setDate(newDate.getDate() + 7);
      return getWeekStart(newDate);
    });
  };

  // Переключение на текущую неделю
  const goToCurrentWeek = () => {
    setSelectedWeekStart(getWeekStart(new Date()));
  };

  // Проверка, попадает ли дата папки в выбранную неделю
  const isFolderInSelectedWeek = (folder: Folder): boolean => {
    if (!folder.target_date) return false;
    
    const folderDate = new Date(folder.target_date);
    const weekStart = selectedWeekStart;
    const weekEnd = getWeekEnd(weekStart);
    
    return folderDate >= weekStart && folderDate <= weekEnd;
  };

  // Фильтруем папки по выбранной неделе
  const filteredFolders = folders.filter(isFolderInSelectedWeek);

  const handleDragStart = (chat: Chat) => {
    setDraggedChat(chat);
  };

  const handleDragOver = (e: React.DragEvent, folderId: string | null) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverFolder(folderId);
  };

  const handleDragLeave = () => {
    setDragOverFolder(null);
  };

  const handleDrop = async (e: React.DragEvent, folderId: string | null) => {
    e.preventDefault();
    setDragOverFolder(null);

    // Получаем данные чата из dataTransfer
    let chatToMove: Chat & { fromDashboard?: boolean } | null = draggedChat;
    
    if (!chatToMove) {
      try {
        const chatData = e.dataTransfer.getData('application/json');
        if (chatData) {
          chatToMove = JSON.parse(chatData);
        }
      } catch (error) {
        console.error('Failed to parse dragged chat data:', error);
        return;
      }
    }

    if (!chatToMove) return;

    try {
      const oldFolderId = chatToMove.folder_id;
      
      // Перемещаем чат в папку
      await folderService.moveChatToFolder(chatToMove.id, folderId);
      
      // Обновляем локальное состояние
      if (folderId) {
        // Добавляем чат в новую папку
        setFolderChats(prev => ({
          ...prev,
          [folderId]: [...(prev[folderId] || []), { ...chatToMove!, folder_id: folderId }]
        }));
      }

      // Удаляем чат из старой папки (если он был в папке)
      if (oldFolderId) {
        setFolderChats(prev => ({
          ...prev,
          [oldFolderId]: (prev[oldFolderId] || []).filter(
            chat => chat.id !== chatToMove!.id
          )
        }));
      }

      // Всегда обновляем список чатов в ChatContext после перемещения
      // Это нужно, чтобы чат исчез из левой панели (если он был там)
      // или появился там (если был перемещен обратно)
      await refreshChats();
      
      setDraggedChat(null);
    } catch (error: any) {
      console.error('Failed to move chat:', error);
      alert(error.response?.data?.detail || 'Ошибка при перемещении чата');
    }
  };

  const handleDeleteFolder = async (folderId: string) => {
    if (!window.confirm('Вы уверены, что хотите удалить этот дэшборд? Все чаты будут перемещены в корень.')) {
      return;
    }

    try {
      await folderService.deleteFolder(folderId);
      setFolders(prev => prev.filter(f => f.folder_id !== folderId));
      setFolderChats(prev => {
        const newState = { ...prev };
        delete newState[folderId];
        return newState;
      });
      await refreshChats();
    } catch (error) {
      console.error('Failed to delete folder:', error);
    }
  };

  const handleStartEdit = (folder: Folder) => {
    setEditingFolderId(folder.folder_id);
    setEditingFolderName(folder.name);
  };

  const handleCancelEdit = () => {
    setEditingFolderId(null);
    setEditingFolderName('');
  };

  const handleSaveEdit = async (folderId: string) => {
    if (!editingFolderName.trim()) {
      alert('Название папки не может быть пустым');
      return;
    }

    try {
      const updatedFolder = await folderService.updateFolder(folderId, {
        name: editingFolderName.trim()
      });
      
      // Обновляем папку в локальном состоянии
      setFolders(prev => prev.map(f => 
        f.folder_id === folderId ? { ...f, name: updatedFolder.name } : f
      ));
      
      // Отправляем событие для обновления в других компонентах
      window.dispatchEvent(new CustomEvent('folderUpdated', { 
        detail: { folderId, name: updatedFolder.name } 
      }));
      
      setEditingFolderId(null);
      setEditingFolderName('');
    } catch (error: any) {
      console.error('Failed to update folder:', error);
      alert(error.response?.data?.detail || 'Ошибка при обновлении папки');
    }
  };

  const handleChatClick = (chatId: string) => {
    onChatSelect(chatId);
  };

  if (loading && folders.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-dark-text/70">Загрузка дэшбордов...</div>
      </div>
    );
  }

  return (
    <>
    <div 
      ref={containerRef}
      className="flex-1 flex flex-col overflow-hidden"
      onDragOver={(e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
      }}
      onDrop={(e) => {
        e.preventDefault();
        // Если бросили вне папки, ничего не делаем (чаты остаются без папки)
        // handleDrop(e, null);
      }}
    >
      {/* Фильтр по неделям - над первой карточкой */}
      <div className="flex items-center justify-center pt-4 pb-2 px-4 sm:px-6">
        <div className="bg-dark-accent/80 rounded-lg border border-dark-border/30 px-4 py-2 flex items-center gap-3 shadow-lg">
          <button
            onClick={goToPreviousWeek}
            className="text-dark-text/70 hover:text-dark-text transition-colors p-1"
            title="Предыдущая неделя"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-sm font-medium text-dark-text px-3 whitespace-nowrap">
            {formatWeekRange(selectedWeekStart)}
          </span>
          <button
            onClick={goToNextWeek}
            className="text-dark-text/70 hover:text-dark-text transition-colors p-1"
            title="Следующая неделя"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
          {(() => {
            const today = new Date();
            const currentWeekStart = getWeekStart(today);
            const isCurrentWeek = selectedWeekStart.getTime() === currentWeekStart.getTime();
            if (!isCurrentWeek) {
              return (
                <button
                  onClick={goToCurrentWeek}
                  className="ml-2 text-xs text-custom-blue hover:underline whitespace-nowrap"
                  title="Текущая неделя"
                >
                  Сегодня
                </button>
              );
            }
            return null;
          })()}
        </div>
      </div>
      
      {/* Горизонтальная прокрутка для карточек */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden min-h-0">
        <div className="flex gap-4 p-4 sm:p-6 h-full items-stretch">
          {filteredFolders.map((folder) => (
          <div
            key={folder.folder_id}
            className={`bg-dark-accent/60 rounded-lg border-2 transition-all duration-200 w-80 flex-shrink-0 flex flex-col ${
              dragOverFolder === folder.folder_id
                ? 'border-custom-blue shadow-lg shadow-custom-blue/20'
                : 'border-dark-border/20'
            }`}
            onDragOver={(e) => handleDragOver(e, folder.folder_id)}
            onDragLeave={handleDragLeave}
            onDrop={(e) => handleDrop(e, folder.folder_id)}
          >
            {/* Заголовок папки */}
            <div className="p-4 border-b border-dark-border/20 flex items-center justify-between">
              <div className="flex-1 min-w-0">
                {editingFolderId === folder.folder_id ? (
                  <input
                    type="text"
                    value={editingFolderName}
                    onChange={(e) => setEditingFolderName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveEdit(folder.folder_id);
                      } else if (e.key === 'Escape') {
                        handleCancelEdit();
                      }
                    }}
                    onBlur={() => handleSaveEdit(folder.folder_id)}
                    className="w-full px-2 py-1 text-base font-medium text-dark-text bg-dark-secondary border border-custom-blue/50 rounded focus:outline-none focus:ring-2 focus:ring-custom-blue/50"
                    autoFocus
                  />
                ) : (
                  <>
                    <h3 className="text-base font-medium text-dark-text truncate">
                      {folder.name}
                    </h3>
                    {folder.target_date ? (() => {
                      const dateInfo = formatDateAndDay(folder.target_date);
                      return dateInfo ? (
                        <div className="text-xs text-dark-text/60 mt-1">
                          <span>{dateInfo.date}</span>
                          <span className="ml-2 text-dark-text/50">{dateInfo.dayName}</span>
                        </div>
                      ) : null;
                    })() : (
                      <div className="text-xs text-dark-text/50 mt-1">
                        Дата не указана
                      </div>
                    )}
                    {folder.description && (
                      <p className="text-xs text-dark-text/60 mt-1 truncate">
                        {folder.description}
                      </p>
                    )}
                    <p className="text-xs text-dark-text/50 mt-1">
                      {folderChats[folder.folder_id]?.length || 0} чатов
                    </p>
                  </>
                )}
              </div>
              <div className="ml-2 flex items-center gap-1">
                {editingFolderId === folder.folder_id ? (
                  <>
                    <button
                      onClick={() => handleSaveEdit(folder.folder_id)}
                      className="p-1 text-custom-blue hover:text-custom-blue/80 transition-colors"
                      title="Сохранить"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="p-1 text-dark-text/50 hover:text-dark-text transition-colors"
                      title="Отмена"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleStartEdit(folder)}
                      className="p-1 text-dark-text/50 hover:text-custom-blue transition-colors"
                      title="Редактировать название"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDeleteFolder(folder.folder_id)}
                      className="p-1 text-dark-text/50 hover:text-red-400 transition-colors"
                      title="Удалить дэшборд"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Список чатов в папке */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
              {folderChats[folder.folder_id]?.length > 0 ? (
                folderChats[folder.folder_id].map((chat) => (
                  <div
                    key={chat.id}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.effectAllowed = 'move';
                      e.dataTransfer.setData('application/json', JSON.stringify({ ...chat, fromDashboard: true }));
                    }}
                    onClick={() => handleChatClick(chat.id)}
                    className="p-3 bg-dark-secondary/60 rounded-lg border border-dark-border/20 hover:border-custom-blue/50 hover:bg-dark-secondary/80 cursor-pointer transition-all"
                  >
                    <div className="text-sm font-medium text-dark-text truncate">
                      {chat.title || `Заявка #${chat.id.substring(0, 8)}`}
                    </div>
                    {chat.message_count && chat.message_count > 0 && (
                      <div className="text-xs text-dark-text/50 mt-1">
                        {chat.message_count} сообщений
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center text-dark-text/40 py-8 text-sm">
                  Перетащите чаты сюда
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Кнопка создания нового дэшборда */}
        <div
          className="bg-dark-accent/40 rounded-lg border-2 border-dashed border-dark-border/30 hover:border-custom-blue/50 w-80 flex-shrink-0 flex items-center justify-center cursor-pointer transition-all"
          onClick={handleCreateFolder}
        >
          <div className="text-center">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-12 w-12 text-dark-text/40 mx-auto mb-2"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                clipRule="evenodd"
              />
            </svg>
            <p className="text-sm text-dark-text/60">Создать доску</p>
          </div>
        </div>
        </div>
      </div>
    </div>

    {/* Модальное окно для создания дэшборда */}
    {showCreateModal && (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-dark-secondary rounded-lg border border-dark-border p-6 w-full max-w-md mx-4">
          <h3 className="text-lg font-medium text-dark-text mb-4">
            Создать новый дэшборд
          </h3>
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleConfirmCreate();
              } else if (e.key === 'Escape') {
                handleCancelCreate();
              }
            }}
            placeholder="Введите название дэшборда"
            className="w-full px-4 py-2 bg-dark-accent border border-dark-border rounded-lg text-dark-text placeholder-dark-text/50 focus:outline-none focus:border-custom-blue transition-colors mb-4"
            autoFocus
          />
          
          {/* Поле выбора даты */}
          <div className="mb-4">
            <label className="flex items-center gap-2 mb-2">
              <input
                type="checkbox"
                checked={useCurrentDate}
                onChange={(e) => {
                  setUseCurrentDate(e.target.checked);
                  if (e.target.checked) {
                    setSelectedDate(new Date().toISOString().split('T')[0]);
                  }
                }}
                className="w-4 h-4 text-custom-blue bg-dark-accent border-dark-border rounded focus:ring-custom-blue"
              />
              <span className="text-sm text-dark-text">Использовать текущую дату</span>
            </label>
            {!useCurrentDate && (
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full px-4 py-2 bg-dark-accent border border-dark-border rounded-lg text-dark-text focus:outline-none focus:border-custom-blue transition-colors"
              />
            )}
          </div>

          <div className="flex gap-3 justify-end">
            <button
              onClick={handleCancelCreate}
              className="px-4 py-2 text-dark-text/70 hover:text-dark-text border border-dark-border rounded-lg hover:bg-dark-accent transition-colors"
            >
              Отмена
            </button>
            <button
              onClick={handleConfirmCreate}
              disabled={!newFolderName.trim()}
              className="px-4 py-2 bg-custom-blue text-dark-primary rounded-lg hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              Создать
            </button>
          </div>
        </div>
      </div>
    )}
    </>
  );
};

export default Dashboard;

