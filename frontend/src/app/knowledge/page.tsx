// frontend/src/app/knowledge/enhanced-page.tsx
// Enhanced knowledge base page with chat interface
// Replace the content of page.tsx with this file

'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Send,
  Loader2,
  MessageSquare,
  Sparkles,
  FileText,
  Clock,
  TrendingUp,
  BookOpen,
  Search,
  History,
  Lightbulb
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    title: string
    confidence: number
    date: string
  }>
  timestamp: Date
}

interface KnowledgeStats {
  transcription_count: number
  vector_count: number
  query_count: number
  total_duration_hours: number
}

interface QueryHistory {
  id: string
  query: string
  answer: string
  confidence?: number
  created_at: string
}

export default function EnhancedKnowledgePage() {
  const { token } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [chatMode, setChatMode] = useState<'all' | 'meetings'>('all')
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [history, setHistory] = useState<QueryHistory[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!token) return
    fetchStats()
    fetchHistory()

    // Add welcome message
    setMessages([{
      id: '0',
      role: 'assistant',
      content: "👋 Hi! I'm your AI assistant. I can help you search through all your transcriptions and answer questions based on your knowledge base. What would you like to know?",
      timestamp: new Date()
    }])
  }, [token])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const fetchStats = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/stats`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/history?per_page=5`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setHistory(data.queries)
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: input,
          limit: 5
        }),
      })

      if (response.ok) {
        const result = await response.json()

        // Map backend sources to frontend format
        const mappedSources = result.sources?.map((source: any) => ({
          title: source.title || 'Untitled',
          confidence: source.similarity || 0,
          date: source.created_at || new Date().toISOString(),
          transcription_id: source.transcription_id
        })) || []

        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: result.answer,
          sources: mappedSources,
          timestamp: new Date()
        }

        setMessages(prev => [...prev, assistantMessage])
        fetchHistory() // Refresh history
      } else {
        throw new Error('Query failed')
      }
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "Sorry, I encountered an error processing your question. Please try again.",
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const loadHistoryQuery = (query: string) => {
    setInput(query)
    setShowHistory(false)
  }

  const suggestedQueries = [
    "What are the main topics discussed?",
    "Summarize the key points",
    "What decisions were made?",
    "What action items were mentioned?"
  ]

  return (
    <DashboardLayout>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chat Area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
            <p className="text-gray-600 mt-1">Ask anything about your transcriptions</p>
          </div>

          {/* Chat Container */}
          <Card className="h-[600px] flex flex-col">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {message.role === 'assistant' && (
                      <div className="flex items-center space-x-2 mb-2">
                        <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
                          <Sparkles className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-xs font-medium text-gray-600">AI Assistant</span>
                      </div>
                    )}

                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>

                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
                        <p className="text-xs font-medium text-gray-600">Sources:</p>
                        {message.sources.map((source, idx) => (
                          <div key={idx} className="flex items-center justify-between text-xs">
                            <span className="text-gray-700">{source.title}</span>
                            <Badge variant="secondary" className="text-xs">
                              {Math.round(source.confidence * 100)}%
                            </Badge>
                          </div>
                        ))}
                      </div>
                    )}

                    <p className="text-xs mt-2 opacity-60">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                      <span className="text-sm text-gray-600">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t p-4">
              {/* Suggested Queries */}
              {messages.length === 1 && (
                <div className="mb-3 flex flex-wrap gap-2">
                  {suggestedQueries.map((query, idx) => (
                    <button
                      key={idx}
                      onClick={() => setInput(query)}
                      className="px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded-full hover:bg-blue-100 transition-colors"
                    >
                      <Lightbulb className="w-3 h-3 inline mr-1" />
                      {query}
                    </button>
                  ))}
                </div>
              )}

              <form onSubmit={handleSubmit} className="flex space-x-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question about your transcriptions..."
                  disabled={loading}
                  className="flex-1"
                />
                <Button type="submit" disabled={loading || !input.trim()}>
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </form>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Stats */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-blue-600" />
                Knowledge Base Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Transcriptions</span>
                <span className="text-lg font-bold text-gray-900">
                  {stats?.transcription_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Knowledge Chunks</span>
                <span className="text-lg font-bold text-gray-900">
                  {stats?.vector_count || 0}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Total Hours</span>
                <span className="text-lg font-bold text-gray-900">
                  {stats?.total_duration_hours || 0}h
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">Queries Made</span>
                <span className="text-lg font-bold text-gray-900">
                  {stats?.query_count || 0}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Recent Queries */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <History className="w-5 h-5 mr-2 text-purple-600" />
                Recent Queries
              </CardTitle>
            </CardHeader>
            <CardContent>
              {history.length > 0 ? (
                <div className="space-y-3">
                  {history.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => loadHistoryQuery(item.query)}
                      className="w-full text-left p-3 rounded-lg hover:bg-gray-50 transition-colors group"
                    >
                      <p className="text-sm font-medium text-gray-900 line-clamp-1 group-hover:text-blue-600">
                        {item.query}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(item.created_at).toLocaleDateString()}
                      </p>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6">
                  <MessageSquare className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">No queries yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Tips */}
          <Card className="bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <Lightbulb className="w-5 h-5 mr-2 text-yellow-600" />
                Pro Tips
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-gray-700">
              <p>• Ask specific questions for better results</p>
              <p>• Reference dates or topics for context</p>
              <p>• Use natural language queries</p>
              <p>• Check sources for accuracy</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  )
}
