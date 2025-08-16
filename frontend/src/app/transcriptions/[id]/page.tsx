// frontend/src/app/transcriptions/[id]/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Play, 
  Pause, 
  Download, 
  Share, 
  Edit3, 
  Clock, 
  FileAudio,
  MessageSquare,
  Loader2
} from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'
import { ExportActions } from '@/components/transcription/ExportActions'

interface TranscriptionDetail {
  id: string
  title: string
  status: string
  file_type?: string
  file_size?: number
  duration_seconds?: number
  transcription_text?: string
  summary_text?: string
  language: string
  created_at: string
  completed_at?: string
  processing_time_seconds?: number
  error_message?: string
}

export default function TranscriptionDetailPage() {
  const { token, user } = useAuth()
  const { id } = useParams()
  const router = useRouter()
  const [transcription, setTranscription] = useState<TranscriptionDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token || !id) return
    fetchTranscription()
  }, [token, id])

  const fetchTranscription = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch transcription')
      }

      const data = await response.json()
      setTranscription(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A'
    const mb = bytes / 1024 / 1024
    return `${mb.toFixed(2)} MB`
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

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      </DashboardLayout>
    )
  }

  if (error || !transcription) {
    return (
      <DashboardLayout>
        <div className="text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Transcription Not Found</h2>
          <p className="text-gray-600 mb-8">{error || 'The requested transcription could not be found.'}</p>
          <Button onClick={() => router.push('/transcriptions')}>
            Back to Library
          </Button>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{transcription.title}</h1>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <span className="flex items-center">
                <Clock className="w-4 h-4 mr-1" />
                {formatDuration(transcription.duration_seconds)}
              </span>
              <span className="flex items-center">
                <FileAudio className="w-4 h-4 mr-1" />
                {formatFileSize(transcription.file_size)}
              </span>
              <Badge className={getStatusColor(transcription.status)}>
                {transcription.status}
              </Badge>
            </div>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" size="sm">
              <Share className="w-4 h-4 mr-2" />
              Share
            </Button>
            <Button variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
            <Button variant="outline" size="sm">
              <Edit3 className="w-4 h-4 mr-2" />
              Edit
            </Button>
          </div>
        </div>

        {/* Status Message */}
        {transcription.status === 'processing' && (
          <Card className="border-yellow-200 bg-yellow-50">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <Loader2 className="w-5 h-5 animate-spin text-yellow-600" />
                <div>
                  <p className="font-medium text-yellow-800">Processing in progress...</p>
                  <p className="text-sm text-yellow-600">Your transcription is being processed. This may take a few minutes.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {transcription.status === 'failed' && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-3">
                <div className="w-5 h-5 bg-red-500 rounded-full" />
                <div>
                  <p className="font-medium text-red-800">Processing failed</p>
                  <p className="text-sm text-red-600">{transcription.error_message || 'An error occurred during processing.'}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Transcription */}
            {transcription.transcription_text && (
              <Card>
                <CardHeader>
                  <CardTitle>Transcription</CardTitle>
                  <CardDescription>
                    Auto-generated transcription with {transcription.language} language detection
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose max-w-none">
                    <div className="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-sm leading-relaxed">
                      {transcription.transcription_text}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Summary */}
            {transcription.summary_text && (
              <Card>
                <CardHeader>
                  <CardTitle>AI Summary</CardTitle>
                  <CardDescription>
                    Structured summary with key points and insights
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose max-w-none">
                    <div className="markdown-content">
                      {transcription.summary_text.split('\n').map((line, index) => {
                        if (line.startsWith('## ')) {
                          return <h3 key={index} className="text-lg font-semibold text-gray-900 mt-6 mb-3">{line.replace('## ', '')}</h3>
                        } else if (line.startsWith('- ')) {
                          return <li key={index} className="text-gray-700 mb-1">{line.replace('- ', '')}</li>
                        } else if (line.trim()) {
                          return <p key={index} className="text-gray-700 mb-3">{line}</p>
                        }
                        return null
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Metadata */}
            <Card>
              <CardHeader>
                <CardTitle>Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Language</span>
                  <span className="text-sm font-medium">{transcription.language}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Duration</span>
                  <span className="text-sm font-medium">{formatDuration(transcription.duration_seconds)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">File Size</span>
                  <span className="text-sm font-medium">{formatFileSize(transcription.file_size)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Created</span>
                  <span className="text-sm font-medium">
                    {new Date(transcription.created_at).toLocaleDateString()}
                  </span>
                </div>
                {transcription.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Completed</span>
                    <span className="text-sm font-medium">
                      {new Date(transcription.completed_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {transcription.processing_time_seconds && (
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600">Processing Time</span>
                    <span className="text-sm font-medium">
                      {transcription.processing_time_seconds}s
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
            {/* Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full" variant="outline">
                  <MessageSquare className="w-4 h-4 mr-2" />
                  Ask Questions
                </Button>
                <Button className="w-full" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Download Transcript
                </Button>
                <Button className="w-full" variant="outline">
                  <Share className="w-4 h-4 mr-2" />
                  Share Link
                </Button>
              </CardContent>
            </Card>
            {/* Export & Share Card */}
            {token && ( // Add this condition to ensure token exists
              <Card>
                <CardHeader>
                  <CardTitle>Export & Share</CardTitle>
                </CardHeader>
                <CardContent>
                  <ExportActions 
                    transcription={transcription} 
                    token={token} 
                  />
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}