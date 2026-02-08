import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

interface InputModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  label: string;
  placeholder?: string;
  defaultValue?: string;
  type?: 'text' | 'email';
  onConfirm: (value: string) => void;
  confirmText?: string;
  cancelText?: string;
}

export const InputModal = ({
  isOpen,
  onClose,
  title,
  label,
  placeholder,
  defaultValue = '',
  type = 'text',
  onConfirm,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
}: InputModalProps) => {
  const [value, setValue] = useState(defaultValue);

  useEffect(() => {
    if (isOpen) {
      setValue(defaultValue);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen, defaultValue]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (value.trim()) {
      onConfirm(value.trim());
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConfirm();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="input-modal-title"
    >
      <div
        className="fixed inset-0 bg-slate-900/70 dark:bg-black/60 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
      />
      <div
        className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl dark:shadow-none dark:ring-1 dark:ring-slate-700 max-w-md w-full p-6 transform transition-all"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="pr-8 mb-6">
          <h3 id="input-modal-title" className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{title}</h3>
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            {label}
          </label>
          <input
            type={type}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-700/50 border border-slate-200 dark:border-slate-600 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
            autoFocus
          />
        </div>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-700 rounded-xl hover:bg-slate-200 dark:hover:bg-slate-600 transition"
          >
            {cancelText}
          </button>
          <button
            onClick={handleConfirm}
            disabled={!value.trim()}
            className={clsx(
              'px-4 py-2.5 text-sm font-semibold text-white rounded-xl transition shadow-lg',
              value.trim()
                ? 'bg-blue-600 hover:bg-blue-700 shadow-blue-600/20 dark:bg-blue-600 dark:hover:bg-blue-700'
                : 'bg-slate-300 dark:bg-slate-600 cursor-not-allowed',
            )}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};





