import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  FaArrowRight, 
  FaBrain, 
  FaUsers, 
  FaChartLine, 
  FaStar,
  FaSun,
  FaLayerGroup,
  FaProjectDiagram,
  FaEllipsisH
} from 'react-icons/fa';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [visibleSections, setVisibleSections] = useState<Set<string>>(new Set(['hero']));
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('data-section-id');
            if (id) {
              setVisibleSections((prev) => new Set(prev).add(id));
            }
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    const sections = document.querySelectorAll('[data-section-id]');
    sections.forEach((section) => observerRef.current?.observe(section));

    return () => {
      sections.forEach((section) => observerRef.current?.unobserve(section));
      observerRef.current?.disconnect();
    };
  }, []);

  const handleDownloadResearch = () => {
    const link = document.createElement('a');
    link.href = '/AI Copilot для микробизнеса.pdf';
    link.download = 'AI Copilot для микробизнеса.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Стили для тепловой карты
  const heatStyles: { [key: number]: { backgroundColor: string; boxShadow: string } } = {
    1: {
      backgroundColor: "rgba(187,253,79,0.10)",
      boxShadow: "0 0 0 1px rgba(42,42,42,0.9)",
    },
    2: {
      backgroundColor: "rgba(187,253,79,0.25)",
      boxShadow: "0 0 0 1px rgba(42,42,42,0.9)",
    },
    3: {
      backgroundColor: "rgba(187,253,79,0.45)",
      boxShadow: "0 0 0 1px rgba(42,42,42,0.9)",
    },
    4: {
      backgroundColor: "rgba(187,253,79,0.75)",
      boxShadow: "0 0 0 1px rgba(187,253,79,0.9)",
    },
    5: {
      backgroundColor: "rgba(187,253,79,0.98)",
      boxShadow: "0 0 16px rgba(187,253,79,0.9)",
    },
  };

  const heatmapRows = [
    {
      label: "Операционный предприниматель",
      role: "Кофейня / салон",
      values: [5, 4, 3, 5, 4],
    },
    {
      label: "Онлайн-предприниматель",
      role: "Онлайн-школа / маркетплейс",
      values: [4, 5, 4, 4, 3],
    },
    {
      label: "Сервисный бизнес",
      role: "Мастерская / услуги",
      values: [3, 4, 3, 4, 5],
    },
  ];

  const legendLevels = [
    { label: "Принципиально важно", level: 5 },
    { label: "Очень важно", level: 4 },
    { label: "Важно", level: 3 },
    { label: "Не очень важно", level: 2 },
    { label: "Не важно", level: 1 },
  ];

  const renderHeatmapCells = () => {
    return heatmapRows.reduce((acc: JSX.Element[], row) => {
      acc.push(
        <div
          key={`${row.label}-label`}
          className="flex flex-col justify-center border-t border-dark-border/50 py-2 pr-3"
        >
          <span className="text-[11px] font-medium text-dark-text">{row.label}</span>
          <span className="text-[10px] text-dark-text/60">{row.role}</span>
        </div>
      );

      row.values.forEach((level, idx) => {
        acc.push(
          <div
            key={`${row.label}-${idx}`}
            className="flex items-center justify-center border-t border-dark-border/50 py-2"
          >
            <div
              className="h-10 w-10 rounded-md"
              style={heatStyles[level]}
            />
          </div>
        );
      });

      return acc;
    }, []);
  };

  const getFadeUpClass = (sectionId: string) => {
    return visibleSections.has(sectionId) 
      ? 'opacity-100 translate-y-0' 
      : 'opacity-0 translate-y-6';
  };
  const transitionClass = 'transition-all duration-700 ease-out';

  return (
    <div className="min-h-screen bg-dark-primary text-white overflow-x-hidden">
      {/* Background glow */}
      <div className="pointer-events-none fixed -top-72 -left-40 h-96 w-96 rounded-full bg-custom-blue/18 blur-3xl" />
      <div className="pointer-events-none fixed -bottom-80 right-[-120px] h-[420px] w-[420px] rounded-full bg-purple-500/16 blur-3xl" />

      <div className="relative mx-auto flex max-w-6xl flex-col gap-12 sm:gap-16 lg:gap-20 px-4 pb-16 sm:pb-20 lg:pb-24 pt-6 sm:pt-8">
        {/* Header */}
        <header className="mb-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0">
          <div className="flex items-center gap-3">
              <img src="/Без названия.avif" alt="AlfaBank Logo" className="h-8 sm:h-10 w-auto" />
            </div>
          <div className="flex flex-wrap items-center gap-2 text-xs w-full sm:w-auto">
              {isAuthenticated ? (
                <button
                  onClick={() => navigate('/chat')}
                className="h-8 px-3 text-xs text-dark-text/70 hover:text-custom-blue transition-colors"
                >
                  Перейти к чату
                </button>
              ) : (
                <>
                  <button
                    onClick={() => navigate('/login')}
                  className="h-8 px-3 text-xs text-dark-text/70 hover:text-custom-blue transition-colors"
                  >
                    Войти
                  </button>
                  <button
                    onClick={() => navigate('/register')}
                  className="h-8 px-3 text-xs text-dark-text/70 hover:text-custom-blue transition-colors"
                  >
                    Регистрация
                  </button>
                </>
              )}
            <button
              className="h-8 rounded-full bg-custom-blue px-3 sm:px-4 text-xs font-semibold text-dark-primary hover:bg-custom-blue/90 transition-colors whitespace-nowrap"
              onClick={handleDownloadResearch}
            >
              <span className="hidden sm:inline">Скачать исследование</span>
              <span className="sm:hidden">Скачать</span>
            </button>
          </div>
        </header>

        {/* Hero Section */}
        <section data-section-id="hero" className={`grid gap-6 sm:gap-8 lg:gap-10 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] lg:items-center ${getFadeUpClass('hero')} ${transitionClass}`}>
          <div className="space-y-4 sm:space-y-6">
            <h1 className="text-balance text-3xl sm:text-4xl font-semibold leading-tight lg:text-[3.1rem]">
              Исследование сферы
              <span className="block text-custom-blue">микробизнеса и Copilot-кейса</span>
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-dark-text/70 sm:text-base">
              Мы не просто сделали чат. Команда провела комплексное исследование: кастдевы, анализ рынка, разбор
              референсов и пользовательских сценариев, чтобы понять, как AI Copilot реально помогает микробизнесу.
            </p>
            <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center gap-3">
              <button
                onClick={() => {
                  const heatmapSection = document.getElementById('heatmap-section');
                  heatmapSection?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="h-10 rounded-full bg-custom-blue px-4 sm:px-5 text-sm font-semibold text-dark-primary hover:bg-custom-blue/90 transition-colors flex items-center justify-center gap-2"
              >
                <span className="hidden sm:inline">Смотреть карту инсайтов</span>
                <span className="sm:hidden">Карта инсайтов</span>
                {/* @ts-ignore - react-icons type compatibility */}
                <FaArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => {
                  const methodologySection = document.getElementById('methodology-section');
                  methodologySection?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="h-10 rounded-full border border-dark-border/50 bg-transparent px-4 sm:px-5 text-sm text-dark-text hover:bg-dark-secondary/50 transition-colors"
              >
                Структура исследования
              </button>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-[10px] sm:text-[11px]">
              <span className="rounded-full bg-dark-secondary/50 px-2 sm:px-3 py-1 text-dark-text/70">Кастдев · Desk research</span>
              <span className="rounded-full bg-dark-secondary/50 px-2 sm:px-3 py-1 text-dark-text/70">Проблемы · Сегменты · User-flow</span>
              <span className="rounded-full bg-dark-secondary/50 px-2 sm:px-3 py-1 text-dark-text/70">Адаптивность · Архитектура профилей</span>
            </div>
          </div>

          {/* Hero: карточка-"доска исследования" */}
          <div className="relative mt-4 lg:mt-0">
            <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl shadow-2xl shadow-black/60">
              <div className="space-y-3 sm:space-y-4 p-3 sm:p-4 lg:p-5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs text-dark-text/70">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-custom-blue/15 text-custom-blue">
                      {/* @ts-ignore - react-icons type compatibility */}
                      <FaBrain className="h-3.5 w-3.5" />
                    </div>
                    <div className="leading-tight">
                      <div className="font-medium">Карта инсайтов</div>
                      <div className="text-[10px] text-dark-text/50">микробизнес · владельцы ИП и ООО</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-dark-text/50">
                    {/* @ts-ignore - react-icons type compatibility */}
                    <FaStar className="h-3.5 w-3.5 text-custom-blue" />
                    research-first подход
          </div>
        </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2 rounded-lg sm:rounded-xl bg-dark-primary/50 p-2.5 sm:p-3 text-xs">
                    <div className="text-[9px] sm:text-[10px] uppercase tracking-[0.14em] text-dark-text/50">Основные боли</div>
                    <ul className="space-y-1 sm:space-y-1.5 text-dark-text/70 text-[11px] sm:text-xs">
                      <li>4+ часа в день на документы и коммуникации.</li>
                      <li>Нет юриста, бухгалтера и маркетолога в штате.</li>
                      <li>Решения без аналитики, «на ощущениях».</li>
                    </ul>
                  </div>
                  <div className="space-y-2 rounded-lg sm:rounded-xl bg-dark-primary/50 p-2.5 sm:p-3 text-xs">
                    <div className="text-[9px] sm:text-[10px] uppercase tracking-[0.14em] text-dark-text/50">Ключевые выводы</div>
                    <ul className="space-y-1 sm:space-y-1.5 text-dark-text/70 text-[11px] sm:text-xs">
                      <li>Нужен единый помощник, а не десяток сервисов.</li>
                      <li>Решения должны быть «в кармане» — на ходу.</li>
                      <li>Доверие приходит через прозрачные источники данных.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* О КЕЙСЕ И МЕТОДОЛОГИИ */}
        <section id="methodology-section" data-section-id="methodology" className={`grid gap-6 sm:gap-8 md:grid-cols-[1.2fr_1fr] ${getFadeUpClass('methodology')} ${transitionClass}`}>
          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h2 className="text-base sm:text-lg font-semibold text-white">Контекст кейса</h2>
              <p className="text-xs sm:text-sm text-dark-text/70">
                Кейс хакатона — создать Copilot-приложение для клиентов микробизнеса Альфа-Банка. Не просто чат, а
                продукт, который закрывает реальные потребности предпринимателей и легко адаптируется под разные
                отрасли.
              </p>
              <ul className="mt-2 space-y-1.5 text-xs text-dark-text/70">
                <li>Фокус: клиенты микробизнеса (ИП, ООО до ~15 сотрудников).</li>
                <li>Формат: веб-интерфейс с чат-ассистентом и подключением данных.</li>
                <li>Задача команды: понять, какие сценарии и боли нужно решать в первую очередь.</li>
              </ul>
            </div>
          </div>

          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h2 className="text-base sm:text-lg font-semibold text-white">Методология исследования</h2>
              <div className="space-y-2 text-xs sm:text-sm text-dark-text/70">
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaUsers className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Кастдев</span> — интервью с владельцами микробизнеса из разных
                    сфер: услуги, розница, онлайн.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaChartLine className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Desk research</span> — отчёты о МСБ, аналитика регуляторной
                    нагрузки, примеры цифровых продуктов.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaBrain className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Референсы</span> — Microsoft Copilot, Intuit Assist, Shopify
                    Sidekick, решения российских банков.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaProjectDiagram className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">UX-аналитика</span> — сценарии дня предпринимателя, точки
                    фрустрации, карта контактов с банком.
                  </p>
                </div>
            </div>
          </div>
        </div>
      </section>

        {/* ЦИФРЫ ИССЛЕДОВАНИЯ + ИНСАЙТЫ */}
        <section data-section-id="numbers" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('numbers')} ${transitionClass}`}>
          <div className="flex flex-wrap items-end justify-between gap-4">
            <h2 className="text-xl sm:text-2xl font-semibold">Что мы изучили</h2>
        </div>
        
          <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 md:grid-cols-3">
            {[
              {
                label: "Интервью с предпринимателями",
                value: "3",
              },
              {
                label: "Исследований и отчётов",
                value: "5+",
              },
              {
                label: "Ключевых референсов",
                value: "3",
              },
            ].map((item, i) => (
              <div key={i} className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
                <div className="p-3 sm:p-4 space-y-1">
                  <div className="text-xl sm:text-2xl font-semibold text-custom-blue">{item.value}</div>
                  <div className="text-xs sm:text-sm text-dark-text/70">{item.label}</div>
                </div>
                      </div>
            ))}
          </div>

          <div className="grid gap-3 sm:gap-4 sm:grid-cols-1 md:grid-cols-3">
            {[
              {
                title: "Бизнес в кармане",
                text: "Решения микробизнеса принимаются на ходу — в телефоне, между задачами.",
              },
              {
                title: "Один человек — много ролей",
                text: "Типичный владелец совмещает роль директора, бухгалтера, юриста и маркетолога.",
              },
              {
                title: "Интуитивный менеджмент",
                text: "Отчёты и аналитика почти не ведутся — основной инструмент принятия решений: опыт и интуиция.",
              },
            ].map((item, i) => (
              <div key={i} className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
                <div className="p-4 sm:p-5 space-y-2 sm:space-y-3">
                  <h3 className="text-sm font-semibold text-white">{item.title}</h3>
                  <p className="text-xs sm:text-sm text-dark-text/70">{item.text}</p>
                </div>
                </div>
              ))}
          </div>
        </section>

        {/* ПРОБЛЕМЫ И ПАТТЕРНЫ */}
        <section data-section-id="patterns" className={`grid gap-6 sm:gap-8 md:grid-cols-2 ${getFadeUpClass('patterns')} ${transitionClass}`}>
          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h2 className="text-base sm:text-lg font-semibold text-white">Ключевые паттерны поведения</h2>
              <ul className="space-y-2 text-xs sm:text-sm text-dark-text/70">
                <li>Постоянное переключение между сервисами: банк, мессенджеры, таблицы, почта.</li>
                <li>Делегировать дорого — поэтому большинство задач владелец выполняет сам.</li>
                <li>К критическим вопросам (налоги, проверки, договоры) обращаются в последний момент.</li>
                <li>Многие решения принимаются «на глаз» — без проверки цифрами.</li>
              </ul>
            </div>
          </div>
          
          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h2 className="text-base sm:text-lg font-semibold text-white">Основные проблемы микробизнеса</h2>
              <ul className="space-y-2 text-xs sm:text-sm text-dark-text/70">
                <li>Высокая доля рутины: документы, переписка, отчётность.</li>
                <li>Недостаток экспертизы: нет отдельного юриста, финансового аналитика, маркетолога.</li>
                <li>Сложность в понимании законов и требований — страх штрафов и проверок.</li>
                <li>Отсутствие нормального аналитического слоя: нет времени собирать и интерпретировать данные.</li>
              </ul>
            </div>
          </div>
        </section>

        {/* HEATMAP: ЗАДАЧИ × ПРИОРИТЕТ */}
        <section id="heatmap-section" data-section-id="heatmap" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('heatmap')} ${transitionClass}`}>
          <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-end justify-between gap-3 sm:gap-4">
            <h2 className="text-xl sm:text-2xl font-semibold">Тепловая карта задач</h2>
            <span className="max-w-xs text-xs text-dark-text/60">
              Какие задачи владельцы разных типов микробизнеса считают самыми важными для помощи Copilot
            </span>
          </div>

          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="flex flex-col sm:flex-row gap-4 sm:gap-6 overflow-x-auto p-4 sm:p-5">
              {/* Матрица */}
              <div className="min-w-[600px] sm:min-w-[680px] flex-1">
                <div className="grid text-[11px]" style={{ gridTemplateColumns: "1.6fr repeat(5, 1fr)" }}>
                  {/* заголовки столбцов */}
                  <span />
                  <span className="px-1 pb-2 text-center text-dark-text/60">Документы и письма</span>
                  <span className="px-1 pb-2 text-center text-dark-text/60">Финансы и платежи</span>
                  <span className="px-1 pb-2 text-center text-dark-text/60">Юрвопросы и налоги</span>
                  <span className="px-1 pb-2 text-center text-dark-text/60">Коммуникации с клиентами</span>
                  <span className="px-1 pb-2 text-center text-dark-text/60">Планирование и задачи</span>

                  {renderHeatmapCells()}
                </div>
              </div>

              {/* Легенда */}
              <div className="flex sm:w-40 w-full flex-col justify-between text-[10px] sm:text-[11px] text-dark-text/70 mt-4 sm:mt-0">
                <div className="space-y-2">
                  <div className="text-xs font-semibold text-dark-text">Приоритет задачи</div>
                  <div className="flex flex-col gap-2">
                    {legendLevels.map((item) => (
                      <div key={item.label} className="flex items-center gap-2">
                        <div
                          className="h-6 w-6 rounded-md"
                          style={heatStyles[item.level]}
                        />
                        <span>{item.label}</span>
                      </div>
                  ))}
                  </div>
                </div>
                <p className="mt-4 text-[10px] text-dark-text/50">
                  Чем насыщеннее цвет, тем выше приоритет задачи по результатам интервью (шкала 1–5).
                </p>
              </div>
          </div>
        </div>
      </section>

        {/* ЭМПАТИЯ: КАРТА ПРЕДПРИНИМАТЕЛЯ */}
        <section data-section-id="empathy" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('empathy')} ${transitionClass}`}>
          <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-end justify-between gap-3 sm:gap-4">
            <h2 className="text-xl sm:text-2xl font-semibold">Карта эмпатии предпринимателя</h2>
            <span className="text-xs text-dark-text/60">Собрали, что владелец микробизнеса думает, чувствует и говорит</span>
          </div>
          
          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="grid gap-3 sm:gap-4 p-4 sm:p-5 sm:grid-cols-2">
              <div className="space-y-3 rounded-xl bg-dark-primary/50 p-3 text-xs">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-dark-text/50">
                  Думает и чувствует
                </div>
                <ul className="space-y-1.5 text-dark-text/70">
                  <li>«Я всё время в долгах по задачам, постоянно что-то не успеваю.»</li>
                  <li>«Боюсь допустить ошибку в налогах или договорах.»</li>
                  <li>«Очень хочется больше заниматься продуктом и клиентами, а не бумажками.»</li>
                </ul>
              </div>

              <div className="space-y-3 rounded-xl bg-dark-primary/50 p-3 text-xs">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-dark-text/50">
                  Видит вокруг
                </div>
                <ul className="space-y-1.5 text-dark-text/70">
                  <li>Много несвязанных сервисов: банк, CRM, таблицы, мессенджеры.</li>
                  <li>Рекламу «готовых решений», которые не учитывают специфику его бизнеса.</li>
                  <li>Сложные тексты законов, писем от банка и госорганов.</li>
                </ul>
              </div>

              <div className="space-y-3 rounded-xl bg-dark-primary/50 p-3 text-xs">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-dark-text/50">
                  Говорит и делает
                </div>
                <ul className="space-y-1.5 text-dark-text/70">
                  <li>«Проще сделать самому, чем объяснять кому-то.»</li>
                  <li>Отвечает клиентам из мессенджеров «на бегу», без шаблонов и поддержки.</li>
                  <li>Откладывает сложные задачи до вечера или «до завтра».</li>
                </ul>
            </div>

              <div className="space-y-3 rounded-xl bg-dark-primary/50 p-3 text-xs">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-dark-text/50">
                  Боли и ожидания от Copilot
                </div>
                <ul className="space-y-1.5 text-dark-text/70">
                  <li>Снять страх ошибок в документах и налогах.</li>
                  <li>Сэкономить время на рутине без найма дополнительного сотрудника.</li>
                  <li>Получать понятные, человеческие ответы, а не тексты из закона.</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* СЕГМЕНТЫ И ПЕРСОНЫ */}
        <section data-section-id="personas" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('personas')} ${transitionClass}`}>
          <div className="flex flex-col sm:flex-row flex-wrap items-start sm:items-end justify-between gap-3 sm:gap-4">
            <h2 className="text-xl sm:text-2xl font-semibold">Сегменты и персоны</h2>
            <span className="text-xs text-dark-text/60">Выделили 3 базовых типа пользователей Copilot</span>
            </div>

          <div className="grid gap-3 sm:gap-4 sm:grid-cols-1 md:grid-cols-3">
            {[
              {
                title: "Операционный предприниматель",
                role: "Владелец кофейни / салона",
                text: "Проводит день на точке, решает всё на бегу. Нужен помощник, который возьмёт на себя документы и переписку.",
              },
              {
                title: "Онлайн-предприниматель",
                role: "Маркетплейс / онлайн-школа",
                text: "Сильнее в маркетинге, слабее в юр- и финчасти. Ищет понятные ответы по налогам и договорам.",
              },
              {
                title: "Сервисный бизнес",
                role: "Мастерская / услуги",
                text: "Основной фокус — клиенты и выезды. Важны напоминания, планирование и короткие подсказки по деньгам.",
              },
            ].map((p, i) => (
              <div key={i} className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
                <div className="p-4 sm:p-5 space-y-2 sm:space-y-3">
                  <h3 className="text-sm font-semibold text-white">{p.title}</h3>
                  <p className="text-[10px] sm:text-[11px] text-dark-text/50">{p.role}</p>
                  <p className="text-xs sm:text-sm text-dark-text/70">{p.text}</p>
                </div>
              </div>
            ))}
            </div>
        </section>

        {/* USER FLOW КАК РЕЗУЛЬТАТ UX-АНАЛИЗА */}
        <section data-section-id="userflow" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('userflow')} ${transitionClass}`}>
          <h2 className="text-xl sm:text-2xl font-semibold">User-flow: день предпринимателя</h2>
          <p className="max-w-xl text-xs sm:text-sm text-dark-text/70">
            На основе интервью мы описали типовой день предпринимателя и точки, где Copilot может встраиваться в
            процессы. Эти сценарии легли в основу продуктового решения.
          </p>
          <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 md:grid-cols-4">
            {[
              {
                time: "Утро",
                // @ts-ignore - react-icons type compatibility
                icon: <FaSun className="h-4 w-4" />,
                text: "Проверка почты, мессенджеров, задач на день. Особо больно — длинные письма и непонятные документы.",
              },
              {
                time: "День",
                // @ts-ignore - react-icons type compatibility
                icon: <FaSun className="h-4 w-4" />,
                text: "Работа с клиентами, срочные вопросы по оплатам, договорам, поставкам.",
              },
              {
                time: "Вечер",
                // @ts-ignore - react-icons type compatibility
                icon: <FaSun className="h-4 w-4" />,
                text: "Попытка подвести итоги по выручке и задачам — но часто на это не остаётся сил.",
              },
              {
                time: "Между",
                // @ts-ignore - react-icons type compatibility
                icon: <FaEllipsisH className="h-4 w-4" />,
                text: "Возникают вопросы «по ходу»: как оформить сотрудника, какая ставка налога, что ответить клиенту.",
              },
            ].map((step, i) => (
              <div key={i} className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
                <div className="p-4 sm:p-5 space-y-2 sm:space-y-3">
                  <div className="flex items-center gap-2 text-xs text-dark-text/70">
                    <div className="flex h-6 w-6 sm:h-7 sm:w-7 items-center justify-center rounded-full bg-dark-primary/50">
                      {step.icon}
                    </div>
                    <span className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-[0.12em] text-dark-text/50">
                      {step.time}
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-dark-text/70">{step.text}</p>
                </div>
              </div>
            ))}
            </div>
        </section>

        {/* АДАПТИВНОСТЬ ПОД ОТРАСЛИ */}
        <section data-section-id="adaptation" className={`grid gap-6 sm:gap-8 md:grid-cols-[1.1fr_1fr] ${getFadeUpClass('adaptation')} ${transitionClass}`}>
          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h2 className="text-base sm:text-lg font-semibold text-white">Адаптивность под разные отрасли</h2>
              <p className="text-xs sm:text-sm text-dark-text/70">
                В исследовании мы проверили, как Copilot можно масштабировать между разными типами микробизнеса без
                переписывания продукта. Выделили общее ядро задач и то, что меняется от отрасли к отрасли.
              </p>
              <div className="mt-3 grid gap-2 text-[11px] sm:grid-cols-2">
                <div className="rounded-xl bg-dark-primary/50 p-3">
                  <div className="mb-1 text-[11px] font-semibold text-dark-text">Общее ядро</div>
                  <ul className="space-y-1 text-dark-text/70">
                    <li>Работа с документами и письмами.</li>
                    <li>Финансовая сводка по обороту.</li>
                    <li>Базовые юридические вопросы.</li>
                  </ul>
                </div>
                <div className="rounded-xl bg-dark-primary/50 p-3">
                  <div className="mb-1 text-[11px] font-semibold text-dark-text">Отраслевые различия</div>
                  <ul className="space-y-1 text-dark-text/70">
                    <li>Свой набор регуляторных требований.</li>
                    <li>Разная сезонность и структура выручки.</li>
                    <li>Набор типичных сценариев (акции, услуги, расписание).</li>
                  </ul>
                </div>
              </div>
              <p className="mt-2 text-[11px] text-dark-text/50">
                Отсюда — идея профилей бизнеса: ядро одинаковое, сверху накладываются отраслевые плейбуки и базы знаний.
              </p>
            </div>
            </div>

          <div className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
            <div className="p-4 sm:p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">Схема адаптации (high level)</h3>
              <div className="space-y-2 text-xs sm:text-sm text-dark-text/70">
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaLayerGroup className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Ядро Copilot</span> — LLM и общий набор инструментов (документы,
                    финансы, FAQ).
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaProjectDiagram className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Отраслевые профили</span> — настройки под тип бизнеса: кофейня,
                    салон, онлайн-школа и т.д.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  {/* @ts-ignore - react-icons type compatibility */}
                  <FaChartLine className="mt-0.5 h-3.5 w-3.5 text-custom-blue flex-shrink-0" />
                  <p>
                    <span className="font-semibold">Данные клиента</span> — подключаемые источники (банк, почта,
                    календарь, учёт), на которых строятся инсайты.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ГИПОТЕЗЫ ЦЕННОСТИ */}
        <section data-section-id="hypotheses" className={`space-y-4 sm:space-y-6 ${getFadeUpClass('hypotheses')} ${transitionClass}`}>
          <h2 className="text-xl sm:text-2xl font-semibold">Гипотезы ценности и метрики</h2>
          <p className="max-w-xl text-xs sm:text-sm text-dark-text/70">
            На основе анализа мы сформулировали измеримые гипотезы, которые можно проверить на пилоте. Это связывает
            исследование с бизнес-результатами Альфа-Банка и клиентов.
          </p>

          <div className="grid gap-3 sm:gap-4 sm:grid-cols-2 md:grid-cols-4">
            {[
              {
                value: "–10 ч/нед",
                text: "Сокращение времени на документооборот и коммуникации.",
              },
              {
                value: "–30% рутины",
                text: "Перенос повторяющихся задач на Copilot.",
              },
              {
                value: "×2 быстрее",
                text: "Принятие решений по юр/фин вопросам.",
              },
              {
                value: "+LTV",
                text: "Рост удержания клиентов микробизнеса в экосистеме Альфы.",
              },
            ].map((kpi, i) => (
              <div key={i} className="border border-dark-border/30 bg-dark-secondary/50 rounded-xl sm:rounded-2xl">
                <div className="p-3 sm:p-4 space-y-2">
                  <div className="text-base sm:text-lg font-semibold text-custom-blue">{kpi.value}</div>
                  <p className="text-xs sm:text-sm text-dark-text/70">{kpi.text}</p>
                </div>
              </div>
            ))}
        </div>
      </section>

        {/* ФИНАЛ */}
        <section data-section-id="final" className={`space-y-4 sm:space-y-6 text-center ${getFadeUpClass('final')} ${transitionClass}`}>
          <h2 className="text-xl sm:text-2xl font-semibold">Исследование как фундамент Copilot</h2>
          <p className="mx-auto max-w-2xl text-xs sm:text-sm text-dark-text/70 px-4">
            Этот лендинг показывает только аналитическую часть: как мы подошли к кейсу, какие выводы сделали и как
            сформулировали гипотезы. На базе этой работы собран прототип Copilot-приложения, который можно показать
            отдельно.
          </p>
          <div className="flex flex-col sm:flex-row flex-wrap justify-center gap-3 px-4">
            <button
              className="h-10 rounded-full bg-custom-blue px-4 sm:px-5 text-sm font-semibold text-dark-primary hover:bg-custom-blue/90 transition-colors"
              onClick={handleDownloadResearch}
            >
              Скачать исследование
            </button>
            <button
              onClick={() => navigate(isAuthenticated ? '/chat' : '/register')}
              className="h-10 rounded-full border border-dark-border/50 bg-transparent px-4 sm:px-5 text-sm text-dark-text hover:bg-dark-secondary/50 transition-colors"
            >
              Посмотреть прототип Copilot
            </button>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="border-t border-dark-border/20 py-8 sm:py-12 mt-12 sm:mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center gap-4 sm:gap-6">
            <div className="flex flex-col sm:flex-row justify-between items-center gap-3 sm:gap-4 w-full text-center sm:text-left">
              <div className="flex items-center gap-3">
                <span className="text-sm sm:text-base text-dark-text/70">© 2025 Хакатон Альфа-Будущее</span>
              </div>
              <div className="flex gap-4 sm:gap-6 text-xs sm:text-sm">
                <a href="https://alfabank.ru/alfafuture/" target="_blank" rel="noopener noreferrer" className="text-dark-text/70 hover:text-custom-blue transition-colors">
                  О хакатоне
                </a>
                <a href="mailto:support@alfabank.ru" className="text-dark-text/70 hover:text-custom-blue transition-colors">
                  Поддержка
                </a>
              </div>
            </div>
            
            {/* Логотипы спонсоров */}
            <div className="flex items-center justify-center gap-6 sm:gap-8 pt-2 sm:pt-4">
              <img src="/ITAM_logo 1.svg" alt="ITAM" className="h-8 sm:h-10 w-auto grayscale opacity-40 hover:opacity-60 transition-opacity" />
              <img src="/Logo_alfa-bank.svg" alt="АльфаБанк" className="h-6 sm:h-8 w-auto grayscale opacity-40 hover:opacity-60 transition-opacity" />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
