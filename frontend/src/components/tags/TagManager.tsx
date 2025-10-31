// frontend/src/components/tags/TagManager.tsx
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Plus, X, Tag as TagIcon } from 'lucide-react'

interface Tag {
  id: string
  name: string
  color: string
  usage_count: number
}

interface TagManagerProps {
  transcriptionId?: string
  selectedTags?: string[]
  onTagsChange?: (tagIds: string[]) => void
  mode?: 'select' | 'manage'
}

const TAG_COLORS = [
  '#6B7280', '#EF4444', '#F59E0B', '#10B981',
  '#3B82F6', '#8B5CF6', '#EC4899', '#06B6D4'
]

export function TagManager({
  transcriptionId,
  selectedTags = [],
  onTagsChange,
  mode = 'select'
}: TagManagerProps) {
  const { token } = useAuth()
  const [tags, setTags] = useState<Tag[]>([])
  const [isCreating, setIsCreating] = useState(false)
  const [newTagName, setNewTagName] = useState('')
  const [selectedColor, setSelectedColor] = useState(TAG_COLORS[0])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      fetchTags()
    }
  }, [token])

  const fetchTags = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tags`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setTags(data.tags)
      }
    } catch (error) {
      console.error('Failed to fetch tags:', error)
    } finally {
      setLoading(false)
    }
  }

  const createTag = async () => {
    if (!newTagName.trim()) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tags`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newTagName,
          color: selectedColor
        }),
      })

      if (response.ok) {
        const newTag = await response.json()
        setTags([...tags, { ...newTag, usage_count: 0 }])

        // Auto-add to transcription if in select mode
        if (mode === 'select' && transcriptionId) {
          await addTagToTranscription(newTag.id)
          onTagsChange?.([...selectedTags, newTag.id])
        }

        setNewTagName('')
        setIsCreating(false)
        setSelectedColor(TAG_COLORS[0])
      }
    } catch (error) {
      console.error('Failed to create tag:', error)
    }
  }

  const addTagToTranscription = async (tagId: string) => {
    if (!transcriptionId) return

    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${transcriptionId}/tags/${tagId}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )
    } catch (error) {
      console.error('Failed to add tag:', error)
    }
  }

  const removeTagFromTranscription = async (tagId: string) => {
    if (!transcriptionId) return

    try {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${transcriptionId}/tags/${tagId}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )
    } catch (error) {
      console.error('Failed to remove tag:', error)
    }
  }

  const toggleTag = async (tagId: string) => {
    const isSelected = selectedTags.includes(tagId)

    if (isSelected) {
      await removeTagFromTranscription(tagId)
      onTagsChange?.(selectedTags.filter(id => id !== tagId))
    } else {
      await addTagToTranscription(tagId)
      onTagsChange?.([...selectedTags, tagId])
    }
  }

  if (loading) {
    return (
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="h-6 w-16 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {/* Existing Tags */}
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => {
          const isSelected = selectedTags.includes(tag.id)

          return (
            <button
              key={tag.id}
              onClick={() => mode === 'select' && toggleTag(tag.id)}
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-all ${
                mode === 'select'
                  ? isSelected
                    ? 'ring-2 ring-offset-1'
                    : 'hover:opacity-80'
                  : 'cursor-default'
              }`}
              style={{
                backgroundColor: `${tag.color}20`,
                color: tag.color,
                ringColor: isSelected ? tag.color : 'transparent'
              }}
            >
              <TagIcon className="w-3 h-3 mr-1" />
              {tag.name}
              {mode === 'manage' && tag.usage_count > 0 && (
                <span className="ml-2 text-xs opacity-60">
                  {tag.usage_count}
                </span>
              )}
            </button>
          )
        })}

        {/* Create New Tag Inline */}
        {!isCreating && (
          <button
            onClick={() => setIsCreating(true)}
            className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border-2 border-dashed border-gray-300 text-gray-600 hover:border-gray-400 hover:text-gray-700 transition-colors"
          >
            <Plus className="w-3 h-3 mr-1" />
            New Tag
          </button>
        )}
      </div>

      {/* Create New Tag Form */}
      {isCreating && (
        <div className="flex items-center space-x-2 p-3 bg-gray-50 rounded-lg">
          <Input
            autoFocus
            placeholder="Tag name"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') createTag()
              if (e.key === 'Escape') {
                setIsCreating(false)
                setNewTagName('')
              }
            }}
            className="flex-1 h-8"
          />

          <div className="flex gap-1">
            {TAG_COLORS.map((color) => (
              <button
                key={color}
                onClick={() => setSelectedColor(color)}
                className={`w-5 h-5 rounded-full border transition-all ${
                  selectedColor === color
                    ? 'border-gray-900 scale-110'
                    : 'border-gray-200 hover:scale-105'
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>

          <Button onClick={createTag} size="sm" className="h-8">
            Create
          </Button>
          <Button
            onClick={() => {
              setIsCreating(false)
              setNewTagName('')
            }}
            size="sm"
            variant="ghost"
            className="h-8"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}

      {tags.length === 0 && !isCreating && (
        <div className="text-center py-4 text-gray-500 text-sm">
          No tags yet. Create your first tag to organize transcriptions.
        </div>
      )}
    </div>
  )
}

// Simple Tag Display Component
export function TagBadges({ tagIds, tags }: { tagIds: string[]; tags: Tag[] }) {
  if (!tagIds || tagIds.length === 0) return null

  return (
    <div className="flex flex-wrap gap-1">
      {tagIds.map((tagId) => {
        const tag = tags.find(t => t.id === tagId)
        if (!tag) return null

        return (
          <Badge
            key={tag.id}
            variant="secondary"
            style={{
              backgroundColor: `${tag.color}20`,
              color: tag.color,
              borderColor: tag.color
            }}
            className="text-xs"
          >
            {tag.name}
          </Badge>
        )
      })}
    </div>
  )
}
