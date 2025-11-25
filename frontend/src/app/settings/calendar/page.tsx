// frontend/src/app/settings/calendar/page.tsx
'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Calendar,
  CheckCircle,
  XCircle,
  RefreshCw,
  Trash2,
  AlertCircle,
  ExternalLink
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import {
  detectUserPlatform,
  getPlatformDisplayName,
  getCalendarIcon,
  getCalendarIconPath,
  getCalendarDisplayName,
  getCalendarDescription
} from '@/lib/platform-detection';
import appleIcon from '@/assets/apple-logo.png';
import outlookIcon from '@/assets/outlook.png';
import googleIcon from '@/assets/search.png';

interface CalendarConnection {
  id: string;
  provider: string;
  calendar_name: string;
  is_active: boolean;
  sync_enabled: boolean;
  auto_record_meetings: boolean;
  last_synced_at: string | null;
  created_at: string;
}

export default function CalendarSettingsPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [platform, setPlatform] = useState<ReturnType<typeof detectUserPlatform> | null>(null);
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    // Detect platform
    const detected = detectUserPlatform();
    setPlatform(detected);

    // Check for OAuth callback params
    const success = searchParams.get('success');
    const error = searchParams.get('error');
    const provider = searchParams.get('provider');

    if (success === 'true' && provider) {
      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 5000);
    }

    if (error === 'true') {
      setShowError(true);
      setErrorMessage('Failed to connect calendar. Please try again.');
      setTimeout(() => setShowError(false), 5000);
    }

    loadConnections();
  }, []);

  const loadConnections = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/calendar/connections`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConnections(data);
      }
    } catch (error) {
      console.error('Failed to load calendar connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectCalendar = async (provider: string) => {
    if (!token) return;

    try {
      // Step 1: Get OAuth URL from backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/calendar/${provider}/auth`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to initiate OAuth');
      }

      const { auth_url } = await response.json();

      // Step 2: Redirect user to provider's OAuth page
      // User authorizes there, then gets redirected back
      window.location.href = auth_url;

    } catch (error) {
      console.error('Failed to connect calendar:', error);
      setShowError(true);
      setErrorMessage('Failed to initiate calendar connection. Please try again.');
      setTimeout(() => setShowError(false), 5000);
    }
  };

  const handleSyncCalendar = async (connectionId: string) => {
    if (!token) return;

    setSyncing(connectionId);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/calendar/sync/${connectionId}`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        await loadConnections();
        setShowSuccess(true);
        setTimeout(() => setShowSuccess(false), 3000);
      }
    } catch (error) {
      console.error('Failed to sync calendar:', error);
      setShowError(true);
      setErrorMessage('Failed to sync calendar. Please try again.');
      setTimeout(() => setShowError(false), 5000);
    } finally {
      setSyncing(null);
    }
  };

  const handleDisconnectCalendar = async (connectionId: string, provider: string) => {
    if (!token || !confirm(`Are you sure you want to disconnect your ${provider} calendar?`)) {
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/calendar/connections/${connectionId}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        await loadConnections();
      }
    } catch (error) {
      console.error('Failed to disconnect calendar:', error);
      setShowError(true);
      setErrorMessage('Failed to disconnect calendar. Please try again.');
      setTimeout(() => setShowError(false), 5000);
    }
  };

  const handleToggleSyncEnabled = async (connectionId: string, enabled: boolean) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/calendar/connections/${connectionId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ sync_enabled: enabled }),
        }
      );

      if (response.ok) {
        await loadConnections();
      }
    } catch (error) {
      console.error('Failed to update sync settings:', error);
    }
  };

  const handleToggleAutoRecord = async (connectionId: string, enabled: boolean) => {
    if (!token) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/calendar/connections/${connectionId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ auto_record_meetings: enabled }),
        }
      );

      if (response.ok) {
        await loadConnections();
      }
    } catch (error) {
      console.error('Failed to update auto-record settings:', error);
    }
  };

  const getConnectionForProvider = (provider: string) => {
    return connections.find(c => c.provider === provider && c.is_active);
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <RefreshCw className="w-6 h-6 animate-spin" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-lg mb-6">
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Calendar className="w-8 h-8" />
            Calendar Connections
          </h1>
          <p className="mt-2">
            Connect your calendar to automatically sync meetings and start recordings
          </p>
        </div>

        {/* Success/Error Alerts */}
        {showSuccess && (
          <Alert className="bg-green-50 border-green-200">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              Calendar connected successfully! Your meetings will sync automatically.
            </AlertDescription>
          </Alert>
        )}

        {showError && (
          <Alert className="bg-red-50 border-red-200">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800">
              {errorMessage}
            </AlertDescription>
          </Alert>
        )}

        {/* Platform Detection Banner */}
        {platform && (
          <Card className="bg-blue-50 border-blue-200">
            <CardHeader>
              <CardTitle className="text-blue-900 text-lg">
                📱 We detected you're using {getPlatformDisplayName(platform.os)}
              </CardTitle>
              <CardDescription className="text-blue-700">
                We recommend connecting your {getCalendarDisplayName(platform.primarySuggestion)} for the best experience.
              </CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Calendar Provider Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Google Calendar */}
          <CalendarProviderCard
            provider="google"
            isPrimary={platform?.primarySuggestion === 'google'}
            connection={getConnectionForProvider('google')}
            onConnect={() => handleConnectCalendar('google')}
            onDisconnect={(id) => handleDisconnectCalendar(id, 'google')}
            onSync={handleSyncCalendar}
            onToggleSync={handleToggleSyncEnabled}
            onToggleAutoRecord={handleToggleAutoRecord}
            syncing={syncing}
          />

          {/* Microsoft Outlook */}
          <CalendarProviderCard
            provider="microsoft"
            isPrimary={platform?.primarySuggestion === 'microsoft'}
            connection={getConnectionForProvider('microsoft')}
            onConnect={() => handleConnectCalendar('microsoft')}
            onDisconnect={(id) => handleDisconnectCalendar(id, 'microsoft')}
            onSync={handleSyncCalendar}
            onToggleSync={handleToggleSyncEnabled}
            onToggleAutoRecord={handleToggleAutoRecord}
            syncing={syncing}
          />

          {/* Apple iCloud */}
          <AppleCalendarCard
            isPrimary={platform?.primarySuggestion === 'apple'}
            connection={getConnectionForProvider('apple')}
            onDisconnect={(id: string) => handleDisconnectCalendar(id, 'apple')}
            onSync={handleSyncCalendar}
            onToggleSync={handleToggleSyncEnabled}
            onToggleAutoRecord={handleToggleAutoRecord}
            syncing={syncing}
          />
        </div>

        {/* Connected Calendars List */}
        {connections.filter(c => c.is_active).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Connected Calendars</CardTitle>
              <CardDescription>
                Manage your connected calendar accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {connections.filter(c => c.is_active).map(connection => (
                  <div
                    key={connection.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 relative">
                        <Image
                          src={
                            connection.provider === 'google' ? googleIcon :
                            connection.provider === 'microsoft' ? outlookIcon :
                            appleIcon
                          }
                          alt={`${getCalendarDisplayName(connection.provider)} icon`}
                          width={32}
                          height={32}
                          className="object-contain"
                        />
                      </div>
                      <div>
                        <p className="font-medium">
                          {getCalendarDisplayName(connection.provider)}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {connection.calendar_name || 'Primary Calendar'}
                        </p>
                        {connection.last_synced_at && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Last synced: {new Date(connection.last_synced_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleSyncCalendar(connection.id)}
                        disabled={syncing === connection.id}
                      >
                        <RefreshCw className={`w-4 h-4 ${syncing === connection.id ? 'animate-spin' : ''}`} />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDisconnectCalendar(connection.id, connection.provider)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Help Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              💡 How Calendar Integration Works
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
                1
              </div>
              <div>
                <p className="font-medium">Connect your calendar with one click</p>
                <p className="text-sm text-muted-foreground">
                  No passwords needed! OAuth2 authentication keeps your data secure.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
                2
              </div>
              <div>
                <p className="font-medium">Your meetings sync automatically</p>
                <p className="text-sm text-muted-foreground">
                  We'll detect Zoom, Google Meet, and Teams links in your calendar.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
                3
              </div>
              <div>
                <p className="font-medium">Start recording with one tap</p>
                <p className="text-sm text-muted-foreground">
                  Before your meeting, just click "Record" and we'll handle the rest.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
                4
              </div>
              <div>
                <p className="font-medium">AI generates notes and action items</p>
                <p className="text-sm text-muted-foreground">
                  Get automatic transcripts, summaries, and action items after each meeting.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

// Apple Calendar Card Component (uses CalDAV)
function AppleCalendarCard({
  isPrimary,
  connection,
  onDisconnect,
  onSync,
  onToggleSync,
  onToggleAutoRecord,
  syncing
}: {
  isPrimary: boolean;
  connection?: CalendarConnection;
  onDisconnect: (id: string) => void;
  onSync: (id: string) => void;
  onToggleSync: (id: string, enabled: boolean) => void;
  onToggleAutoRecord: (id: string, enabled: boolean) => void;
  syncing: string | null;
}) {
  const { token } = useAuth();
  const [showSetup, setShowSetup] = useState(false);
  const [email, setEmail] = useState('');
  const [appPassword, setAppPassword] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState('');

  const isConnected = !!connection;
  const isSyncing = syncing === connection?.id;

  const handleConnect = async () => {
    if (!email || !appPassword) {
      setError('Please enter your iCloud email and app-specific password');
      return;
    }

    setIsConnecting(true);
    setError('');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/calendar/apple/setup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email,
          app_password: appPassword,
          calendar_id: 'all'
        }),
      });

      if (response.ok) {
        // Success - reload the page to show the connected calendar
        window.location.reload();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to connect. Please check your credentials.');
      }
    } catch (err) {
      setError('Failed to connect. Please try again.');
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <Card className={`${isPrimary ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
      <CardHeader>
        <div className="w-12 h-12 mb-3 relative">
          <Image
            src={appleIcon}
            alt="iCloud Calendar icon"
            width={48}
            height={48}
            className="object-contain"
          />
        </div>
        {isPrimary && (
          <Badge className="bg-blue-500 text-white mb-2 w-fit">
            Recommended for you
          </Badge>
        )}
        <CardTitle>iCloud Calendar</CardTitle>
        <CardDescription>Apple Calendar, macOS</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected ? (
          <>
            {!showSetup ? (
              <Button
                onClick={() => setShowSetup(true)}
                className="w-full"
                variant={isPrimary ? 'default' : 'outline'}
              >
                Connect iCloud Calendar
              </Button>
            ) : (
              <div className="space-y-4 p-4 border rounded-lg bg-gray-50">
                <div className="space-y-2">
                  <h4 className="font-medium text-sm">Setup Instructions</h4>
                  <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
                    <li>Go to <a href="https://appleid.apple.com" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">appleid.apple.com</a></li>
                    <li>Sign in → Security → App-Specific Passwords</li>
                    <li>Click "Generate password" for "TranscribeAI"</li>
                    <li>Copy the generated password and paste it below</li>
                  </ol>
                </div>

                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label htmlFor="icloud-email">iCloud Email</Label>
                    <Input
                      id="icloud-email"
                      type="email"
                      placeholder="your@icloud.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="app-password">App-Specific Password</Label>
                    <Input
                      id="app-password"
                      type="password"
                      placeholder="xxxx-xxxx-xxxx-xxxx"
                      value={appPassword}
                      onChange={(e) => setAppPassword(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Generate this from your Apple ID settings
                    </p>
                  </div>

                  {error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <div className="flex gap-2">
                    <Button
                      onClick={handleConnect}
                      disabled={isConnecting}
                      className="flex-1"
                    >
                      {isConnecting ? 'Connecting...' : 'Connect'}
                    </Button>
                    <Button
                      onClick={() => {
                        setShowSetup(false);
                        setError('');
                        setEmail('');
                        setAppPassword('');
                      }}
                      variant="outline"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Connected</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSync(connection.id)}
                disabled={isSyncing}
              >
                {isSyncing ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>
            </div>

            {connection.last_synced_at && (
              <p className="text-xs text-muted-foreground">
                Last synced: {new Date(connection.last_synced_at).toLocaleString()}
              </p>
            )}

            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Auto-sync</p>
                  <p className="text-xs text-muted-foreground">
                    Automatically sync calendar events
                  </p>
                </div>
                <Switch
                  checked={connection.sync_enabled}
                  onCheckedChange={(checked) => onToggleSync(connection.id, checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Auto-record</p>
                  <p className="text-xs text-muted-foreground">
                    Automatically start recording meetings
                  </p>
                </div>
                <Switch
                  checked={connection.auto_record_meetings}
                  onCheckedChange={(checked) => onToggleAutoRecord(connection.id, checked)}
                />
              </div>
            </div>

            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={() => onDisconnect(connection.id)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Disconnect
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}

// Calendar Provider Card Component
function CalendarProviderCard({
  provider,
  isPrimary,
  connection,
  onConnect,
  onDisconnect,
  onSync,
  onToggleSync,
  onToggleAutoRecord,
  syncing
}: {
  provider: string;
  isPrimary: boolean;
  connection?: CalendarConnection;
  onConnect: () => void;
  onDisconnect: (id: string) => void;
  onSync: (id: string) => void;
  onToggleSync: (id: string, enabled: boolean) => void;
  onToggleAutoRecord: (id: string, enabled: boolean) => void;
  syncing: string | null;
}) {
  const isConnected = !!connection;
  const isSyncing = syncing === connection?.id;

  const getProviderIcon = () => {
    switch (provider) {
      case 'google':
        return googleIcon;
      case 'microsoft':
        return outlookIcon;
      case 'apple':
        return appleIcon;
      default:
        return googleIcon;
    }
  };

  return (
    <Card className={`${isPrimary ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}>
      <CardHeader>
        <div className="w-12 h-12 mb-3 relative">
          <Image
            src={getProviderIcon()}
            alt={`${getCalendarDisplayName(provider)} icon`}
            width={48}
            height={48}
            className="object-contain"
          />
        </div>
        {isPrimary && (
          <Badge className="bg-blue-500 text-white mb-2 w-fit">
            Recommended for you
          </Badge>
        )}
        <CardTitle>{getCalendarDisplayName(provider)}</CardTitle>
        <CardDescription>{getCalendarDescription(provider)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!isConnected ? (
          <Button
            onClick={onConnect}
            className="w-full"
            variant={isPrimary ? 'default' : 'outline'}
          >
            Connect {getCalendarDisplayName(provider)}
          </Button>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="font-medium">Connected</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onSync(connection.id)}
                disabled={isSyncing}
              >
                {isSyncing ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Sync Now
                  </>
                )}
              </Button>
            </div>

            {connection.last_synced_at && (
              <p className="text-xs text-muted-foreground">
                Last synced: {new Date(connection.last_synced_at).toLocaleString()}
              </p>
            )}

            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Auto-sync</p>
                  <p className="text-xs text-muted-foreground">
                    Sync calendar every 15 minutes
                  </p>
                </div>
                <Switch
                  checked={connection.sync_enabled}
                  onCheckedChange={(checked) => onToggleSync(connection.id, checked)}
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Auto-record</p>
                  <p className="text-xs text-muted-foreground">
                    Automatically prepare meetings
                  </p>
                </div>
                <Switch
                  checked={connection.auto_record_meetings}
                  onCheckedChange={(checked) => onToggleAutoRecord(connection.id, checked)}
                />
              </div>
            </div>

            <Button
              variant="destructive"
              size="sm"
              className="w-full"
              onClick={() => onDisconnect(connection.id)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Disconnect
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
