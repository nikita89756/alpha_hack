import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import OnboardingSteps, { OnboardingData } from '../components/OnboardingSteps';
import { businessService, onboardingService } from '../services/api';

const BusinessRegistrationPage: React.FC = () => {
  const { register, login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingAccount, setIsCreatingAccount] = useState(false);
  const [isCompletingOnboarding, setIsCompletingOnboarding] = useState(false);
  const [currentBusinessId, setCurrentBusinessId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingData, setOnboardingData] = useState<Partial<OnboardingData>>({});

  // Загружаем сохраненные данные онбординга из localStorage только если мы не завершили онбординг
  useEffect(() => {
    const savedOnboarding = localStorage.getItem('onboardingData');
    if (savedOnboarding) {
      try {
        const parsed = JSON.parse(savedOnboarding);
        // Проверяем, не завершен ли онбординг (если есть все данные, значит онбординг в процессе)
        // Если данных нет или они пустые, не загружаем
        if (parsed && Object.keys(parsed).length > 0) {
          setOnboardingData(parsed);
        }
      } catch (e) {
        console.error('Failed to parse saved onboarding data:', e);
      }
    }
  }, []);

  // Проверяем наличие данных регистрации
  useEffect(() => {
    const pendingRegistration = localStorage.getItem('pendingRegistration');
    if (!pendingRegistration) {
      // Если данных нет, перенаправляем на регистрацию
      navigate('/register', { replace: true });
      return;
    }
    setIsLoading(false);
  }, [navigate]);

  const createAccount = async () => {
    // Если аккаунт уже создан, просто переходим в чат
    if (isAuthenticated) {
      localStorage.removeItem('pendingRegistration');
      localStorage.removeItem('registrationInProcess');
      navigate('/chat');
      return;
    }

    // Получаем сохраненные данные регистрации
    const pendingRegistration = localStorage.getItem('pendingRegistration');
    if (!pendingRegistration) {
      // Если данных нет, перенаправляем на регистрацию
      navigate('/register');
      return;
    }

    try {
      const registrationData = JSON.parse(pendingRegistration);
      
      // Регистрируем пользователя
      await register({
        username: registrationData.username,
        email: registrationData.email,
        password: registrationData.password,
        full_name: registrationData.full_name,
      });
      
      // Автоматически логиним пользователя
      await login({
        email: registrationData.email,
        password: registrationData.password,
      });
      
      // Удаляем временные данные
      localStorage.removeItem('pendingRegistration');
      localStorage.removeItem('registrationInProcess');
    } catch (err: any) {
      console.error('Failed to create account:', err);
      throw err;
    }
  };

  const handleOnboardingComplete = async (data: OnboardingData) => {
    if (!currentBusinessId) {
      setFormError('ID бизнеса не найден');
      return;
    }

    setIsCompletingOnboarding(true);
    try {
      // Сначала создаем аккаунт, если еще не создан
      if (!isAuthenticated) {
        await createAccount();
      }

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
      
      // Очищаем сохраненные данные онбординга
      localStorage.removeItem('onboardingData');
      
      // Очищаем состояние онбординга для следующего использования
      setOnboardingData({});
      setCurrentBusinessId(null);
      setShowOnboarding(false);
      
      // Переходим в чат
      navigate('/chat');
    } catch (err: any) {
      setFormError(err.response?.data?.detail || err.response?.data?.error || 'Ошибка при сохранении данных онбординга');
      setIsCompletingOnboarding(false);
    }
  };

  const handleBusinessFormComplete = async (data: OnboardingData) => {
    setFormError(null);

    if (!data.business_name.trim()) {
      setFormError('Название бизнеса обязательно');
      return;
    }

    if (!data.business_description.trim()) {
      setFormError('Описание бизнеса обязательно');
      return;
    }

    try {
      // Сначала создаем аккаунт, если еще не создан
      if (!isAuthenticated) {
        await createAccount();
      }

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
    }
  };

  const handleSkip = async () => {
    setIsCreatingAccount(true);
    try {
      await createAccount();
      // Переходим на страницу чата
      navigate('/chat');
    } catch (err) {
      console.error('Failed to skip registration:', err);
    } finally {
      setIsCreatingAccount(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full bg-dark-primary relative overflow-hidden">
        <div className="flex items-center justify-center w-full h-full min-h-screen p-3 sm:p-4">
          <div className="w-full max-w-2xl">
            <div className="p-5 sm:p-6 lg:p-8 rounded-lg sm:rounded-xl bg-dark-secondary/80 backdrop-blur-sm border border-dark-border/50 shadow-2xl">
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-custom-blue"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Если показываем онбординг (этапы 1-3)
  if (showOnboarding) {
    return (
      <div className="flex min-h-screen w-full bg-dark-primary relative overflow-hidden">
        <div className="flex items-center justify-center w-full h-full min-h-screen p-3 sm:p-4">
          <div className="w-full max-w-2xl">
            <div className="p-5 sm:p-6 lg:p-8 rounded-lg sm:rounded-xl bg-dark-secondary/80 backdrop-blur-sm border border-dark-border/50 shadow-2xl">
              <OnboardingSteps
                initialData={onboardingData}
                onComplete={handleOnboardingComplete}
                onBack={() => setShowOnboarding(false)}
                startStep={1}
              />
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
      </div>
    );
  }

  // Форма добавления бизнеса (этап 0) - в стиле онбординга
  return (
    <div className="flex min-h-screen w-full bg-dark-primary relative overflow-hidden">
      <div className="flex items-center justify-center w-full h-full min-h-screen p-3 sm:p-4">
        <div className="w-full max-w-2xl">
          <div className="p-5 sm:p-6 lg:p-8 rounded-lg sm:rounded-xl bg-dark-secondary/80 backdrop-blur-sm border border-dark-border/50 shadow-2xl">
            <OnboardingSteps
              key={`business-form-${showOnboarding}`}
              initialData={showOnboarding ? onboardingData : {}}
              onComplete={handleBusinessFormComplete}
              onBack={() => navigate('/register')}
              startStep={0}
            />
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
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusinessRegistrationPage;
