/**
 * Format timestamp for display
 */
export const formatTimestamp = (dateString: string | undefined): string => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
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
export const deduplicateCharts = (charts: any[]): any[] => {
  const seen = new Set<string>();
  const unique: any[] = [];

  for (const chart of charts) {
    let signature = '';
    try {
      const type = chart.type || chart.chartType || '';
      const labels = chart.data?.labels?.join(',') || '';
      const firstDataset = chart.data?.datasets?.[0];
      const dataValues = firstDataset?.data?.join(',') || '';
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
 * Extract Chart.js JSON(s) from mixed text/JSON content
 */
export const extractChartsFromText = (content: string): { textPart: string; charts: any[] } => {
  const charts: any[] = [];
  let textPart = content;

  // STEP 1: First try to extract from Markdown code blocks (```json ... ```)
  const codeBlockPattern = /```json\s*([\s\S]*?)```/g;
  let codeBlockMatch;
  const codeBlockPositions: { start: number; end: number; json: any }[] = [];

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

  // If found in code blocks, use those
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
  const jsonPositions: { start: number; end: number; json: any }[] = [];

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
