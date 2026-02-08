import { createContext, useContext, useState, useCallback, useRef } from 'react';
import type { ReactNode } from 'react';
import { Modal } from './modal';
import { InputModal } from './input-modal';
import { ToastContainer } from './toast';
import type { ToastType } from './toast';

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

const defaultModalState: ModalState = {
  isOpen: false,
  title: '',
  message: '',
  onConfirm: null,
};

const defaultInputModalState: InputModalState = {
  isOpen: false,
  title: '',
  label: '',
  onConfirm: null,
};

export const ModalProvider = ({ children }: { children: ReactNode }) => {
  const [modalState, setModalState] = useState<ModalState>(defaultModalState);
  const [inputModalState, setInputModalState] = useState<InputModalState>(defaultInputModalState);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const modalResolveRef = useRef<((value: boolean) => void) | null>(null);
  const inputResolveRef = useRef<((value: string | null) => void) | null>(null);

  const showModal = useCallback(
    (config: Omit<ModalState, 'isOpen'>): Promise<boolean> => {
      return new Promise((resolve) => {
        modalResolveRef.current = resolve;
        setModalState({
          ...config,
          isOpen: true,
          onConfirm: config.onConfirm,
        });
      });
    },
    [],
  );

  const closeModal = useCallback(() => {
    if (modalResolveRef.current) {
      modalResolveRef.current(false);
      modalResolveRef.current = null;
    }
    setModalState((prev) => ({ ...prev, isOpen: false, onConfirm: null }));
  }, []);

  const showInput = useCallback(
    (config: Omit<InputModalState, 'isOpen' | 'onConfirm'>): Promise<string | null> => {
      return new Promise((resolve) => {
        inputResolveRef.current = resolve;
        setInputModalState({
          ...config,
          isOpen: true,
          onConfirm: null,
        });
      });
    },
    [],
  );

  const closeInputModal = useCallback(() => {
    if (inputResolveRef.current) {
      inputResolveRef.current(null);
      inputResolveRef.current = null;
    }
    setInputModalState((prev) => ({ ...prev, isOpen: false, onConfirm: null }));
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
    modalState.onConfirm?.();
    if (modalResolveRef.current) {
      modalResolveRef.current(true);
      modalResolveRef.current = null;
    }
    setModalState((prev) => ({ ...prev, isOpen: false, onConfirm: null }));
  }, [modalState.onConfirm]);

  const handleInputConfirm = useCallback((value: string) => {
    if (inputResolveRef.current) {
      inputResolveRef.current(value);
      inputResolveRef.current = null;
    }
    setInputModalState((prev) => ({ ...prev, isOpen: false, onConfirm: null }));
  }, []);

  return (
    <ModalContext.Provider value={{ showModal, showToast, showInput }}>
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
      <InputModal
        isOpen={inputModalState.isOpen}
        onClose={closeInputModal}
        title={inputModalState.title}
        label={inputModalState.label}
        placeholder={inputModalState.placeholder}
        defaultValue={inputModalState.defaultValue}
        type={inputModalState.type}
        onConfirm={handleInputConfirm}
      />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ModalContext.Provider>
  );
};

