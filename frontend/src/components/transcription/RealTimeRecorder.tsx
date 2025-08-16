// frontend/src/components/transcription/RealTimeRecorder.tsx
'use client'

import React, { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { 
  Mic, 
  MicOff, 
  Square, 
  Play, 
  Pause, 
  Download,
  AlertCircle,
  Volume2
} from 'lucide-react'

interface RealTimeRecorderProps {
  onTranscriptionComplete?: (transcription: string, audioBlob: Blob) => void
}

export function RealTimeRecorder({ onTranscriptionComplete }: RealTimeRecorderProps) {
  const { token } = useAuth()
  const [isRecording, setIsRecording] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [transcription, setTranscription] = useState('')
  const [realTimeText, setRealTimeText] = useState('')
  const [error, setError] = useState('')
  const [recordingTime, setRecordingTime] = useState(0)
  const [audioLevel, setAudioLevel] = useState(0)
  
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
      setTranscription('')
      setRealTimeText('')

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

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/realtime`, {
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
      const formData = new FormData()
      formData.append('audio', audioBlob, 'recording.webm')

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/complete`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData
      })

      if (response.ok) {
        const result = await response.json()
        setTranscription(result.text || realTimeText)
        onTranscriptionComplete?.(result.text || realTimeText, audioBlob)
      }
    } catch (error) {
      console.error('Final transcription failed:', error)
      setTranscription(realTimeText)
      onTranscriptionComplete?.(realTimeText, audioBlob)
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
      a.download = `recording-${new Date().toISOString()}.webm`
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

        {/* Recording Controls */}
        <div className="flex flex-col items-center space-y-4">
          <div className="flex items-center space-x-4">
            {!isRecording ? (
              <Button
                onClick={startRecording}
                size="lg"
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
        </div>

        {/* Real-time Transcription */}
        {(isRecording || realTimeText) && (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">Real-time Transcription:</h4>
            <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
              <p className="text-gray-700 text-sm leading-relaxed">
                {realTimeText || "Listening..."}
                {isRecording && <span className="animate-pulse ml-1">|</span>}
              </p>
            </div>
          </div>
        )}

        {/* Final Transcription */}
        {transcription && (
          <div className="space-y-2">
            <h4 className="font-medium text-gray-900">Final Transcription:</h4>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-gray-800 leading-relaxed">{transcription}</p>
            </div>
          </div>
        )}

        {/* Playback Controls */}
        {!isRecording && audioChunksRef.current.length > 0 && (
          <div className="flex justify-center space-x-3">
            <Button
              onClick={playRecording}
              variant="outline"
              size="sm"
              disabled={isPlaying}
            >
              {isPlaying ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
              {isPlaying ? 'Playing...' : 'Play Recording'}
            </Button>
            
            <Button
              onClick={downloadRecording}
              variant="outline"
              size="sm"
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>
        )}

        <audio ref={audioRef} className="hidden" />
      </CardContent>
    </Card>
  )
}