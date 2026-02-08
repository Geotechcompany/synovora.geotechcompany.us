import { useEffect } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: () => void;
  variant?: 'default' | 'danger';
}

export const Modal = ({
  isOpen,
  onClose,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  onConfirm,
  variant = 'default',
}: ModalProps) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className="fixed inset-0 bg-slate-900/70 dark:bg-black/60 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
      />
      <div
        className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl dark:shadow-none dark:ring-1 dark:ring-slate-700 max-w-md w-full p-6 transform transition-all duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="pr-8">
          <h3 id="modal-title" className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{title}</h3>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{message}</p>
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
            className={clsx(
              'px-4 py-2.5 text-sm font-semibold text-white rounded-xl transition shadow-lg',
              variant === 'danger'
                ? 'bg-rose-600 hover:bg-rose-700 shadow-rose-600/20 dark:bg-rose-600 dark:hover:bg-rose-700'
                : 'bg-blue-600 hover:bg-blue-700 shadow-blue-600/20 dark:bg-blue-600 dark:hover:bg-blue-700',
            )}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
};





