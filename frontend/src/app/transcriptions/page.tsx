// frontend/src/app/transcriptions/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
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
  ChevronRight
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
}

interface TranscriptionList {
  transcriptions: Transcription[]
  total: number
  page: number
  per_page: number
}

export default function TranscriptionLibraryPage() {
  const { token } = useAuth()
  const [data, setData] = useState<TranscriptionList | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const perPage = 10

  useEffect(() => {
    if (!token) return
    fetchTranscriptions()
  }, [token, currentPage, statusFilter])

  const fetchTranscriptions = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: perPage.toString(),
        ...(statusFilter !== 'all' && { status_filter: statusFilter })
      })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions?${params}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const result = await response.json()
        setData(result)
      }
    } catch (error) {
      console.error('Failed to fetch transcriptions:', error)
    } finally {
      setLoading(false)
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
        fetchTranscriptions() // Refresh the list
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

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const mb = bytes / 1024 / 1024
    return `${mb.toFixed(1)} MB`
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
      <div className="space-y-8">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Transcription Library</h1>
            <p className="text-gray-600 mt-2">Manage and search your transcriptions</p>
          </div>
          <Link href="/transcriptions/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              New Transcription
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
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
              <div className="flex gap-2">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="all">All Status</option>
                  <option value="completed">Completed</option>
                  <option value="processing">Processing</option>
                  <option value="failed">Failed</option>
                </select>
                <Button variant="outline" size="sm">
                  <Filter className="w-4 h-4 mr-2" />
                  More Filters
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Transcriptions Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredTranscriptions.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTranscriptions.map((transcription) => (
                <Card key={transcription.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg line-clamp-2">{transcription.title}</CardTitle>
                      <Badge className={`ml-2 ${getStatusColor(transcription.status)}`}>
                        {transcription.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between text-sm text-gray-600">
                      <span className="flex items-center">
                        <Clock className="w-4 h-4 mr-1" />
                        {formatDuration(transcription.duration_seconds)}
                      </span>
                      <span className="flex items-center">
                        <FileAudio className="w-4 h-4 mr-1" />
                        {formatFileSize(transcription.file_size)}
                      </span>
                    </div>
                    
                    <div className="flex items-center text-sm text-gray-500">
                      <Calendar className="w-4 h-4 mr-1" />
                      {new Date(transcription.created_at).toLocaleDateString()}
                    </div>

                    {transcription.transcription_text && (
                      <p className="text-sm text-gray-600 line-clamp-3">
                        {transcription.transcription_text.substring(0, 120)}...
                      </p>
                    )}

                    <div className="flex justify-between items-center pt-4 border-t">
                      <Link href={`/transcriptions/${transcription.id}`}>
                        <Button variant="outline" size="sm">
                          <Play className="w-4 h-4 mr-2" />
                          View
                        </Button>
                      </Link>
                      <div className="flex space-x-1">
                        <Button variant="ghost" size="sm">
                          <Download className="w-4 h-4" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => deleteTranscription(transcription.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-4">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="w-4 h-4 mr-2" />
                  Previous
                </Button>
                
                <span className="text-sm text-gray-600">
                  Page {currentPage} of {totalPages}
                </span>
                
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            )}
          </>
        ) : (
          <Card>
            <CardContent className="text-center py-12">
              <FileAudio className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {search ? 'No matching transcriptions' : 'No transcriptions yet'}
              </h3>
              <p className="text-gray-600 mb-6">
                {search 
                  ? 'Try adjusting your search terms or filters'
                  : 'Get started by creating your first transcription'
                }
              </p>
              {!search && (
                <Link href="/transcriptions/new">
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Transcription
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}