import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AuthLayout from '../components/AuthLayout';
import MultiStepRegisterForm from '../components/MultiStepRegisterForm';

const RegisterPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  
  // Проверяем флаг регистрации для предотвращения редиректа
  const hasRegistrationFlag = localStorage.getItem('registrationInProcess') === 'true';
  
  // Перенаправляем только если пользователь авторизован И не в процессе регистрации
  if (isAuthenticated && !hasRegistrationFlag) {
    return <Navigate to="/chat" replace />;
  }

  return (
    <AuthLayout 
      title="Создайте аккаунт"
      subtitle="Заполните данные для быстрой регистрации"
    >
      <MultiStepRegisterForm />
    </AuthLayout>
  );
};

export default RegisterPage;
