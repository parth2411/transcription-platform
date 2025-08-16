// frontend/src/app/knowledge/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Search, 
  MessageSquare, 
  Clock, 
  TrendingUp, 
  BarChart3,
  Trash2,
  Send,
  Loader2,
  BookOpen,
  FileText
} from 'lucide-react'

interface QueryResult {
  answer: string
  sources: Array<{
    id: string
    title: string
    date: string
    confidence: number
    type: string
  }>
  confidence: number
  query_id: string
}

interface QueryHistory {
  id: string
  query: string
  answer: string
  confidence?: number
  response_time_ms?: number
  created_at: string
  source_count: number
}

interface KnowledgeStats {
  transcription_count: number
  vector_count: number
  query_count: number
  total_duration_hours: number
  collection_name: string
}

export default function KnowledgeBasePage() {
  const { token } = useAuth()
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<QueryResult | null>(null)
  const [history, setHistory] = useState<QueryHistory[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [showHistory, setShowHistory] = useState(false)

  useEffect(() => {
    if (!token) return
    fetchStats()
    fetchHistory()
  }, [token])

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
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/history?per_page=10`, {
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

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    setLoading(true)
    setResult(null)

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query, limit: 5 }),
      })

      if (response.ok) {
        const data = await response.json()
        setResult(data)
        setQuery('') // Clear input after successful query
        fetchHistory() // Refresh history
        fetchStats() // Refresh stats
      } else {
        const error = await response.json()
        console.error('Query failed:', error)
      }
    } catch (error) {
      console.error('Query failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const clearHistory = async () => {
    if (!confirm('Are you sure you want to clear all query history?')) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/knowledge/history`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        setHistory([])
        fetchStats()
      }
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800'
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-gray-600 mt-2">Ask questions about your transcriptions and get AI-powered answers</p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Transcriptions</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.transcription_count}</p>
                  </div>
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-6 h-6 text-blue-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Knowledge Vectors</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.vector_count}</p>
                  </div>
                  <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-6 h-6 text-green-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Queries</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.query_count}</p>
                  </div>
                  <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-purple-600" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Content Hours</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.total_duration_hours}h</p>
                  </div>
                  <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                    <Clock className="w-6 h-6 text-orange-600" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Query Interface */}
        <Card>
          <CardHeader>
            <CardTitle>Ask a Question</CardTitle>
            <CardDescription>
              Search through all your transcriptions and get contextual answers
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleQuery} className="space-y-4">
              <div className="flex space-x-4">
                <div className="flex-1 relative">
                  <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                  <Input
                    placeholder="Ask anything about your transcriptions..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="pl-10 text-lg"
                    disabled={loading}
                  />
                </div>
                <Button type="submit" disabled={loading || !query.trim()}>
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </form>

            {/* Query Result */}
            {result && (
              <div className="mt-6 space-y-4">
                <div className="border border-gray-200 rounded-lg p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900">Answer</h3>
                    <Badge className={getConfidenceColor(result.confidence)}>
                      {(result.confidence * 100).toFixed(0)}% confidence
                    </Badge>
                  </div>
                  <div className="prose max-w-none">
                    <p className="text-gray-700 leading-relaxed">{result.answer}</p>
                  </div>
                </div>

                {/* Sources */}
                {result.sources.length > 0 && (
                  <div className="border border-gray-200 rounded-lg p-6">
                    <h4 className="font-semibold text-gray-900 mb-3">Sources</h4>
                    <div className="space-y-3">
                      {result.sources.map((source, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center space-x-3">
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                            <div>
                              <p className="font-medium text-gray-900">{source.title}</p>
                              <p className="text-sm text-gray-500">
                                {source.date} • {source.type}
                              </p>
                            </div>
                          </div>
                          <Badge variant="outline">
                            {(source.confidence * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Query History and Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Recent Queries */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Recent Queries</CardTitle>
                  <CardDescription>Your latest questions and answers</CardDescription>
                </div>
                <div className="flex space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowHistory(!showHistory)}
                  >
                    {showHistory ? 'Hide' : 'Show'} All
                  </Button>
                  {history.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={clearHistory}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {history.length > 0 ? (
                  <div className="space-y-4">
                    {(showHistory ? history : history.slice(0, 3)).map((item) => (
                      <div key={item.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium text-gray-900 line-clamp-2">{item.query}</h4>
                          <span className="text-xs text-gray-500 ml-4 whitespace-nowrap">
                            {new Date(item.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 line-clamp-3 mb-3">{item.answer}</p>
                        <div className="flex items-center space-x-4 text-xs text-gray-500">
                          <span>{item.source_count} sources</span>
                          {item.confidence && (
                            <span>{(item.confidence * 100).toFixed(0)}% confidence</span>
                          )}
                          {item.response_time_ms && (
                            <span>{item.response_time_ms}ms</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">No queries yet. Ask your first question above!</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Common knowledge base operations</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="outline">
                  <TrendingUp className="w-4 h-4 mr-2" />
                  View Analytics
                </Button>
                <Button className="w-full justify-start" variant="outline">
                  <Search className="w-4 h-4 mr-2" />
                  Advanced Search
                </Button>
                <Button 
                  className="w-full justify-start text-red-600 hover:text-red-700" 
                  variant="outline"
                  onClick={clearHistory}
                  disabled={history.length === 0}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  Clear History
                </Button>
              </CardContent>
            </Card>

            {/* Sample Questions */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Sample Questions</CardTitle>
                <CardDescription>Try asking these questions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {[
                  "What were the main discussion points?",
                  "Summarize the key decisions made",
                  "What action items were mentioned?",
                  "Who spoke the most in the meetings?"
                ].map((sampleQuery, index) => (
                  <button
                    key={index}
                    onClick={() => setQuery(sampleQuery)}
                    className="w-full text-left p-3 text-sm text-gray-600 hover:bg-gray-50 rounded-lg border border-gray-200 transition-colors"
                  >
                    "{sampleQuery}"
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}