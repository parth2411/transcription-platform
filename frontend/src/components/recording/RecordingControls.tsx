// frontend/src/components/recording/RecordingControls.tsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Mic,
  StopCircle,
  Pause,
  Play,
  Volume2,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '@/components/auth/AuthProvider';

interface RecordingControlsProps {
  meetingId: string;
  onRecordingStart?: () => void;
  onRecordingStop?: (transcriptionId: string) => void;
}

interface TranscriptChunk {
  text: string;
  is_final: boolean;
  confidence: number;
  timestamp: string;
}

export function RecordingControls({
  meetingId,
  onRecordingStart,
  onRecordingStop
}: RecordingControlsProps) {
  const { token } = useAuth();

  // Recording state
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Audio state
  const [audioLevel, setAudioLevel] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // WebSocket state
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptChunk[]>([]);

  // Timer
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Audio level monitoring
  useEffect(() => {
    if (!isRecording || isPaused || !analyserRef.current) return;

    const updateAudioLevel = () => {
      const analyser = analyserRef.current;
      if (!analyser) return;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(dataArray);

      // Calculate average volume
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(average / 255); // Normalize to 0-1
    };

    const interval = setInterval(updateAudioLevel, 100);
    return () => clearInterval(interval);
  }, [isRecording, isPaused]);

  const startRecording = async () => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000
        }
      });

      streamRef.current = stream;

      // Setup audio context for visualization
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      mediaRecorderRef.current = mediaRecorder;

      // Start recording session on backend
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/recording/start`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            meeting_id: meetingId,
            audio_settings: {
              sample_rate: 16000,
              channels: 1
            }
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to start recording session');
      }

      const data = await response.json();
      setSessionId(data.session_id);

      // Connect WebSocket
      const ws = new WebSocket(
        `ws://localhost:8000${data.websocket_url}`
      );

      ws.onopen = () => {
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === 'connected') {
          console.log('Recording session started:', message.session_id);
        } else if (message.type === 'transcript') {
          // Add transcript chunk
          setTranscript(prev => [...prev, {
            text: message.text,
            is_final: message.is_final,
            confidence: message.confidence,
            timestamp: new Date().toISOString()
          }]);
        } else if (message.type === 'error') {
          setError(message.message);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
      };

      setWebsocket(ws);

      // Handle audio data
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          // Send audio chunk to backend
          ws.send(event.data);
        }
      };

      // Start recording
      mediaRecorder.start(1000); // Send chunks every 1 second
      setIsRecording(true);

      // Start timer
      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);

      onRecordingStart?.();

    } catch (err: any) {
      console.error('Error starting recording:', err);
      setError(err.message || 'Failed to start recording');
      cleanup();
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      setIsPaused(false);

      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    }
  };

  const stopRecording = async () => {
    try {
      // Stop MediaRecorder
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }

      // Close WebSocket
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify({ type: 'stop' }));
        websocket.close();
      }

      // Stop recording session on backend
      if (sessionId) {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/recording/stop`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              meeting_id: meetingId
            }),
          }
        );

        if (response.ok) {
          const data = await response.json();
          onRecordingStop?.(data.transcription_id);
        }
      }

      cleanup();

    } catch (err: any) {
      console.error('Error stopping recording:', err);
      setError(err.message || 'Failed to stop recording');
      cleanup();
    }
  };

  const cleanup = () => {
    // Stop all tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Clear timer
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    // Reset state
    setIsRecording(false);
    setIsPaused(false);
    setDuration(0);
    setAudioLevel(0);
    setWebsocket(null);
    setSessionId(null);
    mediaRecorderRef.current = null;
    analyserRef.current = null;
  };

  const formatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-4">
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Recording Controls */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Record/Stop Button */}
              {!isRecording ? (
                <Button
                  size="lg"
                  onClick={startRecording}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  <Mic className="w-5 h-5 mr-2" />
                  Start Recording
                </Button>
              ) : (
                <Button
                  size="lg"
                  onClick={stopRecording}
                  variant="destructive"
                >
                  <StopCircle className="w-5 h-5 mr-2" />
                  Stop Recording
                </Button>
              )}

              {/* Pause/Resume Button */}
              {isRecording && (
                <Button
                  size="lg"
                  onClick={isPaused ? resumeRecording : pauseRecording}
                  variant="outline"
                >
                  {isPaused ? (
                    <>
                      <Play className="w-5 h-5 mr-2" />
                      Resume
                    </>
                  ) : (
                    <>
                      <Pause className="w-5 h-5 mr-2" />
                      Pause
                    </>
                  )}
                </Button>
              )}
            </div>

            {/* Duration */}
            <div className="flex items-center gap-4">
              {isRecording && (
                <>
                  {/* Audio Level Indicator */}
                  <div className="flex items-center gap-2">
                    <Volume2 className="w-5 h-5 text-gray-500" />
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 transition-all duration-100"
                        style={{ width: `${audioLevel * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Time Display */}
                  <div className="flex items-center gap-2">
                    {!isPaused && (
                      <div className="w-3 h-3 bg-red-600 rounded-full animate-pulse" />
                    )}
                    <span className="text-2xl font-mono font-bold">
                      {formatDuration(duration)}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Real-time Transcript */}
      {transcript.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">Live Transcription</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {transcript.map((chunk, idx) => (
                <div
                  key={idx}
                  className={`text-sm ${
                    chunk.is_final ? 'text-gray-900' : 'text-gray-500 italic'
                  }`}
                >
                  {chunk.text}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
