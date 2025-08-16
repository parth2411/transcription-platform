// frontend/src/app/transcriptions/new/page.tsx
'use client'

import { useState, useRef } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Upload, 
  Link as LinkIcon, 
  FileText, 
  Mic, 
  Loader2, 
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { useRouter, useSearchParams } from 'next/navigation'
import { RealTimeRecorder } from '@/components/transcription/RealTimeRecorder'

interface TranscriptionForm {
  title: string
  language: string
  generate_summary: boolean
  speaker_diarization: boolean
  add_to_knowledge_base: boolean
}

export default function NewTranscriptionPage() {
  const { token } = useAuth()
  const router = useRouter()
  const searchParams = useSearchParams()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'upload')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [uploadProgress, setUploadProgress] = useState(0)
  
  const [form, setForm] = useState<TranscriptionForm>({
    title: '',
    language: 'auto',
    generate_summary: true,
    speaker_diarization: false,
    add_to_knowledge_base: true
  })
  
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleFormChange = (field: keyof TranscriptionForm, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      if (!form.title) {
        setForm(prev => ({ ...prev, title: file.name.split('.')[0] }))
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) {
      setSelectedFile(file)
      if (!form.title) {
        setForm(prev => ({ ...prev, title: file.name.split('.')[0] }))
      }
    }
  }

  const uploadFile = async () => {
    if (!selectedFile || !form.title) {
      setError('Please select a file and enter a title')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('title', form.title)
      formData.append('language', form.language)
      formData.append('generate_summary', form.generate_summary.toString())
      formData.append('speaker_diarization', form.speaker_diarization.toString())
      formData.append('add_to_knowledge_base', form.add_to_knowledge_base.toString())

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/upload`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      setSuccess('File uploaded successfully! Processing started.')
      
      // Redirect to transcription detail page after a short delay
      setTimeout(() => {
        router.push(`/transcriptions/${result.id}`)
      }, 2000)

    } catch (err: any) {
      setError(err.message || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const processUrl = async () => {
    if (!url || !form.title) {
      setError('Please enter a URL and title')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          url,
          title: form.title,
          language: form.language,
          generate_summary: form.generate_summary,
          speaker_diarization: form.speaker_diarization,
          add_to_knowledge_base: form.add_to_knowledge_base
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'URL processing failed')
      }

      const result = await response.json()
      setSuccess('URL processing started!')
      
      setTimeout(() => {
        router.push(`/transcriptions/${result.id}`)
      }, 2000)

    } catch (err: any) {
      setError(err.message || 'URL processing failed')
    } finally {
      setLoading(false)
    }
  }

  const processText = async () => {
    if (!text || !form.title) {
      setError('Please enter text and title')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          text,
          title: form.title,
          generate_summary: form.generate_summary,
          add_to_knowledge_base: form.add_to_knowledge_base
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Text processing failed')
      }

      const result = await response.json()
      setSuccess('Text processing started!')
      
      setTimeout(() => {
        router.push(`/transcriptions/${result.id}`)
      }, 2000)

    } catch (err: any) {
      setError(err.message || 'Text processing failed')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'upload', label: 'Upload File', icon: Upload },
    { id: 'url', label: 'From URL', icon: LinkIcon },
    { id: 'realtime', label: 'Live Recording', icon: Mic },
    { id: 'text', label: 'Text Input', icon: FileText },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">New Transcription</h1>
          <p className="text-gray-600 mt-2">Upload audio, video, or text to create a new transcription</p>
        </div>

        {/* Status Messages */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {success && (
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertDescription>{success}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Tabs */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`py-2 px-1 border-b-2 font-medium text-sm ${
                        activeTab === tab.id
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <Icon className="w-4 h-4" />
                        <span>{tab.label}</span>
                      </div>
                    </button>
                  )
                })}
              </nav>
            </div>
            
            {/* Upload File Tab */}
            {activeTab === 'upload' && (
              <Card>
                <CardHeader>
                  <CardTitle>Upload Audio/Video File</CardTitle>
                  <CardDescription>
                    Supported formats: MP3, WAV, MP4, MOV, AVI (max 100MB)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div
                    className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors"
                    onDragOver={handleDragOver}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    {selectedFile ? (
                      <div>
                        <p className="text-lg font-medium text-gray-900 mb-2">
                          {selectedFile.name}
                        </p>
                        <p className="text-gray-500">
                          {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-lg font-medium text-gray-900 mb-2">
                          Drop files here or click to browse
                        </p>
                        <p className="text-gray-500">
                          Supports audio and video files up to 100MB
                        </p>
                      </div>
                    )}
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="audio/*,video/*"
                      className="hidden"
                      onChange={handleFileSelect}
                    />
                  </div>

                  <Button
                    onClick={uploadFile}
                    disabled={!selectedFile || loading}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Upload and Process
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )} 
            {/* URL Tab */}
            {activeTab === 'url' && (
              <Card>
                <CardHeader>
                  <CardTitle>Process from URL</CardTitle>
                  <CardDescription>
                    Enter a YouTube, podcast, or direct media URL
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="url">Media URL</Label>
                    <Input
                      id="url"
                      type="url"
                      placeholder="https://youtube.com/watch?v=..."
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <Button
                    onClick={processUrl}
                    disabled={!url || loading}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <LinkIcon className="w-4 h-4 mr-2" />
                        Process URL
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
            {activeTab === 'realtime' && (
              <div className="space-y-6">
                <RealTimeRecorder
                  onTranscriptionComplete={(text, audioBlob) => {
                    // Set the transcription in form
                    if (!form.title) {
                      setForm(prev => ({ 
                        ...prev, 
                        title: `Live Recording ${new Date().toLocaleString()}`
                      }))
                    }
                    
                    // You can process the completed transcription here
                    setSuccess('Live recording completed! Transcription ready.')
                    
                    // Optionally save to backend
                    if (form.add_to_knowledge_base && text) {
                      // Save to knowledge base
                      processText()
                    }
                  }}
                />
              </div>
            )}
            {/* Text Tab */}
            {activeTab === 'text' && (
              <Card>
                <CardHeader>
                  <CardTitle>Process Text</CardTitle>
                  <CardDescription>
                    Paste or type text to generate summary and add to knowledge base
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="text">Text Content</Label>
                    <textarea
                      id="text"
                      rows={10}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Paste your text content here..."
                      value={text}
                      onChange={(e) => setText(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <Button
                    onClick={processText}
                    disabled={!text || loading}
                    className="w-full"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <FileText className="w-4 h-4 mr-2" />
                        Process Text
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
          
          {/* Options Sidebar */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Processing Options</CardTitle>
                <CardDescription>
                  Configure how your content will be processed
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="title">Title</Label>
                  <Input
                    id="title"
                    placeholder="Enter transcription title"
                    value={form.title}
                    onChange={(e) => handleFormChange('title', e.target.value)}
                    disabled={loading}
                  />
                </div>
                {activeTab !== 'text' && (
                  <div className="space-y-2">
                    <Label htmlFor="language">Language</Label>
                    <select
                      id="language"
                      className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      value={form.language}
                      onChange={(e) => handleFormChange('language', e.target.value)}
                      disabled={loading}
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="en">English</option>
                      <option value="es">Spanish</option>
                      <option value="fr">French</option>
                      <option value="de">German</option>
                      <option value="it">Italian</option>
                      <option value="pt">Portuguese</option>
                    </select>
                  </div>
                )}

                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="summary"
                      checked={form.generate_summary}
                      onChange={(e) => handleFormChange('generate_summary', e.target.checked)}
                      className="rounded border-gray-300"
                      disabled={loading}
                    />
                    <Label htmlFor="summary" className="text-sm">
                      Generate summary
                    </Label>
                  </div>

                  {activeTab !== 'text' && (
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="diarization"
                        checked={form.speaker_diarization}
                        onChange={(e) => handleFormChange('speaker_diarization', e.target.checked)}
                        className="rounded border-gray-300"
                        disabled={loading}
                      />
                      <Label htmlFor="diarization" className="text-sm">
                        Speaker identification
                      </Label>
                    </div>
                  )}

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="knowledge"
                      checked={form.add_to_knowledge_base}
                      onChange={(e) => handleFormChange('add_to_knowledge_base', e.target.checked)}
                      className="rounded border-gray-300"
                      disabled={loading}
                    />
                    <Label htmlFor="knowledge" className="text-sm">
                      Add to knowledge base
                    </Label>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Tips */}
            <Card>
              <CardHeader>
                <CardTitle>Tips for Best Results</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-gray-600 space-y-2">
                <p>• Use clear, high-quality audio</p>
                <p>• Minimize background noise</p>
                <p>• Ensure speakers are clearly audible</p>
                <p>• For videos, audio quality matters most</p>
                <p>• Longer files may take more time to process</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}