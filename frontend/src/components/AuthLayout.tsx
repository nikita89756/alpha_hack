import React, { ReactNode } from 'react';

interface AuthLayoutProps {
  children: ReactNode;
  title: string;
  subtitle: string;
  cardWidth?: 'md' | '2xl';
}

const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle, cardWidth = 'md' }) => {
  const maxWidthClass = cardWidth === '2xl' ? 'max-w-2xl' : 'max-w-md';
  
  return (
    <div className="flex min-h-screen w-full bg-dark-primary relative overflow-hidden">
      {/* Центральный контейнер */}
      <div className="flex items-center justify-center w-full h-full min-h-screen p-3 sm:p-4">
        <div className={`w-full ${maxWidthClass}`}>
          <div className="p-5 sm:p-6 lg:p-8 rounded-lg sm:rounded-xl bg-dark-secondary/80 backdrop-blur-sm border border-dark-border/50 shadow-2xl">
            {title && (
              <div className="mb-4 sm:mb-6 text-center">
                <h1 className="text-xl sm:text-2xl font-semibold text-white mb-2">{title}</h1>
                {subtitle && <p className="text-gray-400 text-xs sm:text-sm">{subtitle}</p>}
              </div>
            )}
            {children}
          </div>
          
          <div className="mt-4 sm:mt-6 text-center">
            <p className="text-[10px] sm:text-xs text-gray-500">
              Техническая поддержка: <a href="mailto:support@alfabank.ru" className="text-custom-blue hover:underline transition-colors">support@alfabank.ru</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
