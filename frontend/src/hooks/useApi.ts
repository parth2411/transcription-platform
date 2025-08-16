// frontend/src/hooks/useApi.ts
import { useState, useCallback } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'

interface UseApiOptions {
  onSuccess?: (data: any) => void
  onError?: (error: string) => void
}

export function useApi() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const request = useCallback(async (
    endpoint: string,
    options: RequestInit = {},
    apiOptions: UseApiOptions = {}
  ) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
          ...options.headers,
        },
        ...options,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Request failed')
      }

      const data = await response.json()
      apiOptions.onSuccess?.(data)
      return data
    } catch (err: any) {
      const errorMessage = err.message || 'An error occurred'
      setError(errorMessage)
      apiOptions.onError?.(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [token])

  return { request, loading, error }
}
