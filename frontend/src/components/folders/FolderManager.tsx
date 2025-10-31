// frontend/src/components/folders/FolderManager.tsx
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import {
  Folder,
  Plus,
  Edit2,
  Trash2,
  Check,
  X,
  FolderOpen,
  Star
} from 'lucide-react'

interface Folder {
  id: string
  name: string
  color: string
  icon: string
  transcription_count: number
}

interface FolderManagerProps {
  onSelectFolder?: (folderId: string | null) => void
  selectedFolderId?: string | null
  compact?: boolean
}

const FOLDER_COLORS = [
  { color: '#3B82F6', name: 'Blue' },
  { color: '#10B981', name: 'Green' },
  { color: '#F59E0B', name: 'Orange' },
  { color: '#EF4444', name: 'Red' },
  { color: '#8B5CF6', name: 'Purple' },
  { color: '#EC4899', name: 'Pink' },
  { color: '#06B6D4', name: 'Cyan' },
  { color: '#6B7280', name: 'Gray' }
]

export function FolderManager({ onSelectFolder, selectedFolderId, compact = false }: FolderManagerProps) {
  const { token } = useAuth()
  const [folders, setFolders] = useState<Folder[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [newFolderName, setNewFolderName] = useState('')
  const [selectedColor, setSelectedColor] = useState(FOLDER_COLORS[0].color)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      fetchFolders()
    }
  }, [token])

  const fetchFolders = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/folders`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setFolders(data.folders)
      }
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    } finally {
      setLoading(false)
    }
  }

  const createFolder = async () => {
    if (!newFolderName.trim()) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/folders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newFolderName,
          color: selectedColor,
          icon: 'folder'
        }),
      })

      if (response.ok) {
        const newFolder = await response.json()
        setFolders([...folders, newFolder])
        setNewFolderName('')
        setIsCreating(false)
        setSelectedColor(FOLDER_COLORS[0].color)
      }
    } catch (error) {
      console.error('Failed to create folder:', error)
    }
  }

  const updateFolder = async (folderId: string, name: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/folders/${folderId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name }),
      })

      if (response.ok) {
        setFolders(folders.map(f =>
          f.id === folderId ? { ...f, name } : f
        ))
        setEditingId(null)
      }
    } catch (error) {
      console.error('Failed to update folder:', error)
    }
  }

  const deleteFolder = async (folderId: string) => {
    if (!confirm('Are you sure you want to delete this folder? Transcriptions will not be deleted.')) {
      return
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/folders/${folderId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        setFolders(folders.filter(f => f.id !== folderId))
        if (selectedFolderId === folderId) {
          onSelectFolder?.(null)
        }
      }
    } catch (error) {
      console.error('Failed to delete folder:', error)
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {/* All Transcriptions */}
      <button
        onClick={() => onSelectFolder?.(null)}
        className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
          selectedFolderId === null
            ? 'bg-blue-50 text-blue-600'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
      >
        <FolderOpen className="w-5 h-5" />
        <span className="flex-1 text-left font-medium">All Transcriptions</span>
      </button>

      {/* Favorites */}
      <button
        onClick={() => onSelectFolder?.('favorites')}
        className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
          selectedFolderId === 'favorites'
            ? 'bg-yellow-50 text-yellow-600'
            : 'hover:bg-gray-100 text-gray-700'
        }`}
      >
        <Star className="w-5 h-5" />
        <span className="flex-1 text-left font-medium">Favorites</span>
      </button>

      {!compact && <div className="border-t my-2" />}

      {/* User Folders */}
      {folders.map((folder) => (
        <div key={folder.id} className="group relative">
          {editingId === folder.id ? (
            <div className="flex items-center space-x-2 px-3 py-2">
              <Input
                autoFocus
                defaultValue={folder.name}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    updateFolder(folder.id, e.currentTarget.value)
                  } else if (e.key === 'Escape') {
                    setEditingId(null)
                  }
                }}
                className="flex-1 h-8"
              />
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setEditingId(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <button
              onClick={() => onSelectFolder?.(folder.id)}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                selectedFolderId === folder.id
                  ? 'bg-gray-100 text-gray-900'
                  : 'hover:bg-gray-50 text-gray-700'
              }`}
            >
              <Folder className="w-5 h-5" style={{ color: folder.color }} />
              <span className="flex-1 text-left font-medium">{folder.name}</span>
              {folder.transcription_count > 0 && (
                <span className="text-xs text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full">
                  {folder.transcription_count}
                </span>
              )}

              {/* Actions (visible on hover) */}
              {!compact && (
                <div className="opacity-0 group-hover:opacity-100 flex items-center space-x-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditingId(folder.id)
                    }}
                    className="h-7 w-7 p-0"
                  >
                    <Edit2 className="w-3 h-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation()
                      deleteFolder(folder.id)
                    }}
                    className="h-7 w-7 p-0 hover:bg-red-50 hover:text-red-600"
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              )}
            </button>
          )}
        </div>
      ))}

      {/* Create New Folder - DISABLED per user request */}
      {/* User requested to remove folder creation functionality */}
    </div>
  )
}
