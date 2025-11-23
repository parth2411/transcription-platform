// frontend/src/app/meetings/page.tsx
'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Calendar,
  Video,
  Clock,
  Users,
  ExternalLink,
  RefreshCw,
  CheckCircle,
  Circle,
  FileText,
  Eye
} from 'lucide-react';
import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Meeting {
  id: string;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string;
  timezone: string;
  platform: string | null;
  meeting_url: string | null;
  participants: string | null;
  status: string;
  recording_status: string;
}

interface MeetingListResponse {
  meetings: Meeting[];
  total: number;
  upcoming_count: number;
  past_count: number;
}

export default function MeetingsPage() {
  const { token } = useAuth();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [upcomingCount, setUpcomingCount] = useState(0);
  const [pastCount, setPastCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'upcoming' | 'past' | 'all'>('upcoming');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadMeetings();
  }, [filter, token]);

  const loadMeetings = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/meetings?status_filter=${filter}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data: MeetingListResponse = await response.json();
        setMeetings(data.meetings);
        setUpcomingCount(data.upcoming_count);
        setPastCount(data.past_count);
      }
    } catch (error) {
      console.error('Failed to load meetings:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadMeetings();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const getDuration = (start: string, end: string) => {
    const startDate = new Date(start);
    const endDate = new Date(end);
    const diff = endDate.getTime() - startDate.getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  const getPlatformIcon = (platform: string | null) => {
    if (!platform) return '🎥';
    const lower = platform.toLowerCase();
    if (lower.includes('zoom')) return '🔷';
    if (lower.includes('meet')) return '📹';
    if (lower.includes('teams')) return '👥';
    return '🎥';
  };

  const getPlatformColor = (platform: string | null) => {
    if (!platform) return 'bg-gray-100 text-gray-800';
    const lower = platform.toLowerCase();
    if (lower.includes('zoom')) return 'bg-blue-100 text-blue-800';
    if (lower.includes('meet')) return 'bg-green-100 text-green-800';
    if (lower.includes('teams')) return 'bg-purple-100 text-purple-800';
    return 'bg-gray-100 text-gray-800';
  };

  const isUpcoming = (startTime: string) => {
    return new Date(startTime) > new Date();
  };

  const isSoon = (startTime: string) => {
    const start = new Date(startTime);
    const now = new Date();
    const diff = start.getTime() - now.getTime();
    const minutes = diff / 60000;
    return minutes > 0 && minutes <= 15;
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
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Calendar className="w-8 h-8" />
              Meetings
            </h1>
            <p className="text-muted-foreground mt-2">
              Your synced calendar meetings
            </p>
          </div>
          <Button
            onClick={handleRefresh}
            variant="outline"
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            className={`cursor-pointer transition-colors ${
              filter === 'upcoming' ? 'border-blue-500 bg-blue-50' : ''
            }`}
            onClick={() => setFilter('upcoming')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Upcoming</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{upcomingCount}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Scheduled meetings
              </p>
            </CardContent>
          </Card>

          <Card
            className={`cursor-pointer transition-colors ${
              filter === 'past' ? 'border-gray-500 bg-gray-50' : ''
            }`}
            onClick={() => setFilter('past')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Past</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{pastCount}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Completed meetings
              </p>
            </CardContent>
          </Card>

          <Card
            className={`cursor-pointer transition-colors ${
              filter === 'all' ? 'border-purple-500 bg-purple-50' : ''
            }`}
            onClick={() => setFilter('all')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">All</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{upcomingCount + pastCount}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Total meetings
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Meetings List */}
        {meetings.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold mb-2">No meetings found</h3>
              <p className="text-muted-foreground">
                {filter === 'upcoming'
                  ? "You don't have any upcoming meetings."
                  : filter === 'past'
                  ? "You don't have any past meetings."
                  : 'Connect your calendar to see meetings here.'}
              </p>
              <Link href="/settings/calendar">
                <Button className="mt-4" variant="outline">
                  <Calendar className="w-4 h-4 mr-2" />
                  Go to Calendar Settings
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {meetings.map((meeting) => (
              <Card
                key={meeting.id}
                className={`hover:shadow-md transition-shadow ${
                  isSoon(meeting.start_time) ? 'border-orange-500 bg-orange-50' : ''
                }`}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Meeting Title & Time */}
                      <div className="flex items-start gap-3 mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="text-lg font-semibold">{meeting.title}</h3>
                            {isSoon(meeting.start_time) && (
                              <Badge className="bg-orange-500 text-white">
                                Starting Soon
                              </Badge>
                            )}
                            {!isUpcoming(meeting.start_time) && (
                              <Badge variant="secondary">Past</Badge>
                            )}
                          </div>

                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              <span>{formatDate(meeting.start_time)}</span>
                              <span className="mx-1">•</span>
                              <span>{formatTime(meeting.start_time)}</span>
                              <span className="mx-1">-</span>
                              <span>{formatTime(meeting.end_time)}</span>
                              <span className="ml-2 text-xs">
                                ({getDuration(meeting.start_time, meeting.end_time)})
                              </span>
                            </div>
                          </div>

                          {meeting.description && (
                            <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                              {meeting.description}
                            </p>
                          )}

                          {/* Platform & Participants */}
                          <div className="flex items-center gap-3 mt-3">
                            {meeting.platform && (
                              <Badge className={getPlatformColor(meeting.platform)}>
                                <span className="mr-1">{getPlatformIcon(meeting.platform)}</span>
                                {meeting.platform}
                              </Badge>
                            )}
                            {meeting.participants && (
                              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                                <Users className="w-4 h-4" />
                                <span>{meeting.participants.split(',').length} participants</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-2 ml-4">
                      <div className="flex items-center gap-2">
                        {/* View Details Button - Always visible */}
                        <Link href={`/meetings/${meeting.id}`}>
                          <Button variant="outline" size="sm">
                            <Eye className="w-4 h-4 mr-2" />
                            Details
                          </Button>
                        </Link>

                        {/* Join Meeting Button - Only if meeting URL exists */}
                        {meeting.meeting_url && (
                          <a
                            href={meeting.meeting_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button variant="outline" size="sm">
                              <ExternalLink className="w-4 h-4 mr-2" />
                              Join
                            </Button>
                          </a>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {/* Add Note Button - Always visible */}
                        <Link href={`/meetings/${meeting.id}?tab=notes`}>
                          <Button variant="outline" size="sm">
                            <FileText className="w-4 h-4 mr-2" />
                            Add Note
                          </Button>
                        </Link>

                        {/* Record Button - Only for upcoming meetings */}
                        {isUpcoming(meeting.start_time) && (
                          <Link href={`/meetings/${meeting.id}?tab=recording`}>
                            <Button size="sm" className="bg-red-600 hover:bg-red-700 text-white">
                              <Video className="w-4 h-4 mr-2" />
                              Record
                            </Button>
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Recording Status */}
                  {meeting.recording_status !== 'not_started' && (
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex items-center gap-2 text-sm">
                        {meeting.recording_status === 'completed' ? (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-400" />
                        )}
                        <span className="text-muted-foreground">
                          Recording: {meeting.recording_status}
                        </span>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
