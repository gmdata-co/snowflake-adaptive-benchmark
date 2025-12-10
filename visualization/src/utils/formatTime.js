/**
 * Time formatting utilities for dynamic unit display.
 * Units are selected based on scenario max values so all values
 * within a scenario use the same unit for easy comparison.
 */

/**
 * Determine best time unit based on max time value in seconds.
 * @param {number} maxSeconds - Maximum time value in the dataset
 * @returns {'seconds'|'minutes'|'hours'} - Best unit for display
 */
export function getTimeUnit(maxSeconds) {
  if (maxSeconds < 120) return 'seconds';
  if (maxSeconds <= 3600) return 'minutes';
  return 'hours';
}

/**
 * Format time value with appropriate unit suffix.
 * @param {number} seconds - Time in seconds
 * @param {'seconds'|'minutes'|'hours'} unit - Unit to display
 * @returns {string} - Formatted time string (e.g., "75s", "14.4 min", "3.7 hr")
 */
export function formatTime(seconds, unit) {
  if (seconds == null) return 'N/A';

  switch (unit) {
    case 'minutes':
      return `${(seconds / 60).toFixed(1)} min`;
    case 'hours':
      return `${(seconds / 3600).toFixed(1)} hr`;
    default:
      return `${Math.round(seconds)}s`;
  }
}

/**
 * Convert seconds to numeric value in specified unit (for chart axes).
 * @param {number} seconds - Time in seconds
 * @param {'seconds'|'minutes'|'hours'} unit - Target unit
 * @returns {number} - Converted numeric value
 */
export function convertTime(seconds, unit) {
  switch (unit) {
    case 'minutes':
      return seconds / 60;
    case 'hours':
      return seconds / 3600;
    default:
      return seconds;
  }
}

/**
 * Get unit suffix for axis labels.
 * @param {'seconds'|'minutes'|'hours'} unit - Time unit
 * @returns {string} - Unit suffix (e.g., "s", "min", "hr")
 */
export function getUnitSuffix(unit) {
  switch (unit) {
    case 'minutes':
      return 'min';
    case 'hours':
      return 'hr';
    default:
      return 's';
  }
}
