import React, { useState } from 'react';
import { BusinessCreate } from '../types';
import { businessService } from '../services/api';

interface BusinessFormProps {
  onBusinessAdded: (business: BusinessCreate) => void;
  onSkip: () => void;
  isLoading?: boolean;
  skipButtonText?: string;
}

const BusinessForm: React.FC<BusinessFormProps> = ({ onBusinessAdded, onSkip, isLoading = false, skipButtonText = 'Пропустить' }) => {
  const [formData, setFormData] = useState<BusinessCreate>({
    name: '',
    description: '',
    industry: null,
  });
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value || null }));
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.name.trim()) {
      setError('Название бизнеса обязательно');
      return;
    }

    if (!formData.description.trim()) {
      setError('Описание бизнеса обязательно');
      return;
    }

    setIsSubmitting(true);
    try {
      await onBusinessAdded(formData);
      // Сбрасываем форму после успешного добавления
      setFormData({
        name: '',
        description: '',
        industry: null,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.error || 'Ошибка при добавлении бизнеса');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      {error && (
        <div className="p-4 text-sm text-red-500 bg-dark-accent/50 rounded-lg border border-red-500/50 animate-fade-in mb-4 backdrop-blur-sm">
          <div className="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-500 mr-2 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span>{error}</span>
          </div>
        </div>
      )}

      <div className="space-y-4">
        <div className="relative">
          <label htmlFor="name" className="block text-sm font-medium text-gray-300 mb-1.5">
            Название бизнеса <span className="text-red-500">*</span>
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm3 1h6v4H7V5zm6 6H7v2h6v-2z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="name"
              name="name"
              type="text"
              required
              value={formData.name}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Введите название вашего бизнеса"
            />
          </div>
        </div>

        <div className="relative">
          <label htmlFor="description" className="block text-sm font-medium text-gray-300 mb-1.5">
            Описание бизнеса <span className="text-red-500">*</span>
          </label>
          <textarea
            id="description"
            name="description"
            required
            rows={4}
            value={formData.description}
            onChange={handleChange}
            className="w-full px-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500 resize-none"
            placeholder="Опишите ваш бизнес"
          />
        </div>

        <div className="relative">
          <label htmlFor="industry" className="block text-sm font-medium text-gray-300 mb-1.5">
            Отрасль <span className="text-gray-500 text-xs">(необязательно)</span>
          </label>
          <div className="group relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-custom-blue transition-colors" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 5a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2h-2.22l.123.489.804.804A1 1 0 0113 18H7a1 1 0 01-.707-1.707l.804-.804L7.22 15H5a2 2 0 01-2-2V5zm5.771 7H5V5h10v7H8.771z" clipRule="evenodd" />
              </svg>
            </div>
            <input
              id="industry"
              name="industry"
              type="text"
              value={formData.industry || ''}
              onChange={handleChange}
              className="w-full pl-11 pr-4 py-3 text-white bg-dark-accent/70 border border-custom-border/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:border-custom-blue/50 transition-all duration-200 placeholder-gray-500"
              placeholder="Например: Розничная торговля, IT, Услуги"
            />
          </div>
        </div>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          type="submit"
          disabled={isLoading || isSubmitting}
          className="flex-1 px-4 py-2.5 text-white bg-dark-accent border border-custom-border rounded-md hover:bg-dark-secondary hover:border-custom-blue focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:ring-offset-1 focus:ring-offset-dark-secondary disabled:opacity-50 transition-all duration-200 shadow-md hover:shadow-[0_0_10px_rgba(59,130,246,0.3)] font-medium tracking-wide text-base relative"
        >
          <span className="relative z-10 whitespace-nowrap">
            {isLoading || isSubmitting ? (
              <div className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Добавление...
              </div>
            ) : 'Добавить бизнес'}
          </span>
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="px-4 py-2.5 text-gray-300 bg-dark-accent/50 border border-custom-border/50 rounded-md hover:bg-dark-accent hover:text-white focus:outline-none focus:ring-2 focus:ring-custom-blue/50 focus:ring-offset-1 focus:ring-offset-dark-secondary transition-all duration-200 font-medium"
        >
          {skipButtonText}
        </button>
      </div>
    </form>
  );
};

export default BusinessForm;

