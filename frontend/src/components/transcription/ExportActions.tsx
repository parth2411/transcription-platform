// frontend/src/components/transcription/ExportActions.tsx
'use client'

import React from 'react'
import { Button } from '@/components/ui/button'
import { 
  Download, 
  Share, 
  FileText, 
  Copy,
  Mail,
  Link as LinkIcon
} from 'lucide-react'
import { useToast } from '@/components/ui/toaster'

interface ExportActionsProps {
  transcription: {
    id: string
    title: string
    transcription_text?: string
    summary_text?: string
    created_at: string
  }
  token: string
}

export function ExportActions({ transcription, token }: ExportActionsProps) {
  const { toast } = useToast()

  const downloadTranscript = async (format: 'txt' | 'pdf' | 'docx' | 'srt') => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${transcription.id}/export?format=${format}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${transcription.title}.${format}`
        a.click()
        URL.revokeObjectURL(url)
        
        toast({
          title: "Download started",
          description: `Transcript downloaded as ${format.toUpperCase()}`,
          variant: "success"
        })
      } else {
        throw new Error('Export failed')
      }
    } catch (error) {
      toast({
        title: "Export failed",
        description: "Could not export transcript",
        variant: "destructive"
      })
    }
  }

  const copyToClipboard = async () => {
    try {
      const text = transcription.transcription_text || ''
      await navigator.clipboard.writeText(text)
      toast({
        title: "Copied!",
        description: "Transcript copied to clipboard",
        variant: "success"
      })
    } catch (error) {
      toast({
        title: "Copy failed",
        description: "Could not copy to clipboard",
        variant: "destructive"
      })
    }
  }

  const shareTranscript = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: transcription.title,
          text: transcription.transcription_text,
          url: window.location.href
        })
      } else {
        // Fallback: copy link to clipboard
        await navigator.clipboard.writeText(window.location.href)
        toast({
          title: "Link copied",
          description: "Transcript link copied to clipboard",
          variant: "success"
        })
      }
    } catch (error) {
      console.log('Share cancelled or failed')
    }
  }

  const generateShareableLink = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/transcriptions/${transcription.id}/share`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (response.ok) {
        const { share_url } = await response.json()
        await navigator.clipboard.writeText(share_url)
        toast({
          title: "Shareable link created",
          description: "Link copied to clipboard",
          variant: "success"
        })
      }
    } catch (error) {
      toast({
        title: "Share failed",
        description: "Could not create shareable link",
        variant: "destructive"
      })
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {/* Download Options */}
      <div className="flex gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => downloadTranscript('txt')}
        >
          <Download className="w-4 h-4 mr-1" />
          TXT
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => downloadTranscript('pdf')}
        >
          <FileText className="w-4 h-4 mr-1" />
          PDF
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => downloadTranscript('srt')}
        >
          <Download className="w-4 h-4 mr-1" />
          SRT
        </Button>
      </div>

      {/* Copy & Share */}
      <Button
        variant="outline"
        size="sm"
        onClick={copyToClipboard}
      >
        <Copy className="w-4 h-4 mr-1" />
        Copy
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={shareTranscript}
      >
        <Share className="w-4 h-4 mr-1" />
        Share
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={generateShareableLink}
      >
        <LinkIcon className="w-4 h-4 mr-1" />
        Get Link
      </Button>
    </div>
  )
}