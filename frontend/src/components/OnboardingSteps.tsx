import React, { useState, useEffect } from 'react';

export interface OnboardingData {
  // Этап 0: Тип бизнеса (новый этап)
  business_type: string;
  business_name: string;
  business_description: string; // Описание компании
  city: string;
  
  // Этап 1: Бизнес-цели
  business_goals: string[];
  business_goals_description: string;
  
  // Этап 2: Типичный день
  daily_tasks: string[];
  daily_routine_description: string;
  
  // Этап 3: Главная боль
  primary_pain_point: string[];
  pain_description: string;
}

interface OnboardingStepsProps {
  initialData?: Partial<OnboardingData>;
  onComplete: (data: OnboardingData) => void;
  onBack?: () => void;
  startStep?: number; // Начальный этап (0 - тип бизнеса, 1 - цели, и т.д.)
}

const OnboardingSteps: React.FC<OnboardingStepsProps> = ({ 
  initialData = {}, 
  onComplete, 
  onBack,
  startStep = 0
}) => {
  const [currentStep, setCurrentStep] = useState(startStep);
  
  // Этап 0: Тип бизнеса
  const [businessType, setBusinessType] = useState(initialData.business_type || '');
  const [businessName, setBusinessName] = useState(initialData.business_name || '');
  const [businessDescription, setBusinessDescription] = useState(initialData.business_description || '');
  const [city, setCity] = useState(initialData.city || '');
  
  // Этап 1: Бизнес-цели
  const [businessGoalsDescription, setBusinessGoalsDescription] = useState(
    initialData.business_goals_description || ''
  );
  
  // Этап 2: Типичный день
  const [dailyRoutineDescription, setDailyRoutineDescription] = useState(
    initialData.daily_routine_description || ''
  );
  
  // Этап 3: Главная боль
  const [painDescription, setPainDescription] = useState(
    initialData.pain_description || ''
  );

  // Сбрасываем состояние при изменении initialData (если он пустой)
  useEffect(() => {
    if (!initialData || Object.keys(initialData).length === 0) {
      setBusinessType('');
      setBusinessName('');
      setBusinessDescription('');
      setCity('');
      setBusinessGoalsDescription('');
      setDailyRoutineDescription('');
      setPainDescription('');
      setCurrentStep(startStep);
    }
  }, [initialData, startStep]);

  // Сохраняем данные в localStorage при изменении
  useEffect(() => {
    const data: Partial<OnboardingData> = {
      business_type: businessType,
      business_name: businessName,
      business_description: businessDescription,
      city: city,
      business_goals: [], // Не сохраняем выбранные чипы, только текст
      business_goals_description: businessGoalsDescription,
      daily_tasks: [], // Не сохраняем выбранные чипы, только текст
      daily_routine_description: dailyRoutineDescription,
      primary_pain_point: [], // Не сохраняем выбранные чипы, только текст
      pain_description: painDescription,
    };
    localStorage.setItem('onboardingData', JSON.stringify(data));
  }, [businessType, businessName, businessDescription, city, businessGoalsDescription, dailyRoutineDescription, painDescription]);

  const addHintToTextarea = (hint: string, textareaSetter: React.Dispatch<React.SetStateAction<string>>) => {
    textareaSetter(prev => {
      // Если поле пустое, просто добавляем подсказку
      if (!prev.trim()) {
        return hint;
      }
      // Если поле не пустое, добавляем подсказку через точку и пробел
      return `${prev}. ${hint}`;
    });
  };

  const handleNext = () => {
    // Если мы на step 0 и startStep === 0, вызываем onComplete с данными формы бизнеса
    if (currentStep === 0 && startStep === 0) {
      const businessFormData: OnboardingData = {
        business_type: businessType,
        business_name: businessName,
        business_description: businessDescription,
        city: city,
        business_goals: [],
        business_goals_description: '',
        daily_tasks: [],
        daily_routine_description: '',
        primary_pain_point: [],
        pain_description: '',
      };
      onComplete(businessFormData);
      return;
    }
    
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    } else {
      // Завершение онбординга
      const completeData: OnboardingData = {
        business_type: businessType,
        business_name: businessName,
        business_description: businessDescription,
        city: city,
        business_goals: [], // Чипы не сохраняются, только текст
        business_goals_description: businessGoalsDescription,
        daily_tasks: [], // Чипы не сохраняются, только текст
        daily_routine_description: dailyRoutineDescription,
        primary_pain_point: [], // Чипы не сохраняются, только текст
        pain_description: painDescription,
      };
      onComplete(completeData);
      
      // Очищаем все поля после завершения
      setBusinessType('');
      setBusinessName('');
      setBusinessDescription('');
      setCity('');
      setBusinessGoalsDescription('');
      setDailyRoutineDescription('');
      setPainDescription('');
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    } else if (onBack) {
      onBack();
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return businessName.trim().length > 0 && businessType.trim().length > 0 && businessDescription.trim().length > 0;
      case 1:
        return businessGoalsDescription.trim().length > 0;
      case 2:
        return dailyRoutineDescription.trim().length > 0;
      case 3:
        return painDescription.trim().length > 0;
      default:
        return false;
    }
  };

  return (
    <div className="w-full">
      {/* Логотип */}
      <div className="mb-6">
        <div className="flex items-center gap-2">
          <img 
            src="/Без названия.avif" 
            alt="АЛЬФА БУДУЩЕЕ" 
            className="h-8 object-contain"
          />
        </div>
      </div>

      {/* Этап 0: Тип бизнеса */}
      {currentStep === 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-3">
              Добавим бизнес
            </h2>
            <p className="text-gray-300 text-base mb-6">
              Это может быть кофейня, барбершоп, онлайн-школа или магазин на маркетплейсе. От этого зависят подсказки и аналитика.
            </p>
          </div>

          {/* Карточки типов бизнеса */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {[
              {
                id: 'marketplace',
                title: 'МАРКЕТПЛЕЙС',
                subtitle: 'Селлер на Wildberries',
                description: 'Покажем прибыль по WB/Ozon, расходы на рекламу и комиссии, дадим подсказки по лучшим товарам и кампаниям.'
              },
              {
                id: 'offline',
                title: 'ОФФЛАЙН',
                subtitle: 'Кофейня, салон, студия',
                description: 'Поможем считать выручку и расходы точки, держать под контролем смены и задачи команды, планировать акции и спецпредложения.'
              },
              {
                id: 'online',
                title: 'ОНЛАЙН',
                subtitle: 'Услуги и digital-проекты',
                description: 'Поможем собирать заявки, вести клиентов по воронке, напоминать о встречах и готовить контент для продвижения.'
              }
            ].map((type) => (
              <button
                key={type.id}
                type="button"
                onClick={() => setBusinessType(type.id)}
                className={`p-4 rounded-lg border-2 text-left transition-all duration-200 ${
                  businessType === type.id
                    ? 'bg-custom-blue/20 border-custom-blue'
                    : 'bg-dark-accent/70 border-custom-border/50 hover:border-custom-blue/50'
                }`}
              >
                <div className="font-bold text-white mb-1 text-sm">{type.title}</div>
                <div className={`text-sm mb-2 ${businessType === type.id ? 'text-white' : 'text-gray-300'}`}>
                  {type.subtitle}
                </div>
                <div className={`text-xs ${businessType === type.id ? 'text-gray-200' : 'text-gray-400'}`}>
                  {type.description}
                </div>
              </button>
            ))}
          </div>

          <div className="space-y-5">
            <div className="relative">
              <label htmlFor="business_name" className="block text-sm font-medium text-gray-300 mb-1.5">
                Название бизнеса <span className="text-red-500">*</span>
              </label>
              <input
                id="business_name"
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                required
                className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
                placeholder='Например. Кофейня "На Бауманской"'
              />
            </div>

            <div className="relative">
              <label htmlFor="business_description" className="block text-sm font-medium text-gray-300 mb-1.5">
                Описание бизнеса <span className="text-red-500">*</span>
              </label>
              <textarea
                id="business_description"
                value={businessDescription}
                onChange={(e) => setBusinessDescription(e.target.value)}
                required
                rows={4}
                className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500 resize-none"
                placeholder="Опишите ваш бизнес"
              />
            </div>

            <div className="relative">
              <label htmlFor="city" className="block text-sm font-medium text-gray-300 mb-1.5">
                Город
              </label>
              <input
                id="city"
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
                placeholder="Москва"
              />
            </div>
          </div>
        </div>
      )}

      {/* Этап 1: Бизнес-цели */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-3">
              Познакомимся с Вашим бизнесом
            </h2>
            <p className="text-gray-300 text-base mb-6">
              Расскажите, что для Вас сейчас самое важное:<br />рост, стабильность или разгрузить рутину?
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              'Сэкономить время на бумагах и письмах',
              'Найти точки роста выручки',
              'Систематизировать хаос в задачах'
            ].map((hint) => (
              <button
                key={hint}
                type="button"
                onClick={() => addHintToTextarea(hint, setBusinessGoalsDescription)}
                className="px-3 py-1.5 h-8 rounded-full text-xs bg-dark-accent/50 border border-custom-border/30 text-gray-400 hover:border-custom-blue/30 hover:text-gray-300 transition-all duration-200 inline-flex items-center justify-center whitespace-nowrap"
                style={{ fontSize: '0.75rem', lineHeight: '1rem' }}
              >
                {hint}
              </button>
            ))}
          </div>

          <div>
            <textarea
              value={businessGoalsDescription}
              onChange={(e) => setBusinessGoalsDescription(e.target.value)}
              placeholder="Напишите пару предложений, как будто рассказываете другу."
              rows={4}
              className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500 resize-none"
            />
          </div>
        </div>
      )}

      {/* Этап 2: Типичный день */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-3">
              Как проходит Ваш типичный день?
            </h2>
            <p className="text-gray-300 text-base mb-6">
              С какими задачами Вы просыпаетесь?<br />Что откладываете изо дня в день?
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              'Проверяю кассу и платежи',
              'Отвечаю клиентам и партнёрам',
              'Вечером добиваю отчёты и бумажки'
            ].map((hint) => (
              <button
                key={hint}
                type="button"
                onClick={() => addHintToTextarea(hint, setDailyRoutineDescription)}
                className="px-3 py-1.5 h-8 rounded-full text-xs bg-dark-accent/50 border border-custom-border/30 text-gray-400 hover:border-custom-blue/30 hover:text-gray-300 transition-all duration-200 inline-flex items-center justify-center whitespace-nowrap"
                style={{ fontSize: '0.75rem', lineHeight: '1rem' }}
              >
                {hint}
              </button>
            ))}
          </div>

          <div>
            <textarea
              value={dailyRoutineDescription}
              onChange={(e) => setDailyRoutineDescription(e.target.value)}
              placeholder="Напишите пару предложений, как будто рассказываете другу."
              rows={4}
              className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500 resize-none"
            />
          </div>
        </div>
      )}

      {/* Этап 3: Главная боль */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white mb-3">
              Главная боль, которую хочется решить первой
            </h2>
            <p className="text-gray-300 text-base mb-6">
              Это поможет ассистенту сфокусироваться<br />на том, что даст максимум эффекта.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              'Боюсь пропустить важные требования и штрафы',
              'Маркетинг и продажи на интуиции',
              'Сложно посчитать деньги и PnL'
            ].map((hint) => (
              <button
                key={hint}
                type="button"
                onClick={() => addHintToTextarea(hint, setPainDescription)}
                className="px-3 py-1.5 h-8 rounded-full text-xs bg-dark-accent/50 border border-custom-border/30 text-gray-400 hover:border-custom-blue/30 hover:text-gray-300 transition-all duration-200 inline-flex items-center justify-center whitespace-nowrap"
                style={{ fontSize: '0.75rem', lineHeight: '1rem' }}
              >
                {hint}
              </button>
            ))}
          </div>

          <div>
            <textarea
              value={painDescription}
              onChange={(e) => setPainDescription(e.target.value)}
              placeholder="Напишите пару предложений, как будто рассказываете другу."
              rows={4}
              className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500 resize-none"
            />
          </div>
        </div>
      )}

      {/* Информационный текст и кнопки навигации */}
      <div className="flex items-center justify-between gap-4 mt-8 flex-wrap">
        <p className="text-gray-400 text-xs flex-1 min-w-0">
          Ассистент запомнит эти ответы и будет подстраивать советы под ваш контекст.
        </p>
        <div className="flex gap-3 flex-shrink-0">
        <button
          type="button"
          onClick={handleBack}
          className="px-6 py-2.5 text-gray-300 bg-dark-accent/50 border border-custom-border/50 rounded-md hover:bg-dark-accent hover:text-white focus:outline-none focus:ring-2 focus:ring-custom-blue/50 transition-all duration-200 font-medium"
        >
          Назад
        </button>
        <button
          type="button"
          onClick={handleNext}
          disabled={!canProceed()}
          className="px-4 py-2.5 text-white bg-dark-accent border border-custom-border rounded-md hover:bg-dark-secondary hover:border-custom-blue focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:ring-offset-1 focus:ring-offset-dark-secondary disabled:opacity-50 transition-all duration-200 shadow-md hover:shadow-[0_0_10px_rgba(59,130,246,0.3)] font-medium tracking-wide text-base relative disabled:cursor-not-allowed"
        >
          <span className="relative z-10 whitespace-nowrap">
            {currentStep === 3 ? 'Добавить' : 'Далее'}
          </span>
        </button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingSteps;
