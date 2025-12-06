import React from 'react';
import { FaFilePdf, FaFileWord, FaFileAlt, FaFile } from 'react-icons/fa';

export type FileType = 'pdf' | 'doc' | 'docx' | 'txt' | 'image' | 'unknown';

export interface FileInfo {
  type: FileType;
  name: string;
  iconName: 'pdf' | 'word' | 'txt' | 'unknown';
  color: string;
}

/**
 * Определяет тип файла по его имени
 */
export const getFileType = (filename: string): FileType => {
  const lowerName = filename.toLowerCase();
  
  if (lowerName.endsWith('.pdf')) return 'pdf';
  if (lowerName.endsWith('.docx')) return 'docx';
  if (lowerName.endsWith('.doc')) return 'doc';
  if (lowerName.endsWith('.txt') || lowerName.endsWith('.md')) return 'txt';
  if (/\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(lowerName)) return 'image';
  
  return 'unknown';
};

/**
 * Получает информацию о файле (тип, иконка, цвет)
 */
export const getFileInfo = (filename: string): FileInfo => {
  const type = getFileType(filename);
  
  switch (type) {
    case 'pdf':
      return {
        type: 'pdf',
        name: filename,
        iconName: 'pdf',
        color: 'text-red-500'
      };
    case 'doc':
    case 'docx':
      return {
        type: 'docx',
        name: filename,
        iconName: 'word',
        color: 'text-blue-500'
      };
    case 'txt':
      return {
        type: 'txt',
        name: filename,
        iconName: 'txt',
        color: 'text-gray-400'
      };
    default:
      return {
        type: 'unknown',
        name: filename,
        iconName: 'unknown',
        color: 'text-gray-400'
      };
  }
};

/**
 * Рендерит иконку файла на основе iconName
 */
export const renderFileIcon = (iconName: string, className: string) => {
  switch (iconName) {
    case 'pdf':
      // @ts-ignore - react-icons type compatibility
      return <FaFilePdf className={className} />;
    case 'word':
      // @ts-ignore - react-icons type compatibility
      return <FaFileWord className={className} />;
    case 'txt':
      // @ts-ignore - react-icons type compatibility
      return <FaFileAlt className={className} />;
    default:
      // @ts-ignore - react-icons type compatibility
      return <FaFile className={className} />;
  }
};

/**
 * Проверяет, является ли файл документом (PDF, DOC, DOCX, TXT)
 */
export const isDocumentFile = (filename: string): boolean => {
  const type = getFileType(filename);
  return type === 'pdf' || type === 'doc' || type === 'docx' || type === 'txt';
};

/**
 * Проверяет, является ли файл изображением
 */
export const isImageFile = (filename: string): boolean => {
  return getFileType(filename) === 'image';
};

