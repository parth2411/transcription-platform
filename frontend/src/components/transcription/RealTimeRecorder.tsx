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
  Clock,
  Zap
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
      
      // Start audio level monitoring immediately
      requestAnimationFrame(updateAudioLevel)

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

  const resetRecording = () => {
    setTranscription('')
    setSummary('')
    setRealTimeText('')
    setCompletedResult(null)
    setError('')
    setRecordingTime(0)
    setAudioLevel(0)
    audioChunksRef.current = []
    setTitle('')
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Mic className="w-5 h-5 text-red-500" />
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

        {/* Modern Recording Controls */}
        <div className="flex flex-col items-center space-y-6">
          <div className="flex items-center space-x-6">
            {!isRecording ? (
              <div className="relative">
                {/* Start Recording Button with Modern Animation */}
                <Button
                  onClick={startRecording}
                  size="lg"
                  disabled={isProcessing}
                  className="bg-gradient-to-r from-red-500 to-pink-500 hover:from-red-600 hover:to-pink-600 text-white rounded-full w-20 h-20 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 relative overflow-hidden group"
                >
                  {/* Animated background rings */}
                  <div className="absolute inset-0 rounded-full bg-gradient-to-r from-red-400 to-pink-400 opacity-0 group-hover:opacity-20 animate-pulse"></div>
                  
                  {/* Outer pulsing ring */}
                  <div className="absolute -inset-2 rounded-full bg-red-500 opacity-20 animate-ping"></div>
                  
                  {/* Middle rotating ring */}
                  <div className="absolute -inset-1 rounded-full border-2 border-red-300 opacity-30 animate-spin"></div>
                  
                  {/* Icon */}
                  <Mic className="w-8 h-8 relative z-10" />
                </Button>
                
              </div>
            ) : (
            <div className="flex flex-col items-center gap-4">
                {/* Button container (can keep relative for internal animations) */}
                <div className="relative">
                    <Button
                      onClick={stopRecording}
                      size="lg"
                      className="bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800 text-white rounded-full w-20 h-20 shadow-lg hover:shadow-xl transition-all duration-300 relative overflow-hidden group animate-pulse"
                    >
                      {/* Breathing effect for recording */}
                      <div className="absolute inset-0 rounded-full bg-red-500 opacity-30 animate-ping"></div>
                      <div className="absolute inset-1 rounded-full bg-red-400 opacity-20 animate-pulse"></div>
                      
                      {/* Stop icon */}
                      <Square className="w-8 h-8 relative z-10" />
                    </Button>
                </div>
                
                {/* Recording indicator - NOW IN NORMAL FLOW & CORRECTLY SPACED */}
                <div className="text-sm text-red-600 whitespace-nowrap font-medium">
                  Recording: {formatTime(recordingTime)}
                </div>
            </div>
          )}
          </div>

          {/* Recording Status with Clean Design */}
          {isRecording && (
            <div className="text-center space-y-6 w-full max-w-md">
              {/* Simple waveform-style animation bars */}
              <div className="flex items-center justify-center space-x-1">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className="w-1 bg-red-400 rounded-full animate-pulse"
                    style={{
                      height: `${8 + Math.sin((Date.now() / 300) + i) * 4}px`,
                      animationDelay: `${i * 150}ms`,
                      animationDuration: '1.5s'
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Processing Status with Modern Spinner */}
          {isProcessing && (
            <div className="flex flex-col items-center space-y-4">
              <div className="relative">
                {/* Multi-layer loading spinner */}
                <div className="w-16 h-16 relative">
                  <div className="absolute inset-0 border-4 border-blue-200 rounded-full"></div>
                  <div className="absolute inset-0 border-4 border-transparent border-t-blue-600 rounded-full animate-spin"></div>
                  <div className="absolute inset-2 border-4 border-transparent border-t-purple-500 rounded-full animate-spin" style={{ animationDirection: 'reverse' }}></div>
                  <div className="absolute inset-4 flex items-center justify-center">
                    <Zap className="w-4 h-4 text-blue-600" />
                  </div>
                </div>
              </div>
              
              <Badge variant="outline" className="bg-gradient-to-r from-blue-50 to-purple-50 text-blue-700 border-blue-200 animate-pulse">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                  <span>Processing transcription and generating summary...</span>
                  <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </Badge>
            </div>
          )}
        </div>

        {/* Real-time Transcription with Clean Styling */}
        {(isRecording || realTimeText) && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-900 flex items-center space-x-2">
              <Mic className="w-4 h-4 text-blue-600" />
              <span>Live Transcription:</span>
            </h4>
            <div className="bg-gray-50 rounded-xl p-6 min-h-[120px] border border-gray-200">
              <p className="text-gray-700 text-sm leading-relaxed">
                {realTimeText || (
                  <span className="text-gray-400 italic">
                    Listening for speech...
                  </span>
                )}
                {isRecording && realTimeText && (
                  <span className="inline-block w-0.5 h-4 bg-blue-500 animate-pulse ml-1"></span>
                )}
              </p>
            </div>
          </div>
        )}

        {/* Final Results with Enhanced Design */}
        {completedResult && (
          <div className="space-y-6">
            {/* Success Message with Celebration Animation */}
            <Alert className="border-green-200 bg-gradient-to-r from-green-50 to-emerald-50 relative overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-green-100/20 to-emerald-100/20 animate-pulse"></div>
              <CheckCircle className="h-5 w-5 text-green-600 relative z-10" />
              <AlertDescription className="text-green-800 relative z-10">
                <div className="space-y-2">
                  <p className="font-semibold">🎉 Recording processed successfully!</p>
                  <div className="flex items-center space-x-6 text-sm">
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
                    <Badge variant="outline" className="bg-green-100 text-green-700 border-green-300">
                      ✅ Complete
                    </Badge>
                  </div>
                </div>
              </AlertDescription>
            </Alert>

            {/* Transcription Result */}
            {transcription && (
              <div className="space-y-3">
                <h4 className="font-semibold text-gray-900 flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  <span>Final Transcription:</span>
                </h4>
                <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
                  <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                    {transcription}
                  </p>
                </div>
              </div>
            )}

            {/* Summary */}
            {summary && (
              <div className="space-y-3">
                <h4 className="font-semibold text-gray-900 flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-purple-600" />
                  <span>AI Summary:</span>
                </h4>
                <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 border border-purple-200">
                  <p className="text-gray-800 leading-relaxed">
                    {summary}
                  </p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 pt-4">
              {audioChunksRef.current.length > 0 && (
                <>
                  <Button
                    onClick={playRecording}
                    variant="outline"
                    size="sm"
                    className="flex items-center space-x-2 hover:bg-blue-50 hover:border-blue-300"
                  >
                    {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    <span>{isPlaying ? 'Pause' : 'Play'} Recording</span>
                  </Button>
                  
                  <Button
                    onClick={downloadRecording}
                    variant="outline"
                    size="sm"
                    className="flex items-center space-x-2 hover:bg-green-50 hover:border-green-300"
                  >
                    <Download className="w-4 h-4" />
                    <span>Download Audio</span>
                  </Button>
                </>
              )}
              
              <Button
                onClick={resetRecording}
                variant="outline"
                size="sm"
                className="flex items-center space-x-2 hover:bg-gray-50"
              >
                <Mic className="w-4 h-4" />
                <span>New Recording</span>
              </Button>
            </div>
          </div>
        )}

        {/* Hidden audio element for playback */}
        <audio ref={audioRef} className="hidden" />
      </CardContent>
    </Card>
  )
}
// // frontend/src/components/transcription/RealTimeRecorder.tsx
// 'use client'

// import React, { useState, useRef, useEffect } from 'react'
// import { useAuth } from '@/components/auth/AuthProvider'
// import { Button } from '@/components/ui/button'
// import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
// import { Alert, AlertDescription } from '@/components/ui/alert'
// import { Badge } from '@/components/ui/badge'
// import { Input } from '@/components/ui/input'
// import { Label } from '@/components/ui/label'
// import { Checkbox } from '@/components/ui/checkbox'
// import { 
//   Mic, 
//   MicOff, 
//   Square, 
//   Play, 
//   Pause, 
//   Download,
//   AlertCircle,
//   Volume2,
//   CheckCircle,
//   Database,
//   FileText,
//   Clock
// } from 'lucide-react'

// interface TranscriptionResult {
//   id: string
//   text: string
//   summary: string
//   status: string
//   stored_in_knowledge_base: boolean
//   duration_seconds: number
//   title: string
//   created_at: string
// }

// interface RealTimeRecorderProps {
//   onTranscriptionComplete?: (result: TranscriptionResult) => void
// }

// export function RealTimeRecorder({ onTranscriptionComplete }: RealTimeRecorderProps) {
//   const { token } = useAuth()
//   const [isRecording, setIsRecording] = useState(false)
//   const [isPlaying, setIsPlaying] = useState(false)
//   const [isProcessing, setIsProcessing] = useState(false)
//   const [transcription, setTranscription] = useState('')
//   const [summary, setSummary] = useState('')
//   const [realTimeText, setRealTimeText] = useState('')
//   const [error, setError] = useState('')
//   const [recordingTime, setRecordingTime] = useState(0)
//   const [audioLevel, setAudioLevel] = useState(0)
//   const [completedResult, setCompletedResult] = useState<TranscriptionResult | null>(null)
  
//   // Form settings
//   const [title, setTitle] = useState('')
//   const [addToKnowledgeBase, setAddToKnowledgeBase] = useState(true)
  
//   const mediaRecorderRef = useRef<MediaRecorder | null>(null)
//   const audioChunksRef = useRef<Blob[]>([])
//   const streamRef = useRef<MediaStream | null>(null)
//   const audioContextRef = useRef<AudioContext | null>(null)
//   const analyserRef = useRef<AnalyserNode | null>(null)
//   const timerRef = useRef<NodeJS.Timeout | null>(null)
//   const audioRef = useRef<HTMLAudioElement | null>(null)
//   const chunkIntervalRef = useRef<NodeJS.Timeout | null>(null)

//   useEffect(() => {
//     return () => {
//       stopRecording()
//       if (timerRef.current) clearInterval(timerRef.current)
//       if (chunkIntervalRef.current) clearInterval(chunkIntervalRef.current)
//     }
//   }, [])

//   const startRecording = async () => {
//     try {
//       setError('')
//       setTranscription('')
//       setSummary('')
//       setRealTimeText('')
//       setCompletedResult(null)
      
//       // Generate default title if empty
//       if (!title) {
//         const now = new Date()
//         setTitle(`Recording ${now.toLocaleDateString()} ${now.toLocaleTimeString()}`)
//       }
      
//       // Request microphone access
//       const stream = await navigator.mediaDevices.getUserMedia({ 
//         audio: {
//           echoCancellation: true,
//           noiseSuppression: true,
//           sampleRate: 16000
//         } 
//       })
      
//       streamRef.current = stream

//       // Set up audio level monitoring
//       audioContextRef.current = new AudioContext()
//       analyserRef.current = audioContextRef.current.createAnalyser()
//       const source = audioContextRef.current.createMediaStreamSource(stream)
//       source.connect(analyserRef.current)
      
//       analyserRef.current.fftSize = 256
//       const bufferLength = analyserRef.current.frequencyBinCount
//       const dataArray = new Uint8Array(bufferLength)
      
//       const updateAudioLevel = () => {
//         if (analyserRef.current && isRecording) {
//           analyserRef.current.getByteFrequencyData(dataArray)
//           const average = dataArray.reduce((a, b) => a + b) / bufferLength
//           setAudioLevel(average)
//           requestAnimationFrame(updateAudioLevel)
//         }
//       }
//       updateAudioLevel()

//       // Set up MediaRecorder
//       mediaRecorderRef.current = new MediaRecorder(stream, {
//         mimeType: 'audio/webm'
//       })
      
//       audioChunksRef.current = []
      
//       mediaRecorderRef.current.ondataavailable = (event) => {
//         if (event.data.size > 0) {
//           audioChunksRef.current.push(event.data)
//         }
//       }

//       mediaRecorderRef.current.onstop = () => {
//         const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
//         processCompleteRecording(audioBlob)
//       }

//       // Start recording
//       mediaRecorderRef.current.start(1000) // Collect data every second
//       setIsRecording(true)
//       setRecordingTime(0)

//       // Start timer
//       timerRef.current = setInterval(() => {
//         setRecordingTime(prev => prev + 1)
//       }, 1000)

//       // Process chunks for real-time transcription every 5 seconds
//       chunkIntervalRef.current = setInterval(async () => {
//         if (audioChunksRef.current.length > 0) {
//           const recentChunks = audioChunksRef.current.slice(-5) // Last 5 seconds
//           const chunkBlob = new Blob(recentChunks, { type: 'audio/webm' })
//           await processRealTimeChunk(chunkBlob)
//         }
//       }, 5000)

//     } catch (err: any) {
//       setError(`Microphone access denied: ${err.message}`)
//     }
//   }

//   const stopRecording = () => {
//     if (mediaRecorderRef.current && isRecording) {
//       mediaRecorderRef.current.stop()
//       setIsRecording(false)
//     }

//     if (streamRef.current) {
//       streamRef.current.getTracks().forEach(track => track.stop())
//     }

//     if (audioContextRef.current) {
//       audioContextRef.current.close()
//     }

//     if (timerRef.current) {
//       clearInterval(timerRef.current)
//     }

//     if (chunkIntervalRef.current) {
//       clearInterval(chunkIntervalRef.current)
//     }

//     setAudioLevel(0)
//   }

//   const processRealTimeChunk = async (audioBlob: Blob) => {
//     try {
//       const formData = new FormData()
//       formData.append('audio', audioBlob, 'chunk.webm')

//       const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/realtime-chunk`, {
//         method: 'POST',
//         headers: {
//           Authorization: `Bearer ${token}`,
//         },
//         body: formData
//       })

//       if (response.ok) {
//         const result = await response.json()
//         if (result.text) {
//           setRealTimeText(prev => prev + ' ' + result.text)
//         }
//       }
//     } catch (error) {
//       console.error('Real-time transcription failed:', error)
//     }
//   }

//   const processCompleteRecording = async (audioBlob: Blob) => {
//     try {
//       setIsProcessing(true)
      
//       const formData = new FormData()
//       formData.append('audio', audioBlob, 'recording.webm')
//       formData.append('title', title || `Recording ${new Date().toLocaleString()}`)
//       formData.append('add_to_knowledge_base', addToKnowledgeBase.toString())

//       const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/realtime-complete`, {
//         method: 'POST',
//         headers: {
//           Authorization: `Bearer ${token}`,
//         },
//         body: formData
//       })

//       if (response.ok) {
//         const result: TranscriptionResult = await response.json()
//         setTranscription(result.text || realTimeText)
//         setSummary(result.summary || '')
//         setCompletedResult(result)
//         onTranscriptionComplete?.(result)
//       } else {
//         const error = await response.json()
//         setError(`Processing failed: ${error.detail || 'Unknown error'}`)
//         setTranscription(realTimeText)
//       }
//     } catch (error) {
//       console.error('Final transcription failed:', error)
//       setError('Processing failed. Please try again.')
//       setTranscription(realTimeText)
//     } finally {
//       setIsProcessing(false)
//     }
//   }

//   const playRecording = () => {
//     if (audioChunksRef.current.length > 0) {
//       const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
//       const audioUrl = URL.createObjectURL(audioBlob)
      
//       if (audioRef.current) {
//         audioRef.current.src = audioUrl
//         audioRef.current.play()
//         setIsPlaying(true)
        
//         audioRef.current.onended = () => {
//           setIsPlaying(false)
//           URL.revokeObjectURL(audioUrl)
//         }
//       }
//     }
//   }

//   const downloadRecording = () => {
//     if (audioChunksRef.current.length > 0) {
//       const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
//       const url = URL.createObjectURL(audioBlob)
//       const a = document.createElement('a')
//       a.href = url
//       a.download = `${title || 'recording'}-${new Date().toISOString()}.webm`
//       a.click()
//       URL.revokeObjectURL(url)
//     }
//   }

//   const formatTime = (seconds: number) => {
//     const mins = Math.floor(seconds / 60)
//     const secs = seconds % 60
//     return `${mins}:${secs.toString().padStart(2, '0')}`
//   }

//   return (
//     <Card className="w-full">
//       <CardHeader>
//         <CardTitle className="flex items-center space-x-2">
//           <Mic className="w-5 h-5" />
//           <span>Real-Time Recording</span>
//         </CardTitle>
//       </CardHeader>
//       <CardContent className="space-y-6">
//         {error && (
//           <Alert variant="destructive">
//             <AlertCircle className="h-4 w-4" />
//             <AlertDescription>{error}</AlertDescription>
//           </Alert>
//         )}

//         {/* Recording Settings */}
//         {!isRecording && !completedResult && (
//           <div className="space-y-4">
//             <div className="space-y-2">
//               <Label htmlFor="title">Recording Title</Label>
//               <Input
//                 id="title"
//                 value={title}
//                 onChange={(e) => setTitle(e.target.value)}
//                 placeholder={`Recording ${new Date().toLocaleString()}`}
//               />
//             </div>
            
//             <div className="flex items-center space-x-2">
//               <Checkbox
//                 id="knowledge-base"
//                 checked={addToKnowledgeBase}
//                 onCheckedChange={(checked) => setAddToKnowledgeBase(checked as boolean)}
//               />
//               <Label htmlFor="knowledge-base" className="text-sm">
//                 Add to Knowledge Base for future queries
//               </Label>
//             </div>
//           </div>
//         )}

//         {/* Recording Controls */}
//         <div className="flex flex-col items-center space-y-4">
//           <div className="flex items-center space-x-4">
//             {!isRecording ? (
//               <Button
//                 onClick={startRecording}
//                 size="lg"
//                 disabled={isProcessing}
//                 className="bg-red-500 hover:bg-red-600 text-white rounded-full w-16 h-16"
//               >
//                 <Mic className="w-8 h-8" />
//               </Button>
//             ) : (
//               <Button
//                 onClick={stopRecording}
//                 size="lg"
//                 className="bg-gray-500 hover:bg-gray-600 text-white rounded-full w-16 h-16"
//               >
//                 <Square className="w-8 h-8" />
//               </Button>
//             )}
//           </div>

//           {/* Recording Status */}
//           {isRecording && (
//             <div className="text-center space-y-2">
//               <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
//                 🔴 Recording - {formatTime(recordingTime)}
//               </Badge>
              
//               {/* Audio Level Visualizer */}
//               <div className="flex items-center space-x-2">
//                 <Volume2 className="w-4 h-4 text-gray-500" />
//                 <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
//                   <div 
//                     className="h-full bg-green-500 transition-all duration-100"
//                     style={{ width: `${Math.min(100, (audioLevel / 255) * 100)}%` }}
//                   />
//                 </div>
//               </div>
//             </div>
//           )}

//           {/* Processing Status */}
//           {isProcessing && (
//             <div className="text-center space-y-2">
//               <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
//                 <div className="animate-spin w-4 h-4 mr-2 border-2 border-blue-600 border-t-transparent rounded-full"></div>
//                 Processing transcription and summary...
//               </Badge>
//             </div>
//           )}
//         </div>

//         {/* Real-time Transcription */}
//         {(isRecording || realTimeText) && (
//           <div className="space-y-2">
//             <h4 className="font-medium text-gray-900 flex items-center space-x-2">
//               <Mic className="w-4 h-4" />
//               <span>Real-time Transcription:</span>
//             </h4>
//             <div className="bg-gray-50 rounded-lg p-4 min-h-[100px]">
//               <p className="text-gray-700 text-sm leading-relaxed">
//                 {realTimeText || "Listening..."}
//                 {isRecording && <span className="animate-pulse ml-1">|</span>}
//               </p>
//             </div>
//           </div>
//         )}

//         {/* Final Results */}
//         {completedResult && (
//           <div className="space-y-4">
//             {/* Success Message */}
//             <Alert className="border-green-200 bg-green-50">
//               <CheckCircle className="h-4 w-4 text-green-600" />
//               <AlertDescription className="text-green-800">
//                 <div className="space-y-1">
//                   <p><strong>Recording processed successfully!</strong></p>
//                   <div className="flex items-center space-x-4 text-sm">
//                     <span className="flex items-center space-x-1">
//                       <Clock className="w-3 h-3" />
//                       <span>{formatTime(completedResult.duration_seconds)}</span>
//                     </span>
//                     {completedResult.stored_in_knowledge_base && (
//                       <span className="flex items-center space-x-1">
//                         <Database className="w-3 h-3" />
//                         <span>Stored in Knowledge Base</span>
//                       </span>
//                     )}
//                   </div>
//                 </div>
//               </AlertDescription>
//             </Alert>

//             {/* Final Transcription */}
//             <div className="space-y-2">
//               <h4 className="font-medium text-gray-900 flex items-center space-x-2">
//                 <FileText className="w-4 h-4" />
//                 <span>Final Transcription:</span>
//               </h4>
//               <div className="bg-blue-50 rounded-lg p-4">
//                 <p className="text-gray-800 leading-relaxed">{transcription}</p>
//               </div>
//             </div>

//             {/* Summary */}
//             {summary && (
//               <div className="space-y-2">
//                 <h4 className="font-medium text-gray-900 flex items-center space-x-2">
//                   <FileText className="w-4 h-4" />
//                   <span>Summary:</span>
//                 </h4>
//                 <div className="bg-purple-50 rounded-lg p-4">
//                   <div 
//                     className="text-gray-800 leading-relaxed prose prose-sm max-w-none"
//                     dangerouslySetInnerHTML={{ __html: summary.replace(/\n/g, '<br>') }}
//                   />
//                 </div>
//               </div>
//             )}
//           </div>
//         )}

//         {/* Playback Controls */}
//         {!isRecording && audioChunksRef.current.length > 0 && (
//           <div className="flex justify-center space-x-3">
//             <Button
//               onClick={playRecording}
//               variant="outline"
//               size="sm"
//               disabled={isPlaying || isProcessing}
//             >
//               {isPlaying ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
//               {isPlaying ? 'Playing' : 'Play'}
//             </Button>
            
//             <Button
//               onClick={downloadRecording}
//               variant="outline"
//               size="sm"
//               disabled={isProcessing}
//             >
//               <Download className="w-4 h-4 mr-2" />
//               Download
//             </Button>
//           </div>
//         )}

//         {/* Hidden audio element for playback */}
//         <audio ref={audioRef} style={{ display: 'none' }} />
//       </CardContent>
//     </Card>
//   )
// }