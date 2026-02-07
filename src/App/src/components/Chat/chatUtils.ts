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
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    const now = Date.now();
    const remaining = delay - (now - lastCall);
    if (remaining <= 0) {
      if (timer) { clearTimeout(timer); timer = null; }
      lastCall = now;
      fn(...args);
    } else if (!timer) {
      timer = setTimeout(() => {
        lastCall = Date.now();
        timer = null;
        fn(...args);
      }, remaining);
    }
  };
};

// Tool event parsing: Extract tool events from streaming text
const TOOL_EVENT_REGEX = /__TOOL_EVENT__(.*?)__END_TOOL_EVENT__/g;

// Reasoning content parsing: Extract GPT-5 thinking content from streaming text
// REPLACE marker indicates cumulative text that should replace (not append)
const REASONING_REPLACE_REGEX =
  /__REASONING_REPLACE__([\s\S]*?)__END_REASONING_REPLACE__/g;

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
      if (process.env.NODE_ENV === 'development') console.warn("Failed to parse tool event:", e);
    }
  }

  return { events, cleanedText };
};

/**
 * Parse reasoning content from streaming text and return cleaned text
 * SDK sends cumulative text, so we use REPLACE mode to replace (not append)
 * @param text Raw streaming text containing potential reasoning markers
 * @returns { reasoningReplace: string | null, cleanedText: string }
 *          reasoningReplace is the full cumulative text to replace current state
 */
export const parseReasoningContent = (
  text: string
): { reasoningReplace: string | null; cleanedText: string } => {
  let reasoningReplace: string | null = null;
  let cleanedText = text;

  // Use REPLACE regex - SDK sends cumulative text that should replace state
  const matches = Array.from(text.matchAll(REASONING_REPLACE_REGEX));
  for (const match of matches) {
    if (match[1]) {
      // Take the last match as the most up-to-date cumulative text
      reasoningReplace = match[1];
      cleanedText = cleanedText.replace(match[0], "");
    }
  }

  return { reasoningReplace, cleanedText };
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
