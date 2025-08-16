'use client'

import * as React from "react"
import { createContext, useContext, useState, useCallback } from "react"
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react"
import { cn } from "@/lib/utils"

interface Toast {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'destructive' | 'success' | 'warning' | 'info'
  duration?: number
}

interface ToastContextType {
  toasts: Toast[]
  toast: (toast: Omit<Toast, 'id'>) => void
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9)
    const newToast = { ...toast, id }
    
    setToasts((prev) => [...prev, newToast])

    // Auto dismiss after duration (default 5 seconds)
    const duration = toast.duration ?? 5000
    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, duration)
    }
  }, [])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss }}>
      {children}
      <Toaster />
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

function Toaster() {
  const { toasts, dismiss } = useToast()

  const getIcon = (variant?: string) => {
    switch (variant) {
      case 'success':
        return <CheckCircle className="h-4 w-4" />
      case 'destructive':
        return <AlertCircle className="h-4 w-4" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />
      case 'info':
        return <Info className="h-4 w-4" />
      default:
        return <Info className="h-4 w-4" />
    }
  }

  const getVariantStyles = (variant?: string) => {
    switch (variant) {
      case 'success':
        return 'border-green-200 bg-green-50 text-green-900'
      case 'destructive':
        return 'border-red-200 bg-red-50 text-red-900'
      case 'warning':
        return 'border-yellow-200 bg-yellow-50 text-yellow-900'
      case 'info':
        return 'border-blue-200 bg-blue-50 text-blue-900'
      default:
        return 'border-gray-200 bg-white text-gray-900'
    }
  }

  if (toasts.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 w-full max-w-sm space-y-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "relative flex w-full items-start gap-3 rounded-lg border p-4 shadow-lg transition-all",
            getVariantStyles(toast.variant)
          )}
        >
          <div className="flex-shrink-0">
            {getIcon(toast.variant)}
          </div>
          <div className="flex-1 min-w-0">
            {toast.title && (
              <div className="font-medium text-sm mb-1">{toast.title}</div>
            )}
            {toast.description && (
              <div className="text-sm opacity-90">{toast.description}</div>
            )}
          </div>
          <button
            onClick={() => dismiss(toast.id)}
            className="flex-shrink-0 ml-2 p-1 rounded-md hover:bg-black/10 transition-colors"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      ))}
    </div>
  )
}

// Convenience functions
export const toast = {
  success: (title: string, description?: string) => {
    const { toast } = useToast()
    toast({ title, description, variant: 'success' })
  },
  error: (title: string, description?: string) => {
    const { toast } = useToast()
    toast({ title, description, variant: 'destructive' })
  },
  warning: (title: string, description?: string) => {
    const { toast } = useToast()
    toast({ title, description, variant: 'warning' })
  },
  info: (title: string, description?: string) => {
    const { toast } = useToast()
    toast({ title, description, variant: 'info' })
  },
}

export { Toaster }