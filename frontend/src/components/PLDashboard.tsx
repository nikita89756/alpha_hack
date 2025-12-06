import React, { useState, useEffect } from 'react';
import { useChat } from '../context/ChatContext';
import { wbService } from '../services/api';
import { WBPnLData } from '../types';

interface PLDashboardProps {
  onSwitchToChat: () => void;
}

const PLDashboard: React.FC<PLDashboardProps> = ({ onSwitchToChat }) => {
  const { createNewChat, selectedBusinessId } = useChat();
  const [plData, setPlData] = useState<WBPnLData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [showInfoModal, setShowInfoModal] = useState(false);

  // Загрузка данных P&L при монтировании и смене бизнеса
  useEffect(() => {
    // Сбрасываем состояние при смене бизнеса
    setPlData(null);
    setError(null);
    setShowKeyInput(false);
    setHasKey(null);
    setApiKey('');
    // Загружаем данные только если бизнес выбран
    if (selectedBusinessId) {
      loadPnLData();
    }
  }, [selectedBusinessId]);


  // Загрузка данных P&L
  const loadPnLData = async (providedKey?: string) => {
    if (!selectedBusinessId) {
      setError('Выберите бизнес для загрузки данных');
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      // Если передан ключ - сразу сохраняем и загружаем данные
      if (providedKey) {
        const response = await wbService.buildPnL(selectedBusinessId, providedKey);
        if (response.status === 'success' && response.data) {
          setPlData(response.data);
          setHasKey(true);
          setShowKeyInput(false);
          setApiKey(''); // Очищаем поле ввода после успешной загрузки
        }
        return;
      }

      // Сначала пытаемся получить данные из кэша (Redis)
      try {
        const cachedResponse = await wbService.getCachedPnL(selectedBusinessId);
        if (cachedResponse.status === 'success' && cachedResponse.data) {
          console.log('PLDashboard: Данные загружены из кэша Redis');
          setPlData(cachedResponse.data);
          setHasKey(true);
          setShowKeyInput(false);
          return;
        }
      } catch (cacheErr: any) {
        // Если кэш пуст (404) - это нормально, продолжаем проверку ключа
        if (cacheErr.response?.status === 404) {
          console.log('PLDashboard: Кэш пуст, проверяем наличие ключа');
          // Кэш пуст, проверяем наличие ключа и загружаем данные
          try {
            const response = await wbService.buildPnL(selectedBusinessId, null);
            if (response.status === 'success' && response.data) {
              console.log('PLDashboard: Данные загружены с сохраненным ключом');
              setPlData(response.data);
              setHasKey(true);
              setShowKeyInput(false);
              return;
            }
          } catch (keyErr: any) {
            // Если ключа нет - показываем форму ввода
            const errorMessage = keyErr.response?.data?.detail || keyErr.message || '';
            const statusCode = keyErr.response?.status;
            console.log('PLDashboard: Ключ не найден, показываем форму ввода. Status:', statusCode, 'Message:', errorMessage);
            if (statusCode === 400 || 
                errorMessage.includes('API ключ не найден') || 
                errorMessage.includes('не найден') ||
                errorMessage.includes('API ключ не передан')) {
              setHasKey(false);
              setShowKeyInput(true);
              setPlData(null);
              setError(null); // Не показываем ошибку, просто форму ввода
              return;
            }
            // Другие ошибки пробрасываем дальше
            throw keyErr;
          }
        } else {
          // Другие ошибки кэша (не 404) пробрасываем дальше
          console.error('PLDashboard: Ошибка при получении кэша:', cacheErr);
          throw cacheErr;
        }
      }
    } catch (err: any) {
      // Обрабатываем ошибки
      const errorMessage = err.response?.data?.detail || err.message || 'Ошибка при загрузке данных';
      const statusCode = err.response?.status;
      
      // 404 для кэша - это нормально, просто нет данных
      if (statusCode === 404) {
        setHasKey(false);
        setShowKeyInput(true);
        setPlData(null);
        setError(null); // Не показываем ошибку
      } 
      // 400 - обычно означает, что ключа нет или неверный запрос
      else if (statusCode === 400 || 
               errorMessage.includes('API ключ не найден') || 
               errorMessage.includes('не найден') ||
               errorMessage.includes('API ключ не передан')) {
        setHasKey(false);
        setShowKeyInput(true);
        setPlData(null);
        setError(null); // Не показываем ошибку, просто форму ввода
      } 
      // Другие ошибки показываем пользователю
      else {
        setError(errorMessage);
        setPlData(null);
      }
    } finally {
      setLoading(false);
    }
  };

  // Обработка отправки ключа
  const handleSubmitKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) {
      setError('Введите API ключ');
      return;
    }
    await loadPnLData(apiKey.trim());
  };

  // Форматирование чисел
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatNumber = (value: number): string => {
    return new Intl.NumberFormat('ru-RU').format(value);
  };

  // Обработчик кнопки "Спросить у ИИ"
  const handleAskAI = async (widgetType: string, widgetData: any) => {
    if (!plData) return;
    
    // Формируем текст для вставки в поле ввода
    let messageText = '';
    
    switch (widgetType) {
      case 'gmv':
        messageText = `Общая выручка (GMV): ${formatCurrency(widgetData.gmv)}`;
        break;
      case 'marginality':
        messageText = `Маржинальность: ${widgetData.marginality}%`;
        break;
      case 'sales':
        messageText = `Количество продаж: ${formatNumber(widgetData.number_of_sales)}`;
        break;
      case 'returns':
        messageText = `Коэффициент возвратов: ${widgetData.coef_returns}%`;
        break;
      case 'top_sku':
        messageText = `Топ-5 SKU по выручке:\n${Object.entries(widgetData.top_5_sku)
          .map(([name, value]) => `- ${name}: ${formatCurrency(value as number)}`)
          .join('\n')}`;
        break;
      case 'bot_sku':
        messageText = `Худшие 5 SKU по выручке:\n${Object.entries(widgetData.bot_5_sku)
          .map(([name, value]) => `- ${name}: ${formatCurrency(value as number)}`)
          .join('\n')}`;
        break;
      case 'costs':
        messageText = `Расходы:\n- Логистика: ${formatCurrency(widgetData.cost_logistic)}\n- Хранение: ${formatCurrency(widgetData.cost_saving)}\n- Маркетплейс: ${formatCurrency(widgetData.cost_marketplace)}\n- Реклама WB: ${formatCurrency(widgetData.wb_ad_cost)}`;
        break;
      default:
        messageText = JSON.stringify(widgetData, null, 2);
    }
    
    // Сохраняем текст в sessionStorage для последующей вставки
    sessionStorage.setItem('pendingMessage', messageText);
    
    // Создаем новый чат
    console.log('PLDashboard: Creating new chat...');
    await createNewChat();
    console.log('PLDashboard: Chat created, switching to chat tab...');
    
    // Переключаемся на вкладку чата (после создания чата)
    onSwitchToChat();
    console.log('PLDashboard: onSwitchToChat called');
    
    // Вставляем текст в поле ввода через задержку (после переключения на вкладку)
    const insertMessage = () => {
      const textarea = document.querySelector('textarea[data-component-name="ChatInput"]') as HTMLTextAreaElement;
      if (textarea) {
        const savedMessage = sessionStorage.getItem('pendingMessage');
        if (savedMessage) {
          textarea.value = savedMessage;
          textarea.focus();
          // Триггерим событие input для обновления высоты
          const event = new Event('input', { bubbles: true });
          textarea.dispatchEvent(event);
          sessionStorage.removeItem('pendingMessage');
        }
      } else {
        // Если поле ввода еще не готово, повторяем попытку
        setTimeout(insertMessage, 100);
      }
    };
    
    // Пробуем вставить сообщение через небольшую задержку
    setTimeout(insertMessage, 500);
  };

  // Расчет чистой прибыли и расходов
  // marginality = (gmv - total_costs) / gmv, значит net_revenue = gmv * marginality
  const netProfit = plData ? plData.gmv * plData.marginality : 0;

  const totalCosts = plData ? plData.cost_logistic + 
                     plData.cost_saving + 
                     plData.cost_marketplace + 
                     plData.wb_ad_cost : 0;

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-dark-primary">
      <div className={`max-w-7xl mx-auto px-4 sm:px-6 ${!plData ? 'min-h-full flex items-center justify-center py-6' : 'py-6'}`}>
        {/* Заголовок - показываем только после загрузки данных */}
        {plData && (
          <div className="mb-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">P&L по Wildberries</h1>
                <p className="text-dark-text/70 text-sm sm:text-base">Анализ прибыли и убытков по продажам на маркетплейсе</p>
              </div>
              <button
                onClick={() => setShowInfoModal(true)}
                className="text-dark-text/60 hover:text-custom-blue italic text-sm transition-colors underline decoration-dotted underline-offset-2 hover:decoration-custom-blue"
              >
                Для чего это нужно
              </button>
            </div>
          </div>
        )}

        {/* Форма ввода ключа или состояние загрузки */}
        {loading && (
          <div className="max-w-md mx-auto bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-8 shadow-lg">
            <div className="flex items-center justify-center gap-3">
              <div className="w-5 h-5 border-2 border-custom-blue border-t-transparent rounded-full animate-spin"></div>
              <span className="text-dark-text">Загрузка данных...</span>
            </div>
          </div>
        )}

        {!loading && showKeyInput && (
          <div className="max-w-3xl mx-auto text-center space-y-6 sm:space-y-8 px-3 sm:px-4 w-full">
            {/* Иконка */}
            <div className="flex justify-center">
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-custom-blue/20 flex items-center justify-center border border-custom-blue/30">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 sm:h-10 sm:w-10 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
            </div>
            
            {/* Заголовок */}
            <div className="space-y-2 sm:space-y-3">
              <h2 className="text-2xl sm:text-3xl font-bold text-white">Подключение к Wildberries</h2>
              <p className="text-dark-text/70 text-base sm:text-lg max-w-2xl mx-auto leading-relaxed">
                Давайте начнём! Поделитесь доступом к данным с помощью токена API Wildberries.
              </p>
            </div>

            {/* Инструкция */}
            <div className="max-w-2xl mx-auto text-left space-y-4">
              <div className="bg-dark-secondary/50 p-4 sm:p-5 rounded-lg sm:rounded-xl border border-dark-border/30 space-y-3">
                <p className="text-sm sm:text-base text-dark-text/80 leading-relaxed">
                  Его можно создать за несколько шагов:
                </p>
                <ol className="space-y-3 text-sm sm:text-base text-dark-text/70">
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-custom-blue/20 text-custom-blue flex items-center justify-center text-xs font-semibold mt-0.5">1</span>
                    <span>Перейдите в личный кабинет «WB Партнёры»</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-custom-blue/20 text-custom-blue flex items-center justify-center text-xs font-semibold mt-0.5">2</span>
                    <span>Нажмите «Создать токен» в разделе «Интеграции по API» и дайте токену понятное название</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-custom-blue/20 text-custom-blue flex items-center justify-center text-xs font-semibold mt-0.5">3</span>
                    <span>Убедитесь, что опция «Тестовый контур» отключена, а доступ выдан ко всем разделам. Я получаю данные в режиме «Только для чтения».</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-custom-blue/20 text-custom-blue flex items-center justify-center text-xs font-semibold mt-0.5">4</span>
                    <span>Нажмите «Создать» и сразу же скопируйте появившийся токен — посмотреть его ещё раз позже будет нельзя</span>
                  </li>
                </ol>
                <div className="pt-2">
                  <button
                    onClick={() => setShowInfoModal(true)}
                    className="text-dark-text/60 hover:text-custom-blue italic text-sm transition-colors underline decoration-dotted underline-offset-2 hover:decoration-custom-blue"
                  >
                    Для чего это нужно
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <div className="max-w-2xl mx-auto p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm flex items-start gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            {/* Форма */}
            <form onSubmit={handleSubmitKey} className="max-w-2xl mx-auto space-y-5">
              <div className="relative">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="Вставьте ваш токен API"
                  className="w-full px-4 py-3.5 bg-dark-accent/60 border border-dark-border/50 rounded-xl text-dark-text placeholder-dark-text/40 focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue transition-all duration-200 text-center text-base"
                  disabled={loading}
                />
              </div>

              <div className="pt-2 sm:pt-4">
                <button
                  type="submit"
                  disabled={loading || !apiKey.trim()}
                  className="px-6 sm:px-8 py-2.5 sm:py-3 bg-custom-blue hover:bg-custom-blue/90 text-dark-primary font-semibold rounded-lg sm:rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 text-sm sm:text-base disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:hover:shadow-lg"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-dark-primary border-t-transparent rounded-full animate-spin"></div>
                      Загрузка...
                    </span>
                  ) : (
                    'Подключить и загрузить данные'
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {error && !showKeyInput && (
          <div className="mb-6 bg-red-500/20 border border-red-500/50 rounded-xl p-4">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {!plData && !loading && !showKeyInput && (
          <div className="max-w-2xl mx-auto bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-8 shadow-lg text-center">
            <div className="space-y-4">
              <p className="text-dark-text/70 text-base sm:text-lg">Данные не загружены</p>
              <button
                onClick={() => setShowKeyInput(true)}
                className="px-6 sm:px-8 py-2.5 sm:py-3 bg-custom-blue hover:bg-custom-blue/90 text-dark-primary font-semibold rounded-lg sm:rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 text-sm sm:text-base"
              >
                Ввести API ключ
              </button>
            </div>
          </div>
        )}

        {/* Основные метрики */}
        {plData && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {/* GMV */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-dark-text/70">Общая выручка (GMV)</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-white mb-4">{formatCurrency(plData.gmv)}</p>
              <button
                onClick={() => handleAskAI('gmv', { gmv: plData.gmv })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>

            {/* Маржинальность */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-dark-text/70">Маржинальность</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-white mb-4">{(plData.marginality * 100).toFixed(1)}%</p>
              <button
                onClick={() => handleAskAI('marginality', { marginality: (plData.marginality * 100).toFixed(1) })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>

            {/* Количество продаж */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-dark-text/70">Количество продаж</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-white mb-4">{formatNumber(plData.number_of_sales)}</p>
              <button
                onClick={() => handleAskAI('sales', { number_of_sales: plData.number_of_sales })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>

            {/* Коэффициент возвратов */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-5 shadow-lg">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-dark-text/70">Коэффициент возвратов</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <p className="text-2xl font-bold text-white mb-4">{(plData.coef_returns * 100).toFixed(1)}%</p>
              <button
                onClick={() => handleAskAI('returns', { coef_returns: (plData.coef_returns * 100).toFixed(1) })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>
          </div>
        )}

        {/* Топ-5 и Худшие 5 SKU */}
        {plData && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Топ-5 SKU */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-6 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Топ-5 SKU по выручке</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-custom-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
              </div>
              <div className="space-y-3 mb-4">
                {Object.entries(plData.top_5_sku).slice(0, 5).map(([name, value], index) => (
                  <div key={name} className="flex items-center justify-between p-3 bg-dark-accent/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-custom-blue/20 flex items-center justify-center text-custom-blue font-bold text-sm">
                        {index + 1}
                      </div>
                      <span className="text-dark-text font-medium truncate">{name}</span>
                    </div>
                    <span className="text-white font-semibold">{formatCurrency(value)}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => handleAskAI('top_sku', { top_5_sku: plData.top_5_sku })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>

            {/* Худшие 5 SKU */}
            <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-6 shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Худшие 5 SKU по выручке</h3>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
              </div>
              <div className="space-y-3 mb-4">
                {Object.entries(plData.bot_5_sku).slice(0, 5).map(([name, value], index) => (
                  <div key={name} className="flex items-center justify-between p-3 bg-dark-accent/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-red-400/20 flex items-center justify-center text-red-400 font-bold text-sm">
                        {index + 1}
                      </div>
                      <span className="text-dark-text font-medium truncate">{name}</span>
                    </div>
                    <span className="text-white font-semibold">{formatCurrency(value)}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => handleAskAI('bot_sku', { bot_5_sku: plData.bot_5_sku })}
                className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                <span>Спросить у ИИ</span>
              </button>
            </div>
          </div>
        )}

        {/* Расходы */}
        {plData && (
          <div className="bg-dark-secondary/80 rounded-xl border border-dark-border/50 p-6 shadow-lg mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Расходы</h3>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="p-4 bg-dark-accent/50 rounded-lg">
                <div className="text-sm text-dark-text/70 mb-1">Логистика</div>
                <div className="text-xl font-bold text-white">{formatCurrency(plData.cost_logistic)}</div>
              </div>
              <div className="p-4 bg-dark-accent/50 rounded-lg">
                <div className="text-sm text-dark-text/70 mb-1">Хранение</div>
                <div className="text-xl font-bold text-white">{formatCurrency(plData.cost_saving)}</div>
              </div>
              <div className="p-4 bg-dark-accent/50 rounded-lg">
                <div className="text-sm text-dark-text/70 mb-1">Маркетплейс</div>
                <div className="text-xl font-bold text-white">{formatCurrency(plData.cost_marketplace)}</div>
              </div>
              <div className="p-4 bg-dark-accent/50 rounded-lg">
                <div className="text-sm text-dark-text/70 mb-1">Реклама WB</div>
                <div className="text-xl font-bold text-white">{formatCurrency(plData.wb_ad_cost)}</div>
              </div>
            </div>
            <div className="pt-4 border-t border-dark-border/30">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-dark-text/70">Общая сумма расходов</span>
                <span className="text-xl font-bold text-red-400">{formatCurrency(totalCosts)}</span>
              </div>
            </div>
            <button
              onClick={() => handleAskAI('costs', {
                cost_logistic: plData.cost_logistic,
                cost_saving: plData.cost_saving,
                cost_marketplace: plData.cost_marketplace,
                wb_ad_cost: plData.wb_ad_cost
              })}
              className="flex items-center gap-1.5 text-custom-blue hover:text-custom-blue/80 text-xs italic transition-colors cursor-pointer mt-4"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span>Спросить у ИИ</span>
            </button>
          </div>
        )}

        {/* Итоговая прибыль */}
        {plData && (
          <div className="bg-gradient-to-r from-custom-blue/20 to-custom-blue/10 rounded-xl border border-custom-blue/30 p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-white mb-2">Чистая прибыль</h3>
                <p className="text-3xl font-bold text-custom-blue">{formatCurrency(netProfit)}</p>
                <p className="text-sm text-dark-text/70 mt-2">
                  Маржинальность: {(plData.marginality * 100).toFixed(1)}% от GMV
                </p>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-custom-blue/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
          </div>
        )}

        {/* Модальное окно с описанием */}
        {showInfoModal && (
          <div 
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-3 sm:p-4 overflow-y-auto"
            onClick={(e) => {
              if (e.target === e.currentTarget) {
                setShowInfoModal(false);
              }
            }}
          >
            <div 
              className="bg-dark-secondary rounded-xl sm:rounded-2xl border border-dark-border/50 shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="p-5 sm:p-6 lg:p-8">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-xl sm:text-2xl font-bold text-white">P&L по Wildberries</h3>
                  <button
                    onClick={() => setShowInfoModal(false)}
                    className="text-gray-400 hover:text-white transition-colors p-1 rounded-lg hover:bg-dark-accent/30"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>

                <div className="space-y-4 text-dark-text/80 leading-relaxed">
                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Что показывает этот сервис?</h4>
                    <p className="text-sm sm:text-base">
                      P&L (Profit & Loss) дашборд предоставляет полный финансовый анализ ваших продаж на маркетплейсе Wildberries. 
                      Вы получаете детальную информацию о прибыли и убытках, которая помогает принимать обоснованные бизнес-решения.
                    </p>
                  </div>

                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Основные метрики:</h4>
                    <ul className="space-y-2 text-sm sm:text-base list-disc list-inside">
                      <li><strong className="text-white">GMV (Общая выручка)</strong> — общая сумма продаж до вычета всех расходов</li>
                      <li><strong className="text-white">Маржинальность</strong> — процент чистой прибыли от выручки</li>
                      <li><strong className="text-white">Количество продаж</strong> — общее число успешных транзакций</li>
                      <li><strong className="text-white">Коэффициент возвратов</strong> — процент возвращенных товаров</li>
                      <li><strong className="text-white">Топ-5 и худшие SKU</strong> — анализ самых прибыльных и убыточных товаров</li>
                      <li><strong className="text-white">Детализация расходов</strong> — логистика, хранение, комиссии маркетплейса, реклама</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Для чего это нужно?</h4>
                    <ul className="space-y-2 text-sm sm:text-base list-disc list-inside">
                      <li>Понимание реальной прибыльности бизнеса на Wildberries</li>
                      <li>Выявление наиболее и наименее прибыльных товаров</li>
                      <li>Оптимизация расходов на логистику, хранение и рекламу</li>
                      <li>Принятие решений о расширении или сокращении ассортимента</li>
                      <li>Планирование бюджета и прогнозирование доходов</li>
                      <li>Сравнение эффективности разных товаров и категорий</li>
                    </ul>
                  </div>

                  <div>
                    <h4 className="text-lg font-semibold text-white mb-2">Как использовать?</h4>
                    <p className="text-sm sm:text-base">
                      После подключения API ключа данные автоматически загружаются из вашего личного кабинета Wildberries. 
                      Вы можете задать вопросы ИИ-ассистенту о любой метрике, нажав на кнопку "Спросить у ИИ" под каждым виджетом. 
                      Ассистент поможет проанализировать данные и даст рекомендации по улучшению показателей.
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-6 border-t border-dark-border/30">
                  <button
                    onClick={() => setShowInfoModal(false)}
                    className="w-full px-6 py-3 bg-custom-blue hover:bg-custom-blue/90 text-dark-primary font-semibold rounded-lg transition-all duration-300 shadow-lg hover:shadow-xl"
                  >
                    Понятно
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default PLDashboard;

