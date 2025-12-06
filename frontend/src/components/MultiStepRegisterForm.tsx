import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const MultiStepRegisterForm: React.FC = () => {
  const navigate = useNavigate();
  
  const [formData, setFormData] = useState({
    username: '',
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [formError, setFormError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setFormError(null);
  };

  const validateEmail = (email: string): boolean => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    setFormError(null);
    
    if (!formData.username || !formData.email || !formData.password || !formData.confirmPassword) {
      setFormError('Пожалуйста, заполните все обязательные поля');
      return;
    }
    
    if (formData.username.length < 3) {
      setFormError('Имя пользователя должно содержать не менее 3 символов');
      return;
    }
    
    if (!validateEmail(formData.email)) {
      setFormError('Пожалуйста, введите корректный email');
      return;
    }
    
    if (formData.password !== formData.confirmPassword) {
      setFormError('Пароли не совпадают');
      return;
    }
    
    if (formData.password.length < 6) {
      setFormError('Пароль должен содержать не менее 6 символов');
      return;
    }
    
    // Сохраняем данные регистрации во временное хранилище
    localStorage.setItem('pendingRegistration', JSON.stringify({
      username: formData.username,
      email: formData.email,
      password: formData.password,
      full_name: formData.full_name || undefined,
    }));
    
    // Устанавливаем флаг процесса регистрации
    localStorage.setItem('registrationInProcess', 'true');
    
    // Переходим на страницу добавления бизнесов (без создания аккаунта)
    navigate('/register/business');
  };

  return (
    <form className="space-y-5" onSubmit={handleRegisterSubmit}>
      {formError && (
        <div className="p-4 text-sm text-red-500 bg-dark-accent/50 rounded-lg border border-red-500/50 animate-fade-in mb-4 backdrop-blur-sm">
          <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{formError}</span>
          </div>
        </div>
      )}
      
      <div className="space-y-4">
        <div className="relative">
          <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-1.5">
            Имя пользователя <span className="text-red-500">*</span>
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="username"
              name="username"
              type="text"
              required
              value={formData.username}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Введите имя пользователя"
            />
          </div>
          <p className="text-xs text-gray-500 mt-1 ml-1">Минимум 3 символа</p>
        </div>
        
        <div className="relative">
          <label htmlFor="full_name" className="block text-sm font-medium text-gray-300 mb-1.5">
            Полное имя <span className="text-gray-500 text-xs">(необязательно)</span>
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="full_name"
              name="full_name"
              type="text"
              value={formData.full_name}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Введите ваше полное имя"
            />
          </div>
        </div>
        
        <div className="relative">
          <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1.5">
            Email
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
                <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
              </svg>
            </div>
            <input
              id="email"
              name="email"
              type="email"
              required
              value={formData.email}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Введите ваш email"
            />
          </div>
        </div>
        
        <div className="relative">
          <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1.5">
            Пароль
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="password"
              name="password"
              type="password"
              required
              value={formData.password}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Введите пароль"
            />
          </div>
          <p className="text-xs text-gray-500 mt-1 ml-1">Минимум 6 символов</p>
        </div>
        
        <div className="relative">
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-1.5">
            Подтверждение пароля
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              value={formData.confirmPassword}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Подтвердите пароль"
            />
          </div>
        </div>
      </div>
      
      <div className="pt-2">
        <button
          type="submit"
          className="w-full px-4 py-2.5 text-white bg-dark-accent border border-custom-border rounded-md hover:bg-dark-secondary hover:border-custom-blue focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:ring-offset-1 focus:ring-offset-dark-secondary transition-all duration-200 shadow-md hover:shadow-[0_0_10px_rgba(59,130,246,0.3)] font-medium tracking-wide text-base relative"
        >
          <span className="relative z-10 whitespace-nowrap">Далее</span>
        </button>
      </div>
      
      <div className="text-center text-sm pt-4">
        <span className="text-gray-400">Уже есть аккаунт? </span>
        <Link to="/login" className="text-custom-blue hover:text-custom-blue/80 transition-colors focus:outline-none font-medium">
          Войти
        </Link>
      </div>
    </form>
  );
};

export default MultiStepRegisterForm;
