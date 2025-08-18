// frontend/src/components/transcription/RealTimeRecorder.tsx
'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { 
  Mic, 
  MicOff, 
  Square, 
  Play, 
  Pause, 
  Download,
  AlertCircle,
  Volume2,
  CheckCircle,
  Database,
  FileText,
  Clock
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

interface RealTimeRecorderProps {
  onTranscriptionComplete?: (result: TranscriptionResult) => void
}

export function RealTimeRecorder({ onTranscriptionComplete }: RealTimeRecorderProps) {
  const { token } = useAuth()
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [transcription, setTranscription] = useState('')
  const [summary, setSummary] = useState('')
  const [realTimeText, setRealTimeText] = useState('')
  const [error, setError] = useState('')
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  const [completedResult, setCompletedResult] = useState<TranscriptionResult | null>(null)
  
  // Form settings
  const [title, setTitle] = useState('')
  const [addToKnowledgeBase, setAddToKnowledgeBase] = useState(true)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    return () => {
      stopRecording()
      if (timerRef.current) clearInterval(timerRef.current)
      if (chunkIntervalRef.current) clearInterval(chunkIntervalRef.current)
    }
  }, [])

  const startRecording = async () => {
    try {
      setError('')
      setTranscription('')
      setSummary('')
      setRealTimeText('')
      setCompletedResult(null)
      
      // Generate default title if empty
      if (!title) {
        const now = new Date()
        setTitle(`Recording ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`)
      }
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      })
      
      streamRef.current = stream

      // Set up audio level monitoring
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      
      analyserRef.current.fftSize = 256
      const bufferLength = analyserRef.current.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      
      const updateAudioLevel = () => {
        if (analyserRef.current && isRecording) {
          analyserRef.current.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / bufferLength
          setAudioLevel(average)
          requestAnimationFrame(updateAudioLevel)
        }
      }
      updateAudioLevel()

      // Set up MediaRecorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      })
      
      audioChunksRef.current = []
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        processCompleteRecording(audioBlob)
      }

      // Start recording
      mediaRecorderRef.current.start(1000) // Collect data every second
      setIsRecording(true)
      setRecordingTime(0)

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

      // Process chunks for real-time transcription every 5 seconds
      chunkIntervalRef.current = setInterval(async () => {
        if (audioChunksRef.current.length > 0) {
          const recentChunks = audioChunksRef.current.slice(-5) // Last 5 seconds
          const chunkBlob = new Blob(recentChunks, { type: 'audio/webm' })
          await processRealTimeChunk(chunkBlob)
        }
      }, 5000)

    } catch (err: any) {
      setError(`Microphone access denied: ${err.message}`)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
    }

    if (timerRef.current) {
      clearInterval(timerRef.current)
    }

    if (chunkIntervalRef.current) {
      clearInterval(chunkIntervalRef.current)
    }

    setAudioLevel(0)
  }

  const processRealTimeChunk = async (audioBlob: Blob) => {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'chunk.webm')

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/realtime-chunk`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData
      })

      if (response.ok) {
        const result = await response.json()
        if (result.text) {
          setRealTimeText(prev => prev + ' ' + result.text)
        }
      }
    } catch (error) {
      console.error('Real-time transcription failed:', error)
    }
  }

  const processCompleteRecording = async (audioBlob: Blob) => {
    try {
      setIsProcessing(true)
      
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')
      formData.append('title', title || `Recording ${new Date().toLocaleString()}`)
      formData.append('add_to_knowledge_base', addToKnowledgeBase.toString())

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/realtime-complete`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData
      })

      if (response.ok) {
        const result: TranscriptionResult = await response.json()
        setTranscription(result.text || realTimeText)
        setSummary(result.summary || '')
        setCompletedResult(result)
        onTranscriptionComplete?.(result)
      } else {
        const error = await response.json()
        setError(`Processing failed: ${error.detail || 'Unknown error'}`)
        setTranscription(realTimeText)
      }
    } catch (error) {
      console.error('Final transcription failed:', error)
      setError('Processing failed. Please try again.')
      setTranscription(realTimeText)
    } finally {
      setIsProcessing(false)
    }
  }

  const playRecording = () => {
    if (audioChunksRef.current.length > 0) {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      const audioUrl = URL.createObjectURL(audioBlob)
      
      if (audioRef.current) {
        audioRef.current.src = audioUrl
        audioRef.current.play()
        setIsPlaying(true)
        
        audioRef.current.onended = () => {
          setIsPlaying(false)
          URL.revokeObjectURL(audioUrl)
        }
      }
    }
  }

  const downloadRecording = () => {
    if (audioChunksRef.current.length > 0) {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      const url = URL.createObjectURL(audioBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${title || 'recording'}-${new Date().toISOString()}.webm`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Mic className="w-5 h-5" />
          <span>Real-Time Recording</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Recording Settings */}
        {!isRecording && !completedResult && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Recording Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={`Recording ${new Date().toLocaleString()}`}
              />
            </div>
            
            <div className="flex items-center space-x-2">
              <Checkbox
                id="knowledge-base"
                checked={addToKnowledgeBase}
                onCheckedChange={(checked) => setAddToKnowledgeBase(checked as boolean)}
              />
              <Label htmlFor="knowledge-base" className="text-sm">
                Add to Knowledge Base for future queries
              </Label>
            </div>
          </div>
        )}

        {/* Recording Controls */}
        <div className="flex flex-col items-center space-y-4">
          <div className="flex items-center space-x-4">
            {!isRecording ? (
              <Button
                onClick={startRecording}
                size="lg"
                disabled={isProcessing}
                className="bg-red-500 hover:bg-red-600 text-white rounded-full w-16 h-16"
              >
                <Mic className="w-8 h-8" />
              </Button>
            ) : (
              <Button
                onClick={stopRecording}
                size="lg"
                className="bg-gray-500 hover:bg-gray-600 text-white rounded-full w-16 h-16"
              >
                <Square className="w-8 h-8" />
              </Button>
            )}
          </div>

          {/* Recording Status */}
          {isRecording && (
            <div className="text-center space-y-2">
              <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                🔴 Recording - {formatTime(recordingTime)}
              </Badge>
              
              {/* Audio Level Visualizer */}
              <div className="flex items-center space-x-2">
                <Volume2 className="w-4 h-4 text-gray-500" />
                <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-green-500 transition-all duration-100"
                    style={{ width: `${Math.min(100, (audioLevel / 255) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Processing Status */}
          {isProcessing && (
            <div className="text-center space-y-2">
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                <div className="animate-spin w-4 h-4 mr-2 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                Processing transcription and summary...
              </Badge>
            </div>
          )}
        </div>

        {/* Real-time Transcription */}
        {(isRecording || realTimeText) && (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-900 flex items-center space-x-2">
              <Mic className="w-4 h-4" />
              <span>Real-time Transcription:</span>
            </h4>
            <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
              <p className="text-gray-700 text-sm leading-relaxed">
                {realTimeText || "Listening..."}
                {isRecording && <span className="animate-pulse ml-1">|</span>}
              </p>
            </div>
          </div>
        )}

        {/* Final Results */}
        {completedResult && (
          <div className="space-y-4">
            {/* Success Message */}
            <Alert className="border-green-200 bg-green-50">
              <CheckCircle className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                <div className="space-y-1">
                  <p><strong>Recording processed successfully!</strong></p>
                  <div className="flex items-center space-x-4 text-sm">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3" />
                      <span>{formatTime(completedResult.duration_seconds)}</span>
                    </span>
                    {completedResult.stored_in_knowledge_base && (
                      <span className="flex items-center space-x-1">
                        <Database className="w-3 h-3" />
                        <span>Stored in Knowledge Base</span>
                      </span>
                    )}
                  </div>
                </div>
              </AlertDescription>
            </Alert>

            {/* Final Transcription */}
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900 flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>Final Transcription:</span>
              </h4>
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-gray-800 leading-relaxed">{transcription}</p>
              </div>
            </div>

            {/* Summary */}
            {summary && (
              <div className="space-y-2">
                <h4 className="font-medium text-gray-900 flex items-center space-x-2">
                  <FileText className="w-4 h-4" />
                  <span>Summary:</span>
                </h4>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div 
                    className="text-gray-800 leading-relaxed prose prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: summary.replace(/\n/g, '<br>') }}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Playback Controls */}
        {!isRecording && audioChunksRef.current.length > 0 && (
          <div className="flex justify-center space-x-3">
            <Button
              onClick={playRecording}
              variant="outline"
              size="sm"
              disabled={isPlaying || isProcessing}
            >
              {isPlaying ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {isPlaying ? 'Playing' : 'Play'}
            </Button>
            
            <Button
              onClick={downloadRecording}
              variant="outline"
              size="sm"
              disabled={isProcessing}
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>
        )}

        {/* Hidden audio element for playback */}
        <audio ref={audioRef} style={{ display: 'none' }} />
      </CardContent>
    </Card>
  )
}