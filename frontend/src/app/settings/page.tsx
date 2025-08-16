// frontend/src/app/settings/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  User, 
  CreditCard, 
  Shield, 
  Bell, 
  Download,
  Trash2,
  Crown,
  Check,
  AlertCircle,
  Loader2
} from 'lucide-react'

interface UserStats {
  total_transcriptions: number
  monthly_usage: number
  usage_limit: number
  storage_used_mb: number
  subscription_tier: string
}

export default function SettingsPage() {
  const { user, token, updateUser } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [stats, setStats] = useState<UserStats | null>(null)
  
  const [profileForm, setProfileForm] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || ''
  })
  
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  useEffect(() => {
    if (token) {
      fetchUserStats()
    }
  }, [token])

  const fetchUserStats = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/stats`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch user stats:', error)
    }
  }

  const updateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(profileForm),
      })

      if (response.ok) {
        const updatedUser = await response.json()
        updateUser(updatedUser)
        setMessage('Profile updated successfully!')
      } else {
        const error = await response.json()
        setMessage(error.detail || 'Failed to update profile')
      }
    } catch (error) {
      setMessage('Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage('New passwords do not match')
      return
    }

    setLoading(true)
    setMessage('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password,
        }),
      })

      if (response.ok) {
        setMessage('Password changed successfully!')
        setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
      } else {
        const error = await response.json()
        setMessage(error.detail || 'Failed to change password')
      }
    } catch (error) {
      setMessage('Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const exportData = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/users/export-data`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `transcribeai-data-${new Date().toISOString().split('T')[0]}.json`
        a.click()
        URL.revokeObjectURL(url)
        setMessage('Data exported successfully!')
      }
    } catch (error) {
      setMessage('Failed to export data')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'billing', label: 'Billing', icon: CreditCard },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'data', label: 'Data & Privacy', icon: Download },
  ]

  const subscriptionPlans = [
    {
      name: 'Free',
      price: '$0',
      period: '/month',
      features: ['5 transcriptions/month', 'Basic summaries', '30min max length'],
      current: user?.subscription_tier === 'free'
    },
    {
      name: 'Pro',
      price: '$9.99',
      period: '/month',
      features: ['100 transcriptions/month', 'Advanced summaries', '2hr max length', 'Priority support'],
      current: user?.subscription_tier === 'pro',
      popular: true
    },
    {
      name: 'Business',
      price: '$29.99',
      period: '/month',
      features: ['Unlimited transcriptions', 'Team collaboration', 'API access', 'Custom integrations'],
      current: user?.subscription_tier === 'business'
    }
  ]

  return (
    <DashboardLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-2">Manage your account settings and preferences</p>
        </div>

        {message && (
          <Alert className={message.includes('successfully') ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <nav className="space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg text-left transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-50 text-blue-700 border border-blue-200'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <Card>
                <CardHeader>
                  <CardTitle>Profile Information</CardTitle>
                  <CardDescription>Update your personal information</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={updateProfile} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="first_name">First Name</Label>
                        <Input
                          id="first_name"
                          value={profileForm.first_name}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, first_name: e.target.value }))}
                        />
                      </div>
                      <div>
                        <Label htmlFor="last_name">Last Name</Label>
                        <Input
                          id="last_name"
                          value={profileForm.last_name}
                          onChange={(e) => setProfileForm(prev => ({ ...prev, last_name: e.target.value }))}
                        />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        value={user?.email}
                        disabled
                        className="bg-gray-50"
                      />
                      <p className="text-sm text-gray-500 mt-1">Email cannot be changed</p>
                    </div>
                    <Button type="submit" disabled={loading}>
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                      Update Profile
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* Billing Tab */}
            {activeTab === 'billing' && (
              <div className="space-y-6">
                {/* Current Plan */}
                <Card>
                  <CardHeader>
                    <CardTitle>Current Plan</CardTitle>
                    <CardDescription>You are currently on the {user?.subscription_tier} plan</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {stats && (
                      <div className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="text-center p-4 bg-gray-50 rounded-lg">
                            <p className="text-2xl font-bold text-gray-900">{stats.monthly_usage}</p>
                            <p className="text-sm text-gray-600">This Month</p>
                          </div>
                          <div className="text-center p-4 bg-gray-50 rounded-lg">
                            <p className="text-2xl font-bold text-gray-900">{stats.usage_limit}</p>
                            <p className="text-sm text-gray-600">Monthly Limit</p>
                          </div>
                          <div className="text-center p-4 bg-gray-50 rounded-lg">
                            <p className="text-2xl font-bold text-gray-900">{stats.storage_used_mb.toFixed(1)}MB</p>
                            <p className="text-sm text-gray-600">Storage Used</p>
                          </div>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div 
                            className="bg-blue-600 h-3 rounded-full transition-all"
                            style={{ width: `${(stats.monthly_usage / stats.usage_limit) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Subscription Plans */}
                <Card>
                  <CardHeader>
                    <CardTitle>Subscription Plans</CardTitle>
                    <CardDescription>Choose the plan that works best for you</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {subscriptionPlans.map((plan) => (
                        <div 
                          key={plan.name}
                          className={`relative p-6 rounded-lg border-2 ${
                            plan.current 
                              ? 'border-blue-500 bg-blue-50' 
                              : plan.popular 
                              ? 'border-purple-500 bg-purple-50' 
                              : 'border-gray-200'
                          }`}
                        >
                          {plan.popular && (
                            <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-purple-500">
                              Most Popular
                            </Badge>
                          )}
                          {plan.current && (
                            <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-blue-500">
                              Current Plan
                            </Badge>
                          )}
                          <div className="text-center">
                            <h3 className="text-xl font-semibold">{plan.name}</h3>
                            <div className="mt-2">
                              <span className="text-3xl font-bold">{plan.price}</span>
                              <span className="text-gray-600">{plan.period}</span>
                            </div>
                            <ul className="mt-4 space-y-2 text-sm">
                              {plan.features.map((feature, index) => (
                                <li key={index} className="flex items-center">
                                  <Check className="w-4 h-4 text-green-500 mr-2" />
                                  {feature}
                                </li>
                              ))}
                            </ul>
                            <Button 
                              className="w-full mt-6" 
                              variant={plan.current ? "outline" : "default"}
                              disabled={plan.current}
                            >
                              {plan.current ? 'Current Plan' : 'Upgrade'}
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Security Tab */}
            {activeTab === 'security' && (
              <Card>
                <CardHeader>
                  <CardTitle>Change Password</CardTitle>
                  <CardDescription>Update your password to keep your account secure</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={changePassword} className="space-y-4">
                    <div>
                      <Label htmlFor="current_password">Current Password</Label>
                      <Input
                        id="current_password"
                        type="password"
                        value={passwordForm.current_password}
                        onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="new_password">New Password</Label>
                      <Input
                        id="new_password"
                        type="password"
                        value={passwordForm.new_password}
                        onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="confirm_password">Confirm New Password</Label>
                      <Input
                        id="confirm_password"
                        type="password"
                        value={passwordForm.confirm_password}
                        onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                      />
                    </div>
                    <Button type="submit" disabled={loading}>
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                      Change Password
                    </Button>
                  </form>
                </CardContent>
              </Card>
            )}

            {/* Data & Privacy Tab */}
            {activeTab === 'data' && (
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Export Your Data</CardTitle>
                    <CardDescription>Download all your data including transcriptions and queries</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button onClick={exportData} disabled={loading}>
                      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Download className="w-4 h-4 mr-2" />}
                      Export Data
                    </Button>
                  </CardContent>
                </Card>

                <Card className="border-red-200">
                  <CardHeader>
                    <CardTitle className="text-red-600">Danger Zone</CardTitle>
                    <CardDescription>Irreversible actions that will permanently affect your account</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50">
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Account
                    </Button>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Placeholder for other tabs */}
            {activeTab === 'notifications' && (
              <Card>
                <CardHeader>
                  <CardTitle>Notification Preferences</CardTitle>
                  <CardDescription>Choose when and how you want to be notified</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-gray-600">Notification settings coming soon...</p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}