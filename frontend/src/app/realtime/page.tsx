// frontend/src/app/realtime/page.tsx
'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { RealTimeRecorder } from '@/components/transcription/RealTimeRecorder'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Mic, 
  Clock, 
  FileText, 
  Database, 
  CheckCircle,
  ArrowRight,
  Info
} from 'lucide-react'

interface TranscriptionResult {
  id: string
  text: string
  summary: string
  status: string
  stored_in_knowledge_base: boolean
  duration_seconds: number
  title: string
  created_at: string
}

export default function RealTimePage() {
  const [recentTranscriptions, setRecentTranscriptions] = useState<TranscriptionResult[]>([])

  const handleTranscriptionComplete = (result: TranscriptionResult) => {
    setRecentTranscriptions(prev => [result, ...prev.slice(0, 4)]) // Keep last 5
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleString()
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center space-x-3">
            <Mic className="w-8 h-8 text-red-500" />
            <span>Real-Time Recording</span>
          </h1>
          <p className="text-gray-600 mt-2">
            Record audio with live transcription, automatic summarization, and knowledge base integration
          </p>
        </div>

        {/* Info Alert */}
        <Alert className="border-blue-200 bg-blue-50">
          <Info className="h-4 w-4 text-blue-600" />
          <AlertDescription className="text-blue-800">
            <strong>How it works:</strong> Start recording to see live transcription. When you stop, 
            we'll generate a comprehensive summary and optionally store everything in your knowledge base for future queries.
          </AlertDescription>
        </Alert>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Recording Interface */}
          <div className="lg:col-span-2">
            <RealTimeRecorder onTranscriptionComplete={handleTranscriptionComplete} />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Features */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Features</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-start space-x-3">
                  <Mic className="w-5 h-5 text-blue-500 mt-0.5" />
                  <div>
                    <h4 className="font-medium">Live Transcription</h4>
                    <p className="text-sm text-gray-600">See your words appear in real-time as you speak</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <FileText className="w-5 h-5 text-green-500 mt-0.5" />
                  <div>
                    <h4 className="font-medium">Smart Summaries</h4>
                    <p className="text-sm text-gray-600">Automatic AI-generated summaries with key points</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <Database className="w-5 h-5 text-purple-500 mt-0.5" />
                  <div>
                    <h4 className="font-medium">Knowledge Integration</h4>
                    <p className="text-sm text-gray-600">Store in your knowledge base for future queries</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Recent Recordings */}
            {recentTranscriptions.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Recent Recordings</CardTitle>
                  <CardDescription>Your last few real-time recordings</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {recentTranscriptions.map((recording, index) => (
                    <div key={recording.id} className="border-l-4 border-blue-500 pl-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <h5 className="font-medium text-sm truncate">{recording.title}</h5>
                        <Badge variant="outline" className="text-xs">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Complete
                        </Badge>
                      </div>
                      
                      <div className="flex items-center space-x-4 text-xs text-gray-500">
                        <span className="flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{formatTime(recording.duration_seconds)}</span>
                        </span>
                        
                        {recording.stored_in_knowledge_base && (
                          <span className="flex items-center space-x-1">
                            <Database className="w-3 h-3" />
                            <span>Stored</span>
                          </span>
                        )}
                      </div>
                      
                      <p className="text-xs text-gray-600 line-clamp-2">
                        {recording.text.substring(0, 100)}...
                      </p>
                      
                      <p className="text-xs text-gray-500">
                        {formatDate(recording.created_at)}
                      </p>
                    </div>
                  ))}
                  
                  <Button variant="outline" size="sm" className="w-full">
                    View All Recordings
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Tips */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recording Tips</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-gray-600">
                <div className="flex items-start space-x-2">
                  <span className="text-blue-500">•</span>
                  <span>Speak clearly and at a normal pace</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-500">•</span>
                  <span>Use a quiet environment when possible</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-500">•</span>
                  <span>Give meaningful titles for better organization</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-500">•</span>
                  <span>Enable knowledge base storage to make content searchable</span>
                </div>
                <div className="flex items-start space-x-2">
                  <span className="text-blue-500">•</span>
                  <span>Watch the audio level indicator to ensure good input</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}