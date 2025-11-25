// frontend/src/app/transcriptions/enhanced-page.tsx
// Enhanced transcriptions page with folders, tags, and advanced features
// Replace the content of page.tsx with this file

'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { FolderManager } from '@/components/folders/FolderManager'
import { TagManager, TagBadges } from '@/components/tags/TagManager'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Search,
  Filter,
  Plus,
  Play,
  Download,
  Trash2,
  Clock,
  FileAudio,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Star,
  MoreVertical,
  FolderInput,
  Tag as TagIcon,
  Grid3X3,
  List
} from 'lucide-react'
import Link from 'next/link'

interface Transcription {
  id: string
  title: string
  status: string
  file_type?: string
  file_size?: number
  duration_seconds?: number
  created_at: string
  transcription_text?: string
  folder_id?: string
  is_favorite?: boolean
  tags?: string[]
}

interface TranscriptionList {
  transcriptions: Transcription[]
  total: number
  page: number
  per_page: number
}

interface Tag {
  id: string
  name: string
  color: string
}

export default function EnhancedTranscriptionsPage() {
  const { token } = useAuth()
  const [data, setData] = useState<TranscriptionList | null>(null)
  const [tags, setTags] = useState<Tag[]>([])
  const [folders, setFolders] = useState<Array<{id: string, name: string}>>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>('all')
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedTranscriptions, setSelectedTranscriptions] = useState<string[]>([])
  const perPage = 12

  useEffect(() => {
    if (!token) return
    fetchTranscriptions()
    fetchTags()
    fetchFolders()
  }, [token, currentPage, statusFilter, sourceTypeFilter, selectedFolder])

  const fetchTranscriptions = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: perPage.toString(),
        ...(statusFilter !== 'all' && { status_filter: statusFilter }),
        ...(sourceTypeFilter !== 'all' && { source_type: sourceTypeFilter }),
        ...(selectedFolder && selectedFolder !== 'favorites' && { folder_id: selectedFolder })
      })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions?${params}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()

        // Filter favorites if needed
        if (selectedFolder === 'favorites') {
          result.transcriptions = result.transcriptions.filter((t: Transcription) => t.is_favorite)
        }

        setData(result)
      }
    } catch (error) {
      console.error('Failed to fetch transcriptions:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchTags = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tags`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setTags(result.tags)
      }
    } catch (error) {
      console.error('Failed to fetch tags:', error)
    }
  }

  const fetchFolders = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/folders`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setFolders(result.folders)
      }
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    }
  }

  const toggleFavorite = async (id: string, currentValue: boolean) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_favorite: !currentValue }),
      })

      fetchTranscriptions()
    } catch (error) {
      console.error('Failed to toggle favorite:', error)
    }
  }

  const moveToFolder = async (transcriptionId: string, folderId: string | null) => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${transcriptionId}/folder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ folder_id: folderId }),
      })

      fetchTranscriptions()
    } catch (error) {
      console.error('Failed to move to folder:', error)
    }
  }

  const deleteTranscription = async (id: string) => {
    if (!confirm('Are you sure you want to delete this transcription?')) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        fetchTranscriptions()
      }
    } catch (error) {
      console.error('Failed to delete transcription:', error)
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'processing':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredTranscriptions = data?.transcriptions.filter(t =>
    t.title.toLowerCase().includes(search.toLowerCase())
  ) || []

  const totalPages = data ? Math.ceil(data.total / perPage) : 0

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Transcriptions</h1>
            <p className="text-gray-600 mt-1">{data?.total || 0} total transcriptions</p>
          </div>
          <Link href="/transcriptions/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New
            </Button>
          </Link>
        </div>

        {/* Search and Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <Input
                    placeholder="Search transcriptions..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="flex gap-2 flex-wrap">
                {/* Category Filter */}
                <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setSourceTypeFilter('all')}
                    className={`px-4 py-2 text-sm font-medium ${sourceTypeFilter === 'all' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setSourceTypeFilter('meeting')}
                    className={`px-4 py-2 text-sm font-medium border-l ${sourceTypeFilter === 'meeting' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    Meetings
                  </button>
                  <button
                    onClick={() => setSourceTypeFilter('upload')}
                    className={`px-4 py-2 text-sm font-medium border-l ${sourceTypeFilter === 'upload' ? 'bg-blue-50 text-blue-600 border-b-2 border-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    Uploads
                  </button>
                </div>

                {/* Folder Filter */}
                <select
                  value={selectedFolder || ''}
                  onChange={(e) => setSelectedFolder(e.target.value || null)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">All Folders</option>
                  <option value="favorites">Favorites</option>
                  {folders.map((folder) => (
                    <option key={folder.id} value={folder.id}>
                      {folder.name}
                    </option>
                  ))}
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>

                <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`px-3 py-2 ${viewMode === 'grid' ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    <Grid3X3 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`px-3 py-2 border-l ${viewMode === 'list' ? 'bg-blue-50 text-blue-600' : 'text-gray-600 hover:bg-gray-50'}`}
                  >
                    <List className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

          {/* Transcriptions */}
          {loading ? (
            <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4' : 'space-y-4'}>
              {[...Array(6)].map((_, i) => (
                <Card key={i} className="animate-pulse">
                  <CardContent className="pt-6">
                    <div className="space-y-3">
                      <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredTranscriptions.length > 0 ? (
            <>
              {viewMode === 'grid' ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredTranscriptions.map((transcription) => (
                    <Card key={transcription.id} className="hover:shadow-lg transition-shadow group">
                      <CardContent className="pt-6">
                        <div className="space-y-3">
                          {/* Header with favorite */}
                          <div className="flex items-start justify-between">
                            <Link href={`/transcriptions/${transcription.id}`} className="flex-1">
                              <h3 className="font-semibold text-gray-900 line-clamp-2 hover:text-blue-600">
                                {transcription.title}
                              </h3>
                            </Link>
                            <button
                              onClick={() => toggleFavorite(transcription.id, transcription.is_favorite || false)}
                              className="p-1 hover:bg-gray-100 rounded"
                            >
                              <Star
                                className={`w-4 h-4 ${transcription.is_favorite ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'}`}
                              />
                            </button>
                          </div>

                          {/* Status and Duration */}
                          <div className="flex items-center justify-between text-sm">
                            <Badge className={getStatusColor(transcription.status)}>
                              {transcription.status}
                            </Badge>
                            <div className="flex items-center text-gray-500">
                              <Clock className="w-3 h-3 mr-1" />
                              {formatDuration(transcription.duration_seconds)}
                            </div>
                          </div>

                          {/* Tags */}
                          {transcription.tags && transcription.tags.length > 0 && (
                            <TagBadges tagIds={transcription.tags} tags={tags} />
                          )}

                          {/* Date */}
                          <div className="flex items-center text-xs text-gray-500">
                            <Calendar className="w-3 h-3 mr-1" />
                            {new Date(transcription.created_at).toLocaleDateString()}
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2 pt-2 border-t opacity-0 group-hover:opacity-100 transition-opacity">
                            <Link href={`/transcriptions/${transcription.id}`} className="flex-1">
                              <Button size="sm" variant="outline" className="w-full">
                                <Play className="w-3 h-3 mr-1" />
                                View
                              </Button>
                            </Link>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => deleteTranscription(transcription.id)}
                              className="hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredTranscriptions.map((transcription) => (
                    <Card key={transcription.id} className="hover:bg-gray-50 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-center gap-4">
                          <button
                            onClick={() => toggleFavorite(transcription.id, transcription.is_favorite || false)}
                            className="p-2 hover:bg-gray-100 rounded"
                          >
                            <Star
                              className={`w-4 h-4 ${transcription.is_favorite ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'}`}
                            />
                          </button>

                          <div className="flex-1">
                            <Link href={`/transcriptions/${transcription.id}`}>
                              <h3 className="font-medium text-gray-900 hover:text-blue-600">
                                {transcription.title}
                              </h3>
                            </Link>
                            <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                              <span className="flex items-center">
                                <Clock className="w-3 h-3 mr-1" />
                                {formatDuration(transcription.duration_seconds)}
                              </span>
                              <span>{new Date(transcription.created_at).toLocaleDateString()}</span>
                            </div>
                          </div>

                          <Badge className={getStatusColor(transcription.status)}>
                            {transcription.status}
                          </Badge>

                          <div className="flex items-center gap-2">
                            <Link href={`/transcriptions/${transcription.id}`}>
                              <Button size="sm" variant="outline">
                                <Play className="w-3 h-3 mr-1" />
                                View
                              </Button>
                            </Link>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => deleteTranscription(transcription.id)}
                              className="hover:bg-red-50 hover:text-red-600"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between">
                  <p className="text-sm text-gray-600">
                    Showing {(currentPage - 1) * perPage + 1} to{' '}
                    {Math.min(currentPage * perPage, data?.total || 0)} of {data?.total || 0} transcriptions
                  </p>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </Button>
                    <span className="text-sm text-gray-600">
                      Page {currentPage} of {totalPages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      disabled={currentPage === totalPages}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <Card>
              <CardContent className="py-12">
                <div className="text-center">
                  <FileAudio className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No transcriptions found</h3>
                  <p className="text-gray-600 mb-6">
                    {search ? 'Try adjusting your search or filters' : 'Get started by creating your first transcription'}
                  </p>
                  {!search && (
                    <Link href="/transcriptions/new">
                      <Button>
                        <Plus className="w-4 h-4 mr-2" />
                        New Transcription
                      </Button>
                    </Link>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
      </div>
    </DashboardLayout>
  )
}
