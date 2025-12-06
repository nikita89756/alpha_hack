import { useEffect, useCallback, useRef } from 'react';

interface UseWebSocketOptions {
  onMessage: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

// В Docker используем относительный путь /ws (через nginx proxy)
// Локально используем ws://localhost:8002
// Если не задан REACT_APP_WS_URL, используем /ws для работы через nginx proxy
const WS_BASE_URL = process.env.REACT_APP_WS_URL || '/ws';

export const useWebSocket = (chatId: string | null, options: UseWebSocketOptions) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const shouldReconnectRef = useRef(true);

  // Храним актуальные коллбэки в ref, чтобы не пересоздавать соединение на каждый ререндер
  const onMessageRef = useRef(options.onMessage);
  const onOpenRef = useRef(options.onOpen);
  const onCloseRef = useRef(options.onClose);
  const onErrorRef = useRef(options.onError);

  useEffect(() => {
    onMessageRef.current = options.onMessage;
  }, [options.onMessage]);
  useEffect(() => {
    onOpenRef.current = options.onOpen;
  }, [options.onOpen]);
  useEffect(() => {
    onCloseRef.current = options.onClose;
  }, [options.onClose]);
  useEffect(() => {
    onErrorRef.current = options.onError;
  }, [options.onError]);

  const connect = useCallback(() => {
    console.log('🔌 useWebSocket connect() called for chatId:', chatId);
    
    if (!chatId) {
      console.log('useWebSocket: No chatId provided, skipping connection');
      return;
    }

    // Получаем токен из localStorage
    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('useWebSocket: No access token found');
      return;
    }

    // Закрываем существующее соединение если есть
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('useWebSocket: Closing existing connection for chat', chatId);
      // Не пытаться переподключаться по закрытию старого соединения
      shouldReconnectRef.current = false;
      wsRef.current.close();
    }

    // Создаем WebSocket URL
    // Если WS_BASE_URL начинается с /ws (относительный путь), используем текущий host
    let wsUrl: string;
    if (WS_BASE_URL.startsWith('/')) {
      // Относительный путь (например /ws) - используем текущий host
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // WS_BASE_URL уже содержит /ws, просто добавляем chatId
      wsUrl = `${protocol}//${window.location.host}/ws/${chatId}?token=${token}`;
    } else {
      // Абсолютный URL (например ws://localhost:8002)
      wsUrl = `${WS_BASE_URL}/ws/${chatId}?token=${token}`;
    }
    console.log('useWebSocket: Connecting to', wsUrl);

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      // Разрешаем переподключения для нового соединения
      shouldReconnectRef.current = true;

      ws.onopen = () => {
        console.log('useWebSocket: Connected');
        reconnectAttemptsRef.current = 0;
        onOpenRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('useWebSocket: Received message', data);
          onMessageRef.current(data);
        } catch (error) {
          console.error('useWebSocket: Error parsing message', error);
        }
      };

      ws.onerror = (error) => {
        console.error('useWebSocket: Error', error);
        onErrorRef.current?.(error);
      };

      ws.onclose = (event) => {
        console.log('useWebSocket: Closed', event.code, event.reason);
        onCloseRef.current?.();

        // Пытаемся переподключиться если не достигли лимита попыток
        if (shouldReconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts && chatId) {
          reconnectAttemptsRef.current += 1;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          console.log(`useWebSocket: Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (error) {
      console.error('useWebSocket: Failed to create WebSocket', error);
    }
  }, [chatId]);

  useEffect(() => {
    // Предотвращаем двойной вызов в React StrictMode
    let mounted = true;
    
    if (mounted) {
      connect();
    }

    return () => {
      mounted = false;
      console.log('useWebSocket: Cleaning up for chatId:', chatId);
      // Не переподключаться при размонтировании/пересоздании соединения
      shouldReconnectRef.current = false;

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Немедленно закрываем соединение
      if (wsRef.current) {
        console.log('useWebSocket: Closing WebSocket connection for chatId:', chatId);
        try {
          wsRef.current.close();
        } catch (e) {
          // Игнорируем ошибки при закрытии
        }
        wsRef.current = null;
      }
    };
  }, [chatId, connect]); // Зависимость от chatId И connect

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('useWebSocket: Sending message', message);
      wsRef.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    } else {
      console.warn('useWebSocket: Cannot send message, WebSocket not connected');
    }
  }, []);

  return { sendMessage };
};


