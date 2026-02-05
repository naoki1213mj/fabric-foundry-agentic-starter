import type { ToolEvent } from "../../types/AppTypes";

/**
 * Throttle utility for scroll during streaming
 * Prevents excessive scroll calls that cause flickering
 */
export const throttle = <T extends (...args: Parameters<T>) => void>(
  fn: T,
  delay: number
) => {
  let lastCall = 0;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      fn(...args);
    }
  };
};

// Tool event parsing: Extract tool events from streaming text
const TOOL_EVENT_REGEX = /__TOOL_EVENT__(.*?)__END_TOOL_EVENT__/g;

/**
 * Parse tool events from streaming text and return cleaned text
 * @param text Raw streaming text containing potential tool events
 * @returns { events: ToolEvent[], cleanedText: string }
 */
export const parseToolEvents = (
  text: string
): { events: ToolEvent[]; cleanedText: string } => {
  const events: ToolEvent[] = [];
  let cleanedText = text;

  // Use Array.from for ES5 compatibility (matchAll returns IterableIterator)
  const matches = Array.from(text.matchAll(TOOL_EVENT_REGEX));
  for (const match of matches) {
    try {
      const eventJson = match[1];
      const event = JSON.parse(eventJson) as ToolEvent;
      events.push(event);
      // Remove the tool event marker from the text
      cleanedText = cleanedText.replace(match[0], "");
    } catch (e) {
      // Skip malformed tool events
      console.warn("Failed to parse tool event:", e);
    }
  }

  return { events, cleanedText };
};

/**
 * Chart query detection keywords
 */
const CHART_KEYWORDS = [
  "chart",
  "graph",
  "visualize",
  "plot",
  "グラフ",
  "チャート",
  "可視化",
  "図",
  "棒グラフ",
  "円グラフ",
  "折れ線",
  "折れ線グラフ",
];

/**
 * Check if a query is requesting a chart visualization
 */
export const isChartQuery = (query: string): boolean => {
  const lowerCaseQuery = query.toLowerCase();

  return CHART_KEYWORDS.some((keyword) => {
    // English words use word boundary, Japanese uses partial match
    if (/^[a-z]+$/i.test(keyword)) {
      return new RegExp(`\\b${keyword}\\b`).test(lowerCaseQuery);
    }
    return lowerCaseQuery.includes(keyword);
  });
};
