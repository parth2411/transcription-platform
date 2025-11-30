// frontend/src/app/page.tsx
'use client'

import { useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import Image from 'next/image'
import {
  FileAudio,
  Play,
  MessageSquare,
  Zap,
  Calendar,
  Mic,
  Brain,
  CheckCircle,
  Clock,
  Users,
  Sparkles,
  Globe,
  Shield,
  ArrowRight,
  Star,
  Video,
  FileText,
  Search,
  Tag,
  Folders,
  BarChart
} from 'lucide-react'

export default function HomePage() {
  const { user } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (user) {
      router.push('/dashboard')
    }
  }, [user, router])

  if (user) {
    return null // Will redirect to dashboard
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <FileAudio className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold text-gray-900">TranscribeAI</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/login">
                <Button variant="ghost" size="lg">Sign In</Button>
              </Link>
              <Link href="/register">
                <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700">
                  Get Started Free
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <Badge className="mb-4 bg-blue-100 text-blue-700 hover:bg-blue-100">
            <Sparkles className="w-3 h-3 mr-1" />
            AI-Powered Meeting Assistant
          </Badge>
          <h1 className="text-5xl sm:text-7xl font-bold text-gray-900 mb-6 leading-tight">
            Never Take Meeting
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-600">
              Notes Again
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-10 max-w-3xl mx-auto leading-relaxed">
            Record, transcribe, and organize your meetings automatically. Connect your calendar,
            get real-time transcriptions, AI-generated notes, and instant access to everything discussed.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4 mb-12">
            <Link href="/register">
              <Button size="lg" className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-8 py-6 text-lg">
                <Play className="w-5 h-5 mr-2" />
                Start Free Trial
              </Button>
            </Link>
            <Link href="#features">
              <Button size="lg" variant="outline" className="px-8 py-6 text-lg">
                See How It Works
                <ArrowRight className="w-5 h-5 ml-2" />
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto pt-8 border-t">
            <div>
              <div className="text-3xl font-bold text-gray-900">98%</div>
              <div className="text-sm text-gray-600">Accuracy</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900">5min</div>
              <div className="text-sm text-gray-600">Setup Time</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-gray-900">10x</div>
              <div className="text-sm text-gray-600">Faster</div>
            </div>
          </div>
        </div>
      </section>

      {/* Calendar Integration Section */}
      <section className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <Badge className="mb-4 bg-green-100 text-green-700 hover:bg-green-100">
              <Calendar className="w-3 h-3 mr-1" />
              Seamless Integration
            </Badge>
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Syncs With Your Calendar
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Connect Google, Microsoft, or Apple Calendar in one click. Your meetings appear automatically.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <Card className="border-2 hover:border-blue-500 transition-all">
              <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <Image
                    src="/icons/search.png"
                    alt="Google Calendar"
                    width={64}
                    height={64}
                    className="object-contain"
                  />
                </div>
                <CardTitle>Google Calendar</CardTitle>
                <CardDescription>Gmail, Google Workspace</CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-blue-500 transition-all">
              <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <Image
                    src="/icons/outlook.png"
                    alt="Microsoft Outlook"
                    width={64}
                    height={64}
                    className="object-contain"
                  />
                </div>
                <CardTitle>Microsoft Outlook</CardTitle>
                <CardDescription>Outlook, Microsoft 365</CardDescription>
              </CardHeader>
            </Card>

            <Card className="border-2 hover:border-blue-500 transition-all">
              <CardHeader className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 relative">
                  <Image
                    src="/icons/apple-logo.png"
                    alt="Apple Calendar"
                    width={64}
                    height={64}
                    className="object-contain"
                  />
                </div>
                <CardTitle>iCloud Calendar</CardTitle>
                <CardDescription>Apple Calendar, macOS</CardDescription>
              </CardHeader>
            </Card>
          </div>

          <div className="flex items-center justify-center gap-12 text-gray-400">
            <div className="flex items-center gap-2">
              <Video className="w-5 h-5" />
              <span className="text-sm">Zoom</span>
            </div>
            <div className="flex items-center gap-2">
              <Video className="w-5 h-5" />
              <span className="text-sm">Google Meet</span>
            </div>
            <div className="flex items-center gap-2">
              <Video className="w-5 h-5" />
              <span className="text-sm">Microsoft Teams</span>
            </div>
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              <span className="text-sm">In-Person</span>
            </div>
          </div>
        </div>
      </section>

      {/* Real-time Transcription Section */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <Badge className="mb-4 bg-red-100 text-red-700 hover:bg-red-100">
                <Mic className="w-3 h-3 mr-1" />
                Real-Time Recording
              </Badge>
              <h2 className="text-4xl font-bold text-gray-900 mb-6">
                See Every Word As It's Spoken
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Our AI transcribes meetings in real-time with industry-leading accuracy.
                See live captions, never miss a detail, and stay focused on the conversation.
              </p>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Live Transcription</div>
                    <div className="text-gray-600">Words appear instantly as they're spoken</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Speaker Detection</div>
                    <div className="text-gray-600">Automatically identifies different speakers</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Multi-Language Support</div>
                    <div className="text-gray-600">Transcribe in 50+ languages</div>
                  </div>
                </li>
              </ul>
            </div>
            <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-2xl p-8 text-white">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">Recording</span>
                <span className="text-sm text-gray-400 ml-auto">00:15:42</span>
              </div>
              <div className="space-y-4">
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-1">Speaker 1</div>
                  <div className="text-sm">Let's discuss the Q4 roadmap and prioritize features...</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="text-xs text-gray-400 mb-1">Speaker 2</div>
                  <div className="text-sm">Great! I think we should focus on the calendar integration first.</div>
                </div>
                <div className="bg-blue-500/20 rounded-lg p-4 border border-blue-500/50">
                  <div className="text-xs text-blue-300 mb-1">Speaker 1 • Now</div>
                  <div className="text-sm">Absolutely. We can ship that in two weeks...</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* AI Features Section */}
      <section className="bg-gradient-to-br from-purple-50 to-blue-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <Badge className="mb-4 bg-purple-100 text-purple-700 hover:bg-purple-100">
              <Brain className="w-3 h-3 mr-1" />
              AI-Powered
            </Badge>
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Smart Notes, Zero Effort
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              AI automatically generates structured notes, extracts action items, and creates searchable knowledge.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader>
                <FileText className="w-10 h-10 text-blue-600 mb-3" />
                <CardTitle className="text-lg">Auto Summaries</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 text-sm">
                  Get concise summaries with key points, decisions, and next steps automatically.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CheckCircle className="w-10 h-10 text-green-600 mb-3" />
                <CardTitle className="text-lg">Action Items</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 text-sm">
                  AI extracts tasks, assigns owners, and tracks follow-ups from conversations.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <MessageSquare className="w-10 h-10 text-purple-600 mb-3" />
                <CardTitle className="text-lg">Chat with Meetings</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 text-sm">
                  Ask questions about past meetings and get instant AI-powered answers.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <Search className="w-10 h-10 text-orange-600 mb-3" />
                <CardTitle className="text-lg">Smart Search</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 text-sm">
                  Find any topic, decision, or moment across all your meetings instantly.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Organization Features */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="order-2 lg:order-1">
              <Card className="border-2">
                <CardHeader className="bg-gray-50">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900">Library</h3>
                    <div className="flex gap-2">
                      <Badge variant="secondary">All</Badge>
                      <Badge>Meetings</Badge>
                      <Badge variant="secondary">Uploads</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-6 space-y-3">
                  <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                    <Calendar className="w-8 h-8 text-blue-600" />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Q4 Planning Meeting</div>
                      <div className="text-xs text-gray-500">45 min • Today</div>
                    </div>
                    <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
                  </div>
                  <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50">
                    <Calendar className="w-8 h-8 text-gray-400" />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Customer Interview #5</div>
                      <div className="text-xs text-gray-500">30 min • Yesterday</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50">
                    <FileAudio className="w-8 h-8 text-gray-400" />
                    <div className="flex-1">
                      <div className="font-medium text-sm">Product Demo Recording</div>
                      <div className="text-xs text-gray-500">1h 15min • 2 days ago</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="order-1 lg:order-2">
              <Badge className="mb-4 bg-orange-100 text-orange-700 hover:bg-orange-100">
                <Folders className="w-3 h-3 mr-1" />
                Organization
              </Badge>
              <h2 className="text-4xl font-bold text-gray-900 mb-6">
                Everything Organized Automatically
              </h2>
              <p className="text-lg text-gray-600 mb-8">
                Meetings are automatically categorized and searchable. Use folders, tags, and filters to stay organized.
              </p>
              <ul className="space-y-4">
                <li className="flex items-start gap-3">
                  <Tag className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Smart Categories</div>
                    <div className="text-gray-600">Meetings, uploads, and recordings auto-categorized</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Folders className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Folder System</div>
                    <div className="text-gray-600">Organize by project, team, or client</div>
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <Star className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" />
                  <div>
                    <div className="font-semibold text-gray-900">Favorites & Tags</div>
                    <div className="text-gray-600">Mark important meetings and add custom tags</div>
                  </div>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-gradient-to-br from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600">
              Get started in minutes, no credit card required
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-blue-600">
                1
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Connect Calendar</h3>
              <p className="text-gray-600 text-sm">
                Link Google, Microsoft, or Apple Calendar in one click
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-blue-600">
                2
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Start Recording</h3>
              <p className="text-gray-600 text-sm">
                Click record when your meeting starts - that's it!
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-blue-600">
                3
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Get AI Notes</h3>
              <p className="text-gray-600 text-sm">
                Receive summaries, action items, and transcripts automatically
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-blue-600">
                4
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Search & Share</h3>
              <p className="text-gray-600 text-sm">
                Find anything instantly and share notes with your team
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section className="py-20 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div>
              <Shield className="w-12 h-12 text-green-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Enterprise Security</h3>
              <p className="text-gray-400 text-sm">
                Bank-level encryption and SOC 2 compliance
              </p>
            </div>
            <div>
              <Globe className="w-12 h-12 text-blue-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Privacy First</h3>
              <p className="text-gray-400 text-sm">
                Your data is yours. We never train AI on your content
              </p>
            </div>
            <div>
              <Clock className="w-12 h-12 text-purple-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">99.9% Uptime</h3>
              <p className="text-gray-400 text-sm">
                Always available when you need it
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 bg-gradient-to-r from-blue-500 to-purple-600 text-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl sm:text-5xl font-bold mb-6">
            Ready to Transform Your Meetings?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join thousands of teams using TranscribeAI to save time and stay organized
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link href="/register">
              <Button size="lg" className="bg-white text-blue-600 hover:bg-gray-100 px-8 py-6 text-lg">
                <Play className="w-5 h-5 mr-2" />
                Start Free Trial
              </Button>
            </Link>
            <Link href="#features">
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10 px-8 py-6 text-lg">
                View Demo
              </Button>
            </Link>
          </div>
          <p className="mt-6 text-sm opacity-75">
            No credit card required • Cancel anytime • 14-day free trial
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Features</a></li>
                <li><a href="#" className="hover:text-white">Pricing</a></li>
                <li><a href="#" className="hover:text-white">Use Cases</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">About</a></li>
                <li><a href="#" className="hover:text-white">Blog</a></li>
                <li><a href="#" className="hover:text-white">Careers</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Resources</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Documentation</a></li>
                <li><a href="#" className="hover:text-white">Help Center</a></li>
                <li><a href="#" className="hover:text-white">API</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white">Privacy</a></li>
                <li><a href="#" className="hover:text-white">Terms</a></li>
                <li><a href="#" className="hover:text-white">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <FileAudio className="w-5 h-5 text-white" />
              </div>
              <span className="text-white font-bold">TranscribeAI</span>
            </div>
            <p className="text-sm">
              © 2024 TranscribeAI. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
