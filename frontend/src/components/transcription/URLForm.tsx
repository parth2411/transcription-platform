// frontend/src/components/transcription/URLForm.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { AlertCircle, Globe, Youtube, Podcast, VideoIcon } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface URLFormProps {
  onSubmit: (data: URLFormData) => void;
  isLoading?: boolean;
}

interface URLFormData {
  url: string;
  title: string;
  language: string;
  generate_summary: boolean;
  speaker_diarization: boolean;
  add_to_knowledge_base: boolean;
}

const URLForm: React.FC<URLFormProps> = ({ onSubmit, isLoading = false }) => {
  const [formData, setFormData] = useState<URLFormData>({
    url: '',
    title: '',
    language: 'auto',
    generate_summary: true,
    speaker_diarization: false,
    add_to_knowledge_base: true, // Default to true for knowledge base
  });

  const [urlType, setUrlType] = useState<string>('');
  const [isValidUrl, setIsValidUrl] = useState<boolean>(true);

  const detectUrlType = (url: string) => {
    if (!url) {
      setUrlType('');
      return;
    }

    if (url.includes('youtube.com') || url.includes('youtu.be')) {
      setUrlType('YouTube');
    } else if (url.includes('podcast') || url.includes('anchor.fm') || url.includes('spotify.com/episode')) {
      setUrlType('Podcast');
    } else if (url.includes('vimeo.com') || url.includes('twitch.tv')) {
      setUrlType('Video Platform');
    } else if (url.includes('.mp3') || url.includes('.wav') || url.includes('.m4a')) {
      setUrlType('Audio File');
    } else if (url.includes('.mp4') || url.includes('.mov') || url.includes('.avi')) {
      setUrlType('Video File');
    } else {
      setUrlType('Web Content');
    }
  };

  const validateUrl = (url: string) => {
    try {
      new URL(url);
      setIsValidUrl(true);
      return true;
    } catch {
      setIsValidUrl(false);
      return false;
    }
  };

  const handleUrlChange = (url: string) => {
    setFormData(prev => ({ ...prev, url }));
    detectUrlType(url);
    
    if (url) {
      validateUrl(url);
      
      // Auto-generate title if empty
      if (!formData.title) {
        const urlObj = new URL(url);
        const pathParts = urlObj.pathname.split('/').filter(Boolean);
        const lastPart = pathParts[pathParts.length - 1] || urlObj.hostname;
        setFormData(prev => ({ 
          ...prev, 
          title: lastPart.replace(/[-_]/g, ' ').replace(/\.[^/.]+$/, '') 
        }));
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.url || !isValidUrl) {
      return;
    }

    // Title is now optional - will be auto-generated on backend
    onSubmit(formData);
  };

  const getUrlIcon = () => {
    switch (urlType) {
      case 'YouTube':
        return <Youtube className="h-4 w-4 text-red-500" />;
      case 'Podcast':
        return <Podcast className="h-4 w-4 text-purple-500" />;
      case 'Video Platform':
      case 'Video File':
        return <VideoIcon className="h-4 w-4 text-blue-500" />;
      default:
        return <Globe className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle>Transcribe from URL</CardTitle>
        <p className="text-sm text-gray-600">
          Support for YouTube, podcasts, audio/video files, and more
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* URL Input */}
          <div className="space-y-2">
            <Label htmlFor="url">URL</Label>
            <div className="relative">
              <Input
                id="url"
                type="url"
                placeholder="https://youtube.com/watch?v=... or any audio/video URL"
                value={formData.url}
                onChange={(e) => handleUrlChange(e.target.value)}
                className={!isValidUrl && formData.url ? 'border-red-500' : ''}
                required
              />
              {urlType && isValidUrl && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center space-x-1">
                  {getUrlIcon()}
                  <span className="text-xs text-gray-500">{urlType}</span>
                </div>
              )}
            </div>
            {!isValidUrl && formData.url && (
              <p className="text-sm text-red-500">Please enter a valid URL</p>
            )}
          </div>

          {/* Supported Platforms Info */}
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <strong>Supported platforms:</strong> YouTube, Vimeo, Twitch, Podcast platforms, 
              direct audio/video files (.mp3, .wav, .mp4, .mov, etc.), and many more.
            </AlertDescription>
          </Alert>

          {/* Title Input */}
          <div className="space-y-2">
            <Label htmlFor="title">Title (Optional)</Label>
            <Input
              id="title"
              placeholder="Auto-generated from video title or timestamp"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
            />
            <p className="text-xs text-gray-500">
              {formData.title 
                ? "Custom title will be used" 
                : "Title will be automatically extracted from video or generated with timestamp"
              }
            </p>
          </div>

          {/* Language Selection */}
          <div className="space-y-2">
            <Label htmlFor="language">Language</Label>
            <select
              id="language"
              value={formData.language}
              onChange={(e) => setFormData(prev => ({ ...prev, language: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="auto">Auto-detect</option>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="ru">Russian</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="zh">Chinese</option>
            </select>
          </div>

          {/* Processing Options */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Processing Options</h3>
            
            {/* Generate Summary */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="summary">Generate Summary</Label>
                <p className="text-sm text-gray-500">
                  Create an AI-powered summary of the transcription
                </p>
              </div>
              <Switch
                id="summary"
                checked={formData.generate_summary}
                onCheckedChange={(checked) => 
                  setFormData(prev => ({ ...prev, generate_summary: checked }))
                }
              />
            </div>

            {/* Add to Knowledge Base */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="knowledge">Add to Knowledge Base</Label>
                <p className="text-sm text-gray-500">
                  Store transcription and summary for future AI queries
                </p>
              </div>
              <Switch
                id="knowledge"
                checked={formData.add_to_knowledge_base}
                onCheckedChange={(checked) => 
                  setFormData(prev => ({ ...prev, add_to_knowledge_base: checked }))
                }
              />
            </div>

            {/* Speaker Diarization */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="diarization">Speaker Diarization</Label>
                <p className="text-sm text-gray-500">
                  Identify different speakers in the audio (experimental)
                </p>
              </div>
              <Switch
                id="diarization"
                checked={formData.speaker_diarization}
                onCheckedChange={(checked) => 
                  setFormData(prev => ({ ...prev, speaker_diarization: checked }))
                }
              />
            </div>
          </div>

          {/* Knowledge Base Info */}
          {formData.add_to_knowledge_base && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                When enabled, your transcription and summary will be stored in your personal 
                knowledge base, allowing you to search and query this content later using AI.
              </AlertDescription>
            </Alert>
          )}

          {/* Submit Button */}
          <Button 
            type="submit" 
            className="w-full" 
            disabled={isLoading || !formData.url || !isValidUrl}
          >
            {isLoading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing URL...
              </>
            ) : (
              `Transcribe ${urlType || 'Content'}`
            )}
          </Button>

          {/* Processing Note */}
          <p className="text-xs text-gray-500 text-center">
            Processing time depends on content length. Large files may take several minutes.
          </p>
        </form>
      </CardContent>
    </Card>
  );
};

export default URLForm;