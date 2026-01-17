import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { Modal } from './modal';
import { InputModal } from './input-modal';
import { ToastContainer, ToastType } from './toast';

interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
  onRedirect?: () => void;
  redirectDelay?: number;
}

interface ModalState {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  onConfirm: (() => void) | null;
  variant?: 'default' | 'danger';
}

interface InputModalState {
  isOpen: boolean;
  title: string;
  label: string;
  placeholder?: string;
  defaultValue?: string;
  type?: 'text' | 'email';
  onConfirm: ((value: string) => void) | null;
}

interface ModalContextType {
  showModal: (config: Omit<ModalState, 'isOpen'>) => Promise<boolean>;
  showInput: (config: Omit<InputModalState, 'isOpen' | 'onConfirm'>) => Promise<string | null>;
  showToast: (
    message: string,
    type?: ToastType,
    options?: { duration?: number; onRedirect?: () => void; redirectDelay?: number },
  ) => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const useModal = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModal must be used within ModalProvider');
  }
  return context;
};

export const ModalProvider = ({ children }: { children: ReactNode }) => {
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
  });
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showModal = useCallback(
    (config: Omit<ModalState, 'isOpen'>): Promise<boolean> => {
      return new Promise((resolve) => {
        setModalState({
          ...config,
          isOpen: true,
          onConfirm: () => {
            if (config.onConfirm) {
              config.onConfirm();
            }
            resolve(true);
          },
        });
      });
    },
    [],
  );

  const closeModal = useCallback(() => {
    setModalState((prev) => ({ ...prev, isOpen: false, onConfirm: null }));
  }, []);

  const showToast = useCallback(
    (
      message: string,
      type: ToastType = 'info',
      options?: { duration?: number; onRedirect?: () => void; redirectDelay?: number },
    ) => {
      const id = Math.random().toString(36).substring(7);
      setToasts((prev) => [
        ...prev,
        {
          id,
          message,
          type,
          duration: options?.duration,
          onRedirect: options?.onRedirect,
          redirectDelay: options?.redirectDelay,
        },
      ]);
    },
    [],
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const handleModalConfirm = useCallback(() => {
    if (modalState.onConfirm) {
      modalState.onConfirm();
    }
    closeModal();
  }, [modalState.onConfirm, closeModal]);

  return (
    <ModalContext.Provider value={{ showModal, showToast }}>
      {children}
      <Modal
        isOpen={modalState.isOpen}
        onClose={closeModal}
        title={modalState.title}
        message={modalState.message}
        confirmText={modalState.confirmText}
        cancelText={modalState.cancelText}
        onConfirm={handleModalConfirm}
        variant={modalState.variant}
      />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ModalContext.Provider>
  );
};

