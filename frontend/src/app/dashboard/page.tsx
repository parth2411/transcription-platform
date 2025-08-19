// frontend/src/app/dashboard/page.tsx
'use client'

import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  FileText, 
  Clock, 
  MessageSquare, 
  Upload, 
  TrendingUp, 
  Play, 
  Mic
} from 'lucide-react'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface DashboardStats {
  total_transcriptions: number
  completed_transcriptions: number
  total_duration_hours: number
  total_queries: number
  monthly_usage: number
  usage_limit: number
  storage_used_mb: number
}

interface RecentTranscription {
  id: string
  title: string
  status: string
  created_at: string
  duration_seconds?: number
}

export default function DashboardPage() {
  const { user, token } = useAuth()
  const router = useRouter()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentTranscriptions, setRecentTranscriptions] = useState<RecentTranscription[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user || !token) {
      router.push('/login')
      return
    }

    fetchDashboardData()
  }, [user, token, router])

  const fetchDashboardData = async () => {
    try {
      // Fetch user stats
      const statsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/stats`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      
      if (statsResponse.ok) {
        const statsData = await statsResponse.json()
        setStats(statsData)
      }

      // Fetch recent transcriptions
      const transcriptionsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions?per_page=5`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      
      if (transcriptionsResponse.ok) {
        const transcriptionsData = await transcriptionsResponse.json()
        setRecentTranscriptions(transcriptionsData.transcriptions)
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Welcome Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.first_name}!
          </h1>
          <p className="text-gray-600 mt-2">
            Here's what's happening with your transcriptions today.
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Transcriptions</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.total_transcriptions || 0}
                  </p>
                </div>
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <FileText className="w-6 h-6 text-blue-600" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-sm text-gray-500">
                  {stats?.completed_transcriptions || 0} completed
                </p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Hours Processed</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.total_duration_hours || 0}h
                  </p>
                </div>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <Clock className="w-6 h-6 text-green-600" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-sm text-gray-500">This month</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">KB Queries</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.total_queries || 0}
                  </p>
                </div>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-purple-600" />
                </div>
              </div>
              <div className="mt-4">
                <p className="text-sm text-gray-500">Total searches</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Monthly Usage</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.monthly_usage || 0}/{stats?.usage_limit || 0}
                  </p>
                </div>
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <TrendingUp className="w-6 h-6 text-orange-600" />
                </div>
              </div>
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-orange-600 h-2 rounded-full" 
                    style={{ 
                      width: `${((stats?.monthly_usage || 0) / (stats?.usage_limit || 1)) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Get started with your next transcription
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Upload File */}
              <Link href="/transcriptions/new">
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-6 text-center">
                    <Upload className="w-8 h-8 text-blue-600 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900">Upload File</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Upload audio or video files
                    </p>
                  </CardContent>
                </Card>
              </Link>

              {/* From URL */}
              <Link href="/transcriptions/new?tab=url">
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-6 text-center">
                    <FileText className="w-8 h-8 text-green-600 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900">From URL</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Transcribe from YouTube URLs
                    </p>
                  </CardContent>
                </Card>
              </Link>

              {/* Real-time Recording */}
              <Link href="/realtime">
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-6 text-center">
                    <Mic className="w-8 h-8 text-red-600 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900">Real-time Recording</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Start live recording session
                    </p>
                  </CardContent>
                </Card>
              </Link>

              {/* Ask Questions */}
              <Link href="/knowledge">
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardContent className="p-6 text-center">
                    <MessageSquare className="w-8 h-8 text-purple-600 mx-auto mb-3" />
                    <h3 className="font-semibold text-gray-900">Ask Questions</h3>
                    <p className="text-sm text-gray-600 mt-1">
                      Query your knowledge base
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Recent Transcriptions */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Transcriptions</CardTitle>
              <CardDescription>
                Your latest transcription activity
              </CardDescription>
            </div>
            <Link href="/transcriptions">
              <Button variant="outline" size="sm">
                View All
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {recentTranscriptions.length > 0 ? (
              <div className="space-y-4">
                {recentTranscriptions.map((transcription) => (
                  <div key={transcription.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                        <FileText className="w-5 h-5 text-gray-600" />
                      </div>
                      <div>
                        <h4 className="font-medium text-gray-900">{transcription.title}</h4>
                        <div className="flex items-center space-x-2 text-sm text-gray-500">
                          <span>{formatDuration(transcription.duration_seconds)}</span>
                          <span>•</span>
                          <span>{new Date(transcription.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(transcription.status)}`}>
                        {transcription.status}
                      </span>
                      <Link href={`/transcriptions/${transcription.id}`}>
                        <Button variant="ghost" size="sm" className="hover:bg-blue-50">
                          <Play className="w-4 h-4" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="relative mx-auto mb-4 w-16 h-16 flex items-center justify-center">
                  <div className="absolute inset-0 bg-gray-200 rounded-full"></div>
                  <FileText className="w-8 h-8 text-gray-400 relative z-10" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">No transcriptions yet</h3>
                <p className="text-gray-600 mb-4">Get started by uploading your first audio file or try real-time recording</p>
                <div className="flex justify-center space-x-3">
                  <Link href="/transcriptions/new">
                    <Button>
                      <Upload className="w-4 h-4 mr-2" />
                      Upload File
                    </Button>
                  </Link>
                  <Link href="/realtime">
                    <Button variant="outline" className="border-red-200 text-red-600 hover:bg-red-50">
                      <Mic className="w-4 h-4 mr-2" />
                      Start Recording
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Usage Progress */}
        {stats && stats.usage_limit > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Monthly Usage</CardTitle>
              <CardDescription>
                {user?.subscription_tier} plan - {stats.monthly_usage} of {stats.usage_limit} transcriptions used
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between text-sm">
                  <span>Usage this month</span>
                  <span>{stats.monthly_usage}/{stats.usage_limit}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full transition-all ${
                      (stats.monthly_usage / stats.usage_limit) > 0.8 
                        ? 'bg-red-500' 
                        : (stats.monthly_usage / stats.usage_limit) > 0.6 
                        ? 'bg-yellow-500' 
                        : 'bg-green-500'
                    }`}
                    style={{ width: `${(stats.monthly_usage / stats.usage_limit) * 100}%` }}
                  ></div>
                </div>
                {(stats.monthly_usage / stats.usage_limit) > 0.8 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      You're approaching your monthly limit. Consider upgrading to Pro for unlimited transcriptions.
                    </p>
                    <Link href="/settings/billing">
                      <Button variant="outline" size="sm" className="mt-2">
                        Upgrade Plan
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}
// // frontend/src/app/dashboard/page.tsx
// 'use client'

// import { useAuth } from '@/components/auth/AuthProvider'
// import { DashboardLayout } from '@/components/layout/DashboardLayout'
// import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
// import { Button } from '@/components/ui/button'
// import { FileText, Clock, MessageSquare, Upload, TrendingUp, Play } from 'lucide-react'
// import Link from 'next/link'
// import { useEffect, useState } from 'react'
// import { useRouter } from 'next/navigation'

// interface DashboardStats {
//   total_transcriptions: number
//   completed_transcriptions: number
//   total_duration_hours: number
//   total_queries: number
//   monthly_usage: number
//   usage_limit: number
//   storage_used_mb: number
// }

// interface RecentTranscription {
//   id: string
//   title: string
//   status: string
//   created_at: string
//   duration_seconds?: number
// }

// export default function DashboardPage() {
//   const { user, token } = useAuth()
//   const router = useRouter()
//   const [stats, setStats] = useState<DashboardStats | null>(null)
//   const [recentTranscriptions, setRecentTranscriptions] = useState<RecentTranscription[]>([])
//   const [loading, setLoading] = useState(true)

//   useEffect(() => {
//     if (!user || !token) {
//       router.push('/login')
//       return
//     }

//     fetchDashboardData()
//   }, [user, token, router])

//   const fetchDashboardData = async () => {
//     try {
//       // Fetch user stats
//       const statsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/stats`, {
//         headers: {
//           Authorization: `Bearer ${token}`,
//         },
//       })
      
//       if (statsResponse.ok) {
//         const statsData = await statsResponse.json()
//         setStats(statsData)
//       }

//       // Fetch recent transcriptions
//       const transcriptionsResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions?per_page=5`, {
//         headers: {
//           Authorization: `Bearer ${token}`,
//         },
//       })
      
//       if (transcriptionsResponse.ok) {
//         const transcriptionsData = await transcriptionsResponse.json()
//         setRecentTranscriptions(transcriptionsData.transcriptions)
//       }
//     } catch (error) {
//       console.error('Failed to fetch dashboard data:', error)
//     } finally {
//       setLoading(false)
//     }
//   }

//   const formatDuration = (seconds?: number) => {
//     if (!seconds) return 'N/A'
//     const hours = Math.floor(seconds / 3600)
//     const minutes = Math.floor((seconds % 3600) / 60)
//     return `${hours}h ${minutes}m`
//   }

//   const getStatusColor = (status: string) => {
//     switch (status) {
//       case 'completed':
//         return 'bg-green-100 text-green-800'
//       case 'processing':
//         return 'bg-yellow-100 text-yellow-800'
//       case 'failed':
//         return 'bg-red-100 text-red-800'
//       default:
//         return 'bg-gray-100 text-gray-800'
//     }
//   }

//   if (loading) {
//     return (
//       <DashboardLayout>
//         <div className="flex items-center justify-center h-64">
//           <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
//         </div>
//       </DashboardLayout>
//     )
//   }

//   return (
//     <DashboardLayout>
//       <div className="space-y-8">
//         {/* Welcome Header */}
//         <div>
//           <h1 className="text-3xl font-bold text-gray-900">
//             Welcome back, {user?.first_name}!
//           </h1>
//           <p className="text-gray-600 mt-2">
//             Here's what's happening with your transcriptions today.
//           </p>
//         </div>

//         {/* Stats Grid */}
//         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
//           <Card>
//             <CardContent className="p-6">
//               <div className="flex items-center justify-between">
//                 <div>
//                   <p className="text-sm font-medium text-gray-600">Total Transcriptions</p>
//                   <p className="text-2xl font-bold text-gray-900">
//                     {stats?.total_transcriptions || 0}
//                   </p>
//                 </div>
//                 <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
//                   <FileText className="w-6 h-6 text-blue-600" />
//                 </div>
//               </div>
//               <div className="mt-4">
//                 <p className="text-sm text-gray-500">
//                   {stats?.completed_transcriptions || 0} completed
//                 </p>
//               </div>
//             </CardContent>
//           </Card>

//           <Card>
//             <CardContent className="p-6">
//               <div className="flex items-center justify-between">
//                 <div>
//                   <p className="text-sm font-medium text-gray-600">Hours Processed</p>
//                   <p className="text-2xl font-bold text-gray-900">
//                     {stats?.total_duration_hours || 0}h
//                   </p>
//                 </div>
//                 <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
//                   <Clock className="w-6 h-6 text-green-600" />
//                 </div>
//               </div>
//               <div className="mt-4">
//                 <p className="text-sm text-gray-500">This month</p>
//               </div>
//             </CardContent>
//           </Card>

//           <Card>
//             <CardContent className="p-6">
//               <div className="flex items-center justify-between">
//                 <div>
//                   <p className="text-sm font-medium text-gray-600">KB Queries</p>
//                   <p className="text-2xl font-bold text-gray-900">
//                     {stats?.total_queries || 0}
//                   </p>
//                 </div>
//                 <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
//                   <MessageSquare className="w-6 h-6 text-purple-600" />
//                 </div>
//               </div>
//               <div className="mt-4">
//                 <p className="text-sm text-gray-500">Total searches</p>
//               </div>
//             </CardContent>
//           </Card>

//           <Card>
//             <CardContent className="p-6">
//               <div className="flex items-center justify-between">
//                 <div>
//                   <p className="text-sm font-medium text-gray-600">Monthly Usage</p>
//                   <p className="text-2xl font-bold text-gray-900">
//                     {stats?.monthly_usage || 0}/{stats?.usage_limit || 0}
//                   </p>
//                 </div>
//                 <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
//                   <TrendingUp className="w-6 h-6 text-orange-600" />
//                 </div>
//               </div>
//               <div className="mt-4">
//                 <div className="w-full bg-gray-200 rounded-full h-2">
//                   <div 
//                     className="bg-orange-600 h-2 rounded-full" 
//                     style={{ 
//                       width: `${((stats?.monthly_usage || 0) / (stats?.usage_limit || 1)) * 100}%` 
//                     }}
//                   ></div>
//                 </div>
//               </div>
//             </CardContent>
//           </Card>
//         </div>

//         {/* Quick Actions */}
//         <Card>
//           <CardHeader>
//             <CardTitle>Quick Actions</CardTitle>
//             <CardDescription>
//               Get started with your next transcription
//             </CardDescription>
//           </CardHeader>
//           <CardContent>
//             <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
//               <Link href="/transcriptions/new">
//                 <Card className="cursor-pointer hover:shadow-md transition-shadow">
//                   <CardContent className="p-6 text-center">
//                     <Upload className="w-8 h-8 text-blue-600 mx-auto mb-3" />
//                     <h3 className="font-semibold text-gray-900">Upload File</h3>
//                     <p className="text-sm text-gray-600 mt-1">
//                       Upload audio or video files
//                     </p>
//                   </CardContent>
//                 </Card>
//               </Link>

//               <Link href="/transcriptions/new?tab=url">
//                 <Card className="cursor-pointer hover:shadow-md transition-shadow">
//                   <CardContent className="p-6 text-center">
//                     <FileText className="w-8 h-8 text-green-600 mx-auto mb-3" />
//                     <h3 className="font-semibold text-gray-900">From URL</h3>
//                     <p className="text-sm text-gray-600 mt-1">
//                       Transcribe YouTube or podcast URLs
//                     </p>
//                   </CardContent>
//                 </Card>
//               </Link>

//               <Link href="/knowledge">
//                 <Card className="cursor-pointer hover:shadow-md transition-shadow">
//                   <CardContent className="p-6 text-center">
//                     <MessageSquare className="w-8 h-8 text-purple-600 mx-auto mb-3" />
//                     <h3 className="font-semibold text-gray-900">Ask Questions</h3>
//                     <p className="text-sm text-gray-600 mt-1">
//                       Query your knowledge base
//                     </p>
//                   </CardContent>
//                 </Card>
//               </Link>
//             </div>
//           </CardContent>
//         </Card>

//         {/* Recent Transcriptions */}
//         <Card>
//           <CardHeader className="flex flex-row items-center justify-between">
//             <div>
//               <CardTitle>Recent Transcriptions</CardTitle>
//               <CardDescription>
//                 Your latest transcription activity
//               </CardDescription>
//             </div>
//             <Link href="/transcriptions">
//               <Button variant="outline" size="sm">
//                 View All
//               </Button>
//             </Link>
//           </CardHeader>
//           <CardContent>
//             {recentTranscriptions.length > 0 ? (
//               <div className="space-y-4">
//                 {recentTranscriptions.map((transcription) => (
//                   <div key={transcription.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
//                     <div className="flex items-center space-x-3">
//                       <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
//                         <FileText className="w-5 h-5 text-gray-600" />
//                       </div>
//                       <div>
//                         <h4 className="font-medium text-gray-900">{transcription.title}</h4>
//                         <div className="flex items-center space-x-2 text-sm text-gray-500">
//                           <span>{formatDuration(transcription.duration_seconds)}</span>
//                           <span>•</span>
//                           <span>{new Date(transcription.created_at).toLocaleDateString()}</span>
//                         </div>
//                       </div>
//                     </div>
//                     <div className="flex items-center space-x-3">
//                       <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(transcription.status)}`}>
//                         {transcription.status}
//                       </span>
//                       <Link href={`/transcriptions/${transcription.id}`}>
//                         <Button variant="ghost" size="sm">
//                           <Play className="w-4 h-4" />
//                         </Button>
//                       </Link>
//                     </div>
//                   </div>
//                 ))}
//               </div>
//             ) : (
//               <div className="text-center py-8">
//                 <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
//                 <h3 className="text-lg font-medium text-gray-900 mb-2">No transcriptions yet</h3>
//                 <p className="text-gray-600 mb-4">Get started by uploading your first audio file</p>
//                 <Link href="/transcriptions/new">
//                   <Button>
//                     <Upload className="w-4 h-4 mr-2" />
//                     Upload File
//                   </Button>
//                 </Link>
//               </div>
//             )}
//           </CardContent>
//         </Card>

//         {/* Usage Progress */}
//         {stats && stats.usage_limit > 0 && (
//           <Card>
//             <CardHeader>
//               <CardTitle>Monthly Usage</CardTitle>
//               <CardDescription>
//                 {user?.subscription_tier} plan - {stats.monthly_usage} of {stats.usage_limit} transcriptions used
//               </CardDescription>
//             </CardHeader>
//             <CardContent>
//               <div className="space-y-4">
//                 <div className="flex justify-between text-sm">
//                   <span>Usage this month</span>
//                   <span>{stats.monthly_usage}/{stats.usage_limit}</span>
//                 </div>
//                 <div className="w-full bg-gray-200 rounded-full h-3">
//                   <div 
//                     className={`h-3 rounded-full transition-all ${
//                       (stats.monthly_usage / stats.usage_limit) > 0.8 
//                         ? 'bg-red-500' 
//                         : (stats.monthly_usage / stats.usage_limit) > 0.6 
//                         ? 'bg-yellow-500' 
//                         : 'bg-green-500'
//                     }`}
//                     style={{ width: `${(stats.monthly_usage / stats.usage_limit) * 100}%` }}
//                   ></div>
//                 </div>
//                 {(stats.monthly_usage / stats.usage_limit) > 0.8 && (
//                   <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
//                     <p className="text-sm text-yellow-800">
//                       You're approaching your monthly limit. Consider upgrading to Pro for unlimited transcriptions.
//                     </p>
//                     <Link href="/settings/billing">
//                       <Button variant="outline" size="sm" className="mt-2">
//                         Upgrade Plan
//                       </Button>
//                     </Link>
//                   </div>
//                 )}
//               </div>
//             </CardContent>
//           </Card>
//         )}
//       </div>
//     </DashboardLayout>
//   )
// }