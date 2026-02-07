import DOMPurify from 'dompurify';
import type { ChartObject, Citation } from '../../types/AppTypes';

/**
 * Ensure a date string is treated as UTC.
 * Backend stores UTC via datetime.utcnow().isoformat() without 'Z' suffix,
 * so JavaScript's Date constructor would treat it as local time.
 */
const parseAsUTC = (dateString: string): Date => {
  // If already has timezone info (Z, +, -offset), parse as-is
  if (/Z|[+-]\d{2}:\d{2}$/.test(dateString)) {
    return new Date(dateString);
  }
  // Append 'Z' to treat as UTC
  return new Date(dateString + 'Z');
};

/**
 * Format timestamp for display in Japan timezone
 */
export const formatTimestamp = (dateString: string | undefined): string => {
  if (!dateString) return '';
  try {
    const date = parseAsUTC(dateString);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Tokyo'
    });
  } catch {
    return '';
  }
};

/**
 * Chart type pattern for detecting chart JSON
 */
export const CHART_TYPE_PATTERN = /\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/g;

/**
 * Check if content looks like chart JSON
 */
export const looksLikeChartJson = (content: string): boolean => {
  const chartJsonPattern = /```json|"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/i;
  return chartJsonPattern.test(content);
};

/**
 * Helper function to deduplicate charts based on their data
 */
export const deduplicateCharts = (charts: ChartObject[]): ChartObject[] => {
  const seen = new Set<string>();
  const unique: ChartObject[] = [];

  for (const chart of charts) {
    let signature = '';
    try {
      const type = chart.type || chart.chartType || '';
      const labels = chart.data?.labels?.join(',') || '';
      const firstDataset = chart.data?.datasets?.[0];
      const dataValues = firstDataset && Array.isArray(firstDataset.data) ? (firstDataset.data as unknown[]).join(',') : '';
      signature = type + '|' + labels + '|' + dataValues;
    } catch {
      signature = JSON.stringify(chart);
    }

    if (!seen.has(signature)) {
      seen.add(signature);
      unique.push(chart);
    }
  }

  return unique;
};

/**
 * Extract text excluding chart JSON (for streaming display)
 */
export const extractTextExcludingChart = (content: string): string => {
  let textPart = content;

  // Remove ```json ... ``` blocks (complete or incomplete)
  textPart = textPart.replace(/```json[\s\S]*?(```|$)/g, '');

  // Remove raw JSON objects with chart type
  const rawJsonStart = textPart.match(/\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/i);
  if (rawJsonStart && rawJsonStart.index !== undefined) {
    const beforeJson = textPart.substring(0, rawJsonStart.index);
    const afterJsonStart = textPart.substring(rawJsonStart.index);
    // Find where JSON ends (or end of string if incomplete)
    let braceCount = 0;
    let jsonEndIndex = afterJsonStart.length;
    for (let i = 0; i < afterJsonStart.length; i++) {
      if (afterJsonStart[i] === '{') braceCount++;
      else if (afterJsonStart[i] === '}') {
        braceCount--;
        if (braceCount === 0) {
          jsonEndIndex = i + 1;
          break;
        }
      }
    }
    const afterJson = afterJsonStart.substring(jsonEndIndex);
    textPart = (beforeJson + afterJson).trim();
  }

  // Clean up extra whitespace
  textPart = textPart.replace(/\n{3,}/g, '\n\n').trim();
  return textPart;
};

/**
 * Unwrap {"charts": [...]} wrapper into individual chart objects.
 * Also handles nested wrappers inside code blocks or raw JSON.
 */
const unwrapChartsArray = (jsonStr: string): ChartObject[] | null => {
  try {
    const parsed = JSON.parse(jsonStr);
    if (parsed && typeof parsed === 'object' && 'charts' in parsed && Array.isArray(parsed.charts)) {
      return parsed.charts.filter(
        (c: unknown) => c && typeof c === 'object' && ('type' in (c as Record<string, unknown>) || 'chartType' in (c as Record<string, unknown>)) && 'data' in (c as Record<string, unknown>)
      ) as ChartObject[];
    }
  } catch {
    // Not valid JSON or not a charts wrapper
  }
  return null;
};

/**
 * Extract Chart.js JSON(s) from mixed text/JSON content
 */
export const extractChartsFromText = (content: string): { textPart: string; charts: ChartObject[] } => {
  const charts: ChartObject[] = [];
  let textPart = content;

  // STEP 0: Try to detect {"charts": [...]} wrapper in code blocks or raw JSON
  const chartsWrapperCodeBlock = /```json\s*([\s\S]*?"charts"\s*:\s*\[[\s\S]*?)```/g;
  let wrapperMatch;
  while ((wrapperMatch = chartsWrapperCodeBlock.exec(content)) !== null) {
    const unwrapped = unwrapChartsArray(wrapperMatch[1].trim());
    if (unwrapped && unwrapped.length > 0) {
      charts.push(...unwrapped);
      textPart = textPart.substring(0, wrapperMatch.index) + textPart.substring(wrapperMatch.index + wrapperMatch[0].length);
    }
  }

  // Also try raw JSON {"charts": ...} without code blocks
  if (charts.length === 0) {
    const chartsKeyPattern = /\{\s*"charts"\s*:\s*\[/g;
    let rawMatch;
    const wrapperPositions: { start: number; end: number; charts: ChartObject[] }[] = [];
    while ((rawMatch = chartsKeyPattern.exec(content)) !== null) {
      let braceCount = 0;
      let endIndex = -1;
      for (let i = rawMatch.index; i < content.length; i++) {
        if (content[i] === '{') braceCount++;
        else if (content[i] === '}') {
          braceCount--;
          if (braceCount === 0) { endIndex = i; break; }
        }
      }
      if (endIndex !== -1) {
        const unwrapped = unwrapChartsArray(content.substring(rawMatch.index, endIndex + 1));
        if (unwrapped && unwrapped.length > 0) {
          wrapperPositions.push({ start: rawMatch.index, end: endIndex + 1, charts: unwrapped });
        }
      }
    }
    for (let i = wrapperPositions.length - 1; i >= 0; i--) {
      charts.unshift(...wrapperPositions[i].charts);
      textPart = textPart.substring(0, wrapperPositions[i].start) + textPart.substring(wrapperPositions[i].end);
    }
  }

  if (charts.length > 0) {
    textPart = textPart.replace(/Chart\.js[（(][^）)]*[）)][^\n]*/g, '').trim();
    textPart = textPart.replace(/\n{3,}/g, '\n\n');
    return { textPart, charts: deduplicateCharts(charts) };
  }

  // STEP 1: First try to extract from Markdown code blocks (```json ... ```)
  const codeBlockPattern = /```json\s*([\s\S]*?)```/g;
  let codeBlockMatch;
  const codeBlockPositions: { start: number; end: number; json: ChartObject }[] = [];

  while ((codeBlockMatch = codeBlockPattern.exec(content)) !== null) {
    const jsonStr = codeBlockMatch[1].trim();
    try {
      const parsed = JSON.parse(jsonStr);
      if (parsed && parsed.data && parsed.type && parsed.data.datasets) {
        codeBlockPositions.push({
          start: codeBlockMatch.index,
          end: codeBlockMatch.index + codeBlockMatch[0].length,
          json: parsed
        });
      }
    } catch {
      // Invalid JSON in code block, skip
    }
  }

  // If found in code blocks, also try unwrapping {"charts": [...]} inside each
  if (codeBlockPositions.length > 0) {
    for (let i = codeBlockPositions.length - 1; i >= 0; i--) {
      const pos = codeBlockPositions[i];
      charts.unshift(pos.json);
      textPart = textPart.substring(0, pos.start) + textPart.substring(pos.end);
    }
    textPart = textPart.replace(/\n{3,}/g, '\n\n').trim();
    const uniqueCharts = deduplicateCharts(charts);
    return { textPart, charts: uniqueCharts };
  }

  // STEP 2: Fallback - Find raw JSON using bracket counting
  const chartTypePattern = /\{\s*"type"\s*:\s*"(bar|pie|line|doughnut|horizontalBar|radar|polarArea|scatter|bubble)"/g;
  const jsonPositions: { start: number; end: number; json: ChartObject }[] = [];

  let match;
  while ((match = chartTypePattern.exec(content)) !== null) {
    const startIndex = match.index;

    // Find the matching closing brace using bracket counting
    let braceCount = 0;
    let endIndex = -1;

    for (let i = startIndex; i < content.length; i++) {
      if (content[i] === '{') braceCount++;
      else if (content[i] === '}') {
        braceCount--;
        if (braceCount === 0) {
          endIndex = i;
          break;
        }
      }
    }

    if (endIndex !== -1) {
      const jsonStr = content.substring(startIndex, endIndex + 1);
      try {
        const parsed = JSON.parse(jsonStr);
        if (parsed && parsed.data && parsed.type && parsed.data.datasets) {
          jsonPositions.push({ start: startIndex, end: endIndex + 1, json: parsed });
        }
      } catch {
        // Invalid JSON, skip
      }
    }
  }

  // Remove JSON from text (in reverse order to maintain indices)
  for (let i = jsonPositions.length - 1; i >= 0; i--) {
    const pos = jsonPositions[i];
    charts.unshift(pos.json);
    textPart = textPart.substring(0, pos.start) + textPart.substring(pos.end);
  }

  // Clean up extra whitespace and "Chart.js（...）" labels
  textPart = textPart.replace(/Chart\.js（[^）]*）[^\n]*/g, '').trim();
  textPart = textPart.replace(/\n{3,}/g, '\n\n');

  const uniqueCharts = deduplicateCharts(charts);
  return { textPart, charts: uniqueCharts };
};

/**
 * Strip HTML tags from content
 */
export const stripHtmlTags = (content: string): string => {
  return content.replace(/<[^>]*>/g, '');
};

/**
 * Check if content contains HTML tags
 */
export const containsHtml = (content: string): boolean => {
  return /<\/?[a-z][\s\S]*>/i.test(content);
};

/**
 * Convert legacy [[N]](url) citation markers to standard markdown [N](url)
 * for backward compatibility with past conversation history.
 */
export const convertLegacyCitationMarkers = (text: string): string => {
  // [[N]](url) → [N](url)
  return text.replace(/\[\[(\d+)\]\]\(([^)]+)\)/g, '[$1]($2)');
};

/**
 * Convert inline [N] plain-text citation markers to clickable markdown links
 * using the citations array. This ensures inline numbers match the Citations UI.
 *
 * Matches [N] not already followed by ( (which would be [N](url)), and not
 * preceded by [ (which would be [[N]]).
 */
export const linkInlineCitations = (text: string, citations: Citation[]): string => {
  if (!citations || citations.length === 0) return text;

  return text.replace(/(?<!\[)\[(\d+)\](?!\(|\])/g, (match, numStr) => {
    const num = parseInt(numStr, 10);
    if (num >= 1 && num <= citations.length) {
      const citation = citations[num - 1];
      if (citation?.url) {
        return `[${num}](${citation.url})`;
      }
    }
    return match;
  });
};

/**
 * Add target="_blank" and rel="noopener noreferrer" to all links in HTML content
 * This ensures external links open in new tabs safely
 */
export const addTargetBlankToLinks = (html: string): string => {
  // Match <a> tags and add target="_blank" rel="noopener noreferrer" if not present
  return html.replace(
    /<a\s+([^>]*?)>/gi,
    (match, attributes) => {
      // Skip if already has target
      if (/target\s*=/i.test(attributes)) {
        return match;
      }
      return `<a ${attributes} target="_blank" rel="noopener noreferrer">`;
    }
  );
};

/**
 * Sanitize HTML content to prevent XSS attacks, then add target="_blank" to links.
 * Uses DOMPurify to remove dangerous elements (script, event handlers, etc.)
 * while preserving safe formatting tags.
 */
export const sanitizeAndProcessLinks = (html: string): string => {
  const clean = DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'rel'],
    ADD_TAGS: ['table', 'thead', 'tbody', 'tr', 'th', 'td'],
  });
  return addTargetBlankToLinks(clean);
};
