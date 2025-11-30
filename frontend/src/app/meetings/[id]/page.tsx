// frontend/src/app/meetings/[id]/page.tsx
'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  Calendar,
  Video,
  Clock,
  Users,
  ExternalLink,
  ArrowLeft,
  FileText,
  CheckSquare,
  Mic,
  StopCircle,
  Save,
  Trash2,
  Sparkles
} from 'lucide-react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { RecordingControls } from '@/components/recording/RecordingControls';

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
  summary: string | null;
}

export default function MeetingDetailPage({ params }: { params: { id: string } }) {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState('');
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [savedNotes, setSavedNotes] = useState<any[]>([]);
  const [loadingNotes, setLoadingNotes] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Get tab from URL query parameter
  useEffect(() => {
    const tab = searchParams.get('tab');
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  useEffect(() => {
    loadMeeting();
    if (activeTab === 'notes') {
      loadNotes();
    }
  }, [params.id, token, activeTab]);

  const loadMeeting = async () => {
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/meetings/${params.id}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data: Meeting = await response.json();
        setMeeting(data);
      } else if (response.status === 404) {
        router.push('/meetings');
      }
    } catch (error) {
      console.error('Failed to load meeting:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
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
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours} hour${hours > 1 ? 's' : ''} ${remainingMinutes} minutes`;
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

  const loadNotes = async () => {
    if (!token || !meeting) return;

    setLoadingNotes(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/meetings/${params.id}/notes`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSavedNotes(data);
        // If there are existing notes, load the first one into the editor
        if (data.length > 0) {
          setNotes(data[0].content);
        }
      }
    } catch (error) {
      console.error('Failed to load notes:', error);
    } finally {
      setLoadingNotes(false);
    }
  };

  const handleSaveNotes = async () => {
    if (!notes.trim()) return;

    setIsSavingNotes(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/notes`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            meeting_id: params.id,
            content: notes,
            note_type: 'manual',
            section: 'notes'
          }),
        }
      );

      if (response.ok) {
        // Reload notes
        await loadNotes();
        setNotes(''); // Clear editor after saving
      } else {
        console.error('Failed to save note');
      }
    } catch (error) {
      console.error('Error saving note:', error);
    } finally {
      setIsSavingNotes(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/notes/${noteId}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        await loadNotes();
      }
    } catch (error) {
      console.error('Error deleting note:', error);
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      </DashboardLayout>
    );
  }

  if (!meeting) {
    return (
      <DashboardLayout>
        <div className="max-w-4xl mx-auto p-6">
          <Card>
            <CardContent className="text-center py-12">
              <Calendar className="w-12 h-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold mb-2">Meeting not found</h3>
              <p className="text-muted-foreground mb-4">
                The meeting you're looking for doesn't exist or you don't have access to it.
              </p>
              <Link href="/meetings">
                <Button>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Meetings
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Back Button */}
        <Link href="/meetings">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Meetings
          </Button>
        </Link>

        {/* Meeting Header */}
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-2xl mb-2">{meeting.title}</CardTitle>
                <CardDescription className="space-y-2">
                  <div className="flex items-center gap-2 text-base">
                    <Clock className="w-4 h-4" />
                    <span>{formatDate(meeting.start_time)}</span>
                  </div>
                  <div className="flex items-center gap-2 text-base">
                    <span>{formatTime(meeting.start_time)} - {formatTime(meeting.end_time)}</span>
                    <span className="text-xs text-muted-foreground">
                      ({getDuration(meeting.start_time, meeting.end_time)})
                    </span>
                  </div>
                </CardDescription>
              </div>

              <div className="flex items-center gap-2">
                {meeting.platform && (
                  <Badge className={getPlatformColor(meeting.platform)}>
                    <span className="mr-1">{getPlatformIcon(meeting.platform)}</span>
                    {meeting.platform}
                  </Badge>
                )}
                {isUpcoming(meeting.start_time) ? (
                  <Badge className="bg-green-100 text-green-800">Upcoming</Badge>
                ) : (
                  <Badge variant="secondary">Past</Badge>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent>
            {meeting.description && (
              <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Description</h4>
                <p className="text-sm text-muted-foreground">{meeting.description}</p>
              </div>
            )}

            <div className="flex items-center gap-4 mb-4">
              {meeting.participants && (
                <div className="flex items-center gap-2 text-sm">
                  <Users className="w-4 h-4 text-muted-foreground" />
                  <span>{meeting.participants.split(',').length} participants</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              {meeting.meeting_url && (
                <a
                  href={meeting.meeting_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button variant="outline">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Join Meeting
                  </Button>
                </a>
              )}
              {isUpcoming(meeting.start_time) && (
                <Button
                  className="bg-red-600 hover:bg-red-700 text-white"
                  onClick={() => {
                    // Switch to Recording tab
                    setActiveTab('recording');
                  }}
                >
                  <Video className="w-4 h-4 mr-2" />
                  Start Recording
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Tabbed Content */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">
              <FileText className="w-4 h-4 mr-2" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="notes">
              <FileText className="w-4 h-4 mr-2" />
              Notes
            </TabsTrigger>
            <TabsTrigger value="recording">
              <Mic className="w-4 h-4 mr-2" />
              Recording
            </TabsTrigger>
            <TabsTrigger value="actions">
              <CheckSquare className="w-4 h-4 mr-2" />
              Action Items
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview">
            <Card>
              <CardHeader>
                <CardTitle>Meeting Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium mb-1">Date & Time</h4>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(meeting.start_time)} at {formatTime(meeting.start_time)}
                  </p>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-1">Duration</h4>
                  <p className="text-sm text-muted-foreground">
                    {getDuration(meeting.start_time, meeting.end_time)}
                  </p>
                </div>

                {meeting.platform && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Platform</h4>
                    <p className="text-sm text-muted-foreground">{meeting.platform}</p>
                  </div>
                )}

                {meeting.participants && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Participants</h4>
                    <div className="text-sm text-muted-foreground space-y-1">
                      {meeting.participants.split(',').map((participant, idx) => (
                        <div key={idx}>{participant.trim()}</div>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="text-sm font-medium mb-1">Status</h4>
                  <p className="text-sm text-muted-foreground capitalize">{meeting.status}</p>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-1">Recording Status</h4>
                  <p className="text-sm text-muted-foreground capitalize">
                    {meeting.recording_status.replace('_', ' ')}
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* AI Summary Card */}
            {meeting.summary && meeting.recording_status === 'completed' && (
              <Card className="mt-4 border-blue-200 bg-blue-50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-blue-900">
                    <Sparkles className="w-5 h-5" />
                    AI-Generated Summary
                  </CardTitle>
                  <CardDescription className="text-blue-700">
                    Automatically generated after recording
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <div className="whitespace-pre-wrap text-sm text-gray-800 bg-white p-4 rounded-lg border">
                      {meeting.summary}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Notes Tab */}
          <TabsContent value="notes">
            <div className="space-y-4">
              {/* Saved Notes */}
              {savedNotes.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Saved Notes ({savedNotes.length})</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {savedNotes.map((note) => (
                        <div
                          key={note.id}
                          className="border rounded-lg p-4 bg-gray-50 hover:bg-gray-100 transition-colors"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary" className="text-xs">
                                {note.section || 'General'}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {new Date(note.created_at).toLocaleString()}
                              </span>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteNote(note.id)}
                            >
                              <Trash2 className="w-4 h-4 text-red-600" />
                            </Button>
                          </div>
                          <p className="text-sm whitespace-pre-wrap">{note.content}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* New Note Editor */}
              <Card>
                <CardHeader>
                  <CardTitle>Add New Note</CardTitle>
                  <CardDescription>
                    Take notes during or after your meeting. Each note is saved separately.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <Textarea
                    placeholder="Start typing your notes here..."
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="min-h-[300px] font-mono text-sm"
                  />
                  <div className="flex justify-between items-center">
                    <p className="text-xs text-muted-foreground">
                      {notes.length} characters
                    </p>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        onClick={() => setNotes('')}
                        disabled={!notes}
                      >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Clear
                      </Button>
                      <Button
                        onClick={handleSaveNotes}
                        disabled={isSavingNotes || !notes.trim()}
                      >
                        <Save className="w-4 h-4 mr-2" />
                        {isSavingNotes ? 'Saving...' : 'Save Note'}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Recording Tab */}
          <TabsContent value="recording">
            {isUpcoming(meeting.start_time) || meeting.recording_status === 'recording' ? (
              <RecordingControls
                meetingId={meeting.id}
                onRecordingStart={() => {
                  // Refresh meeting data
                  loadMeeting();
                }}
                onRecordingStop={(transcriptionId) => {
                  // Refresh meeting data and show success
                  loadMeeting();
                }}
              />
            ) : (
              <Card>
                <CardHeader>
                  <CardTitle>Recording & Transcription</CardTitle>
                  <CardDescription>
                    View the recording and transcription for this meeting.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-12">
                    <Video className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                    <h3 className="text-lg font-semibold mb-2">Meeting Completed</h3>
                    <p className="text-muted-foreground mb-4">
                      {meeting.recording_status === 'completed'
                        ? 'Recording and transcription available'
                        : 'No recording available for this meeting'}
                    </p>
                    {meeting.recording_status === 'completed' && (
                      <Link href={`/transcriptions`}>
                        <Button>
                          <FileText className="w-4 h-4 mr-2" />
                          View Transcription
                        </Button>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Action Items Tab */}
          <TabsContent value="actions">
            <Card>
              <CardHeader>
                <CardTitle>Action Items</CardTitle>
                <CardDescription>
                  AI-extracted action items and tasks from this meeting.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12">
                  <CheckSquare className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Action Items Yet</h3>
                  <p className="text-muted-foreground">
                    Action items will appear here after the meeting is recorded and transcribed
                  </p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  );
}
