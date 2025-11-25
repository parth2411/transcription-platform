// frontend/src/lib/platform-detection.ts
/**
 * Platform Detection Utility
 * Detects user's operating system and suggests appropriate calendar provider
 */

export interface PlatformDetectionResult {
  os: 'apple' | 'windows' | 'android' | 'linux' | 'other';
  suggestedCalendars: string[];
  primarySuggestion: string;
}

export function detectUserPlatform(): PlatformDetectionResult {
  if (typeof window === 'undefined') {
    // Server-side rendering
    return {
      os: 'other',
      suggestedCalendars: ['google', 'microsoft', 'icloud'],
      primarySuggestion: 'google'
    };
  }

  const userAgent = window.navigator.userAgent;
  const platform = window.navigator.platform;

  // Detect macOS/iOS (Apple users)
  if (/Mac|iPhone|iPad|iPod/.test(platform) || /Mac OS X/.test(userAgent)) {
    return {
      os: 'apple',
      suggestedCalendars: ['icloud', 'google', 'microsoft'],
      primarySuggestion: 'icloud'
    };
  }

  // Detect Windows
  if (/Win/.test(platform)) {
    return {
      os: 'windows',
      suggestedCalendars: ['microsoft', 'google'],
      primarySuggestion: 'microsoft'
    };
  }

  // Detect Android
  if (/Android/.test(userAgent)) {
    return {
      os: 'android',
      suggestedCalendars: ['google'],
      primarySuggestion: 'google'
    };
  }

  // Detect Linux
  if (/Linux/.test(platform)) {
    return {
      os: 'linux',
      suggestedCalendars: ['google', 'microsoft'],
      primarySuggestion: 'google'
    };
  }

  // Default fallback
  return {
    os: 'other',
    suggestedCalendars: ['google', 'microsoft', 'icloud'],
    primarySuggestion: 'google'
  };
}

export function getPlatformDisplayName(os: string): string {
  switch (os) {
    case 'apple':
      return 'macOS/iOS';
    case 'windows':
      return 'Windows';
    case 'android':
      return 'Android';
    case 'linux':
      return 'Linux';
    default:
      return 'your device';
  }
}

export function getCalendarIconPath(provider: string): string {
  switch (provider) {
    case 'google':
      return '/src/assets/search.png';
    case 'microsoft':
    case 'outlook':
      return '/src/assets/outlook.png';
    case 'icloud':
    case 'apple':
      return '/src/assets/apple-logo.png';
    default:
      return '/src/assets/search.png';
  }
}

// Legacy emoji function (kept for backward compatibility)
export function getCalendarIcon(provider: string): string {
  switch (provider) {
    case 'google':
      return '🇬';
    case 'microsoft':
    case 'outlook':
      return '📧';
    case 'icloud':
    case 'apple':
      return '🍎';
    default:
      return '📅';
  }
}

export function getCalendarDisplayName(provider: string): string {
  switch (provider) {
    case 'google':
      return 'Google Calendar';
    case 'microsoft':
    case 'outlook':
      return 'Outlook Calendar';
    case 'icloud':
    case 'apple':
      return 'iCloud Calendar';
    default:
      return provider;
  }
}

export function getCalendarDescription(provider: string): string {
  switch (provider) {
    case 'google':
      return 'Gmail, Google Workspace';
    case 'microsoft':
    case 'outlook':
      return 'Outlook, Microsoft 365';
    case 'icloud':
    case 'apple':
      return 'Apple Calendar, iCloud';
    default:
      return 'Calendar service';
  }
}
