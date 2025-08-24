import React from 'react';

/**
 * LocalTime Component - Displays timestamps in user's local timezone
 * 
 * @param {string|number|Date} timestamp - The timestamp to display
 * @param {string} format - The format type: 'time', 'date', 'datetime', 'relative', 'short'
 * @param {string} prefix - Optional prefix text
 * @param {string} suffix - Optional suffix text
 * @param {string} className - Optional CSS classes
 * @param {object} options - Optional Intl.DateTimeFormat options to override defaults
 */
const LocalTime = ({ 
  timestamp, 
  format = 'datetime', 
  prefix = '', 
  suffix = '', 
  className = '',
  options = {}
}) => {
  if (!timestamp) {
    return null;
  }

  // Convert various timestamp formats to Date object
  const getDate = (ts) => {
    if (ts instanceof Date) return ts;
    if (typeof ts === 'string') {
      // Check if timestamp has timezone info
      let dateStr = ts;
      
      // If the timestamp doesn't end with 'Z' or timezone offset, assume it's UTC
      if (!ts.endsWith('Z') && !ts.match(/[+-]\d{2}:\d{2}$/) && !ts.includes('+00:00')) {
        // This is likely a UTC timestamp without the Z suffix
        if (ts.match(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)) {
          dateStr = ts + 'Z'; // Add Z to indicate UTC
        }
      }
      
      const parsed = new Date(dateStr);
      if (!isNaN(parsed.getTime())) return parsed;
    }
    if (typeof ts === 'number') {
      // Handle Unix timestamps (both seconds and milliseconds)
      const date = ts > 1e12 ? new Date(ts) : new Date(ts * 1000);
      if (!isNaN(date.getTime())) return date;
    }
    return null;
  };

  const date = getDate(timestamp);
  if (!date) {
    return <span className={className}>Invalid date</span>;
  }

  // Default format options for different display types
  const formatOptions = {
    time: {
      hour: 'numeric',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      ...options
    },
    timeOnly: {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      ...options
    },
    date: {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      ...options
    },
    dateShort: {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      ...options
    },
    dateCompact: {
      month: 'numeric',
      day: 'numeric',
      year: '2-digit',
      ...options
    },
    datetime: {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      ...options
    },
    datetimeFull: {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      ...options
    },
    short: {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      ...options
    },
    compact: {
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
      ...options
    },
    relative: options // Custom handling for relative time
  };

  const formatTime = () => {
    try {
      if (format === 'relative') {
        return getRelativeTime(date);
      }
      
      const opts = formatOptions[format] || formatOptions.datetime;
      return date.toLocaleString(undefined, opts);
    } catch (error) {
      console.error('Error formatting time:', error);
      return date.toString();
    }
  };

  // Get relative time (e.g., "2 minutes ago", "in 5 hours")
  const getRelativeTime = (date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);
    const diffMinutes = Math.floor(diffSeconds / 60);
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    // Future dates
    if (diffMs < 0) {
      const absDiffMinutes = Math.abs(diffMinutes);
      const absDiffHours = Math.abs(diffHours);
      const absDiffDays = Math.abs(diffDays);
      
      if (absDiffMinutes < 60) {
        return `in ${absDiffMinutes} minute${absDiffMinutes !== 1 ? 's' : ''}`;
      } else if (absDiffHours < 24) {
        return `in ${absDiffHours} hour${absDiffHours !== 1 ? 's' : ''}`;
      } else {
        return `in ${absDiffDays} day${absDiffDays !== 1 ? 's' : ''}`;
      }
    }

    // Past dates
    if (diffSeconds < 60) {
      return 'just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      // For dates older than a week, show the actual date
      return date.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
    }
  };

  const formattedTime = formatTime();

  return (
    <span 
      className={className}
      title={date.toLocaleString(undefined, {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        second: '2-digit',
        timeZoneName: 'short'
      })}
    >
      {prefix}{formattedTime}{suffix}
    </span>
  );
};

export default LocalTime;

// Export some common format presets as convenience components

// Time formats
export const LocalTimeOnly = (props) => <LocalTime {...props} format="timeOnly" />;
export const LocalTimeWithSeconds = (props) => <LocalTime {...props} format="time" />;

// Date formats  
export const LocalDateOnly = (props) => <LocalTime {...props} format="date" />;
export const LocalDateShort = (props) => <LocalTime {...props} format="dateShort" />;
export const LocalDateCompact = (props) => <LocalTime {...props} format="dateCompact" />;

// Combined date/time formats
export const LocalDateTime = (props) => <LocalTime {...props} format="datetime" />;
export const LocalDateTimeFull = (props) => <LocalTime {...props} format="datetimeFull" />;
export const LocalTimeShort = (props) => <LocalTime {...props} format="short" />;
export const LocalTimeCompact = (props) => <LocalTime {...props} format="compact" />;

// Special formats
export const LocalTimeRelative = (props) => <LocalTime {...props} format="relative" />;