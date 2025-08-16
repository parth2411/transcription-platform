// frontend/src/components/common/StatusBadge.tsx
import { Badge } from '@/components/ui/badge'
import { getStatusColor } from '@/utils/format'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge className={`${getStatusColor(status)} ${className}`} variant="outline">
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  )
}