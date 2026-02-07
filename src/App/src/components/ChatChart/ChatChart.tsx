import {
    Chart as ChartJS,
    registerables,
    type ChartConfiguration,
    type ChartTypeRegistry,
    type Plugin,
} from "chart.js";
import React, { memo, useEffect, useMemo, useRef, useState } from "react";

const chartTypes = {
  barChart: "bar",
  pieChart: "pie",
  doughNutChart: "doughnut",
  lineChart: "line",
};

// Hook to reactively detect theme changes via MutationObserver
const useThemeMode = (): string => {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute("data-theme") || "light"
  );

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const current = document.documentElement.getAttribute("data-theme") || "light";
      setTheme(current);
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  return theme;
};

// Get theme-aware colors for chart text
const getChartColors = (themeMode: string) => {
  const isDarkMode = themeMode === "dark";
  return {
    textColor: isDarkMode ? '#f8fafc' : '#1e293b',
    gridColor: isDarkMode ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0, 0, 0, 0.1)',
    legendColor: isDarkMode ? '#cbd5e1' : '#475569',
    backgroundColor: isDarkMode ? '#1e293b' : '#ffffff',
    tooltipBg: isDarkMode ? '#334155' : '#ffffff',
    tooltipText: isDarkMode ? '#f1f5f9' : '#1e293b',
    tooltipBorder: isDarkMode ? '#475569' : '#e2e8f0',
  };
};

// Chart.js plugin to draw background color on canvas
const backgroundPlugin: Plugin = {
  id: 'customCanvasBackground',
  beforeDraw: (chart) => {
    const ctx = chart.ctx;
    const { width, height } = chart;
    const bgColor = (chart.config.options as Record<string, unknown>)?._bgColor as string | undefined;
    if (bgColor) {
      ctx.save();
      ctx.fillStyle = bgColor;
      // Use rounded rectangle for consistency with UI
      const radius = 10;
      ctx.beginPath();
      ctx.moveTo(radius, 0);
      ctx.lineTo(width - radius, 0);
      ctx.quadraticCurveTo(width, 0, width, radius);
      ctx.lineTo(width, height - radius);
      ctx.quadraticCurveTo(width, height, width - radius, height);
      ctx.lineTo(radius, height);
      ctx.quadraticCurveTo(0, height, 0, height - radius);
      ctx.lineTo(0, radius);
      ctx.quadraticCurveTo(0, 0, radius, 0);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
  },
};

// Register Chart.js components once at module level (idempotent but avoids per-render overhead)
ChartJS.register(...registerables, backgroundPlugin);

interface ChartProps {
  chartContent: {
    data: {
      labels?: (string | number)[];
      datasets?: Array<Record<string, unknown>>;
      [key: string]: unknown;
    };
    options?: Record<string, unknown>;
    type: string;
  };
}


const isValidChartConfig = (content: ChartProps["chartContent"]): boolean => {
  // Basic check for required fields
  if (!content || typeof content !== "object") return false;
  if (!content.data || !content.type) return false;
  // Chart.js expects data.datasets to be an array for most chart types
  if (
    ["bar", "line", "horizontalBar", "doughnut", "pie"].includes(content.type)
  ) {
    if (!content.data.datasets || !Array.isArray(content.data.datasets)) return false;
  }
  return true;
};

// Create a stable signature for chart data to use as dependency
const getChartDataSignature = (chartContent: ChartProps["chartContent"]): string => {
  try {
    const type = chartContent?.type || '';
    const labels = chartContent?.data?.labels?.join(',') || '';
    const datasets = chartContent?.data?.datasets?.map((ds: Record<string, unknown>) =>
      Array.isArray(ds?.data) ? (ds.data as unknown[]).join(',') : ''
    ).join('|') || '';
    return `${type}:${labels}:${datasets}`;
  } catch {
    return JSON.stringify(chartContent);
  }
};

const ChatChart: React.FC<ChartProps> = memo(({ chartContent }) => {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstanceRef = useRef<ChartJS | null>(null);
  const validChart = isValidChartConfig(chartContent);
  const themeMode = useThemeMode();

  // Memoize the chart data signature to prevent unnecessary re-renders
  const chartSignature = useMemo(() => getChartDataSignature(chartContent), [chartContent]);

  useEffect(() => {
    // Copy ref to local variable for cleanup
    const chartRefCurrent = chartRef.current;

    // Skip if chart data hasn't actually changed
    if (!validChart || !chartRefCurrent || !chartContent.data || !chartContent?.type) {
      return;
    }

  // Destroy existing chart before creating new one
  if (chartInstanceRef.current) {
    chartInstanceRef.current.destroy();
    chartInstanceRef.current = null;
  }

  // Get theme-aware colors
  const colors = getChartColors(themeMode);

  // Apply theme colors to all scales dynamically
  const themedScales: Record<string, Record<string, unknown>> = {};
  const originalScales = (chartContent?.options?.scales || {}) as Record<string, Record<string, unknown>>;

  // Process all scales (x, y, y1, y2, etc.)
  for (const scaleKey of Object.keys(originalScales)) {
    const scale = originalScales[scaleKey];
    const ticks = (scale?.ticks ?? {}) as Record<string, unknown>;
    const grid = (scale?.grid ?? {}) as Record<string, unknown>;
    const title = (scale?.title ?? {}) as Record<string, unknown>;
    themedScales[scaleKey] = {
      ...scale,
      ticks: {
        ...ticks,
        color: colors.textColor,
      },
      grid: {
        ...grid,
        color: colors.gridColor,
      },
      title: {
        ...title,
        color: colors.textColor,
      },
    };
  }

  // Ensure at least x and y scales have theme colors even if not in original
  if (!themedScales.x) {
    themedScales.x = {
      ticks: { color: colors.textColor },
      grid: { color: colors.gridColor },
      title: { color: colors.textColor },
    };
  }
  if (!themedScales.y) {
    themedScales.y = {
      ticks: { color: colors.textColor },
      grid: { color: colors.gridColor },
      title: { color: colors.textColor },
    };
  }

  const chartConfigData = {
    type:
      chartContent.type === "horizontalBar"
        ? chartTypes.barChart
        : (chartContent.type as keyof ChartTypeRegistry),
    data: { ...chartContent.data },
    options: {
      ...chartContent?.options,
      responsive: false,
      // Disable animations to prevent flickering during streaming
      animation: false,
      // Store background color for plugin
      _bgColor: colors.backgroundColor,
      indexAxis:
        chartContent.type === "horizontalBar"
          ? "y"
          : chartContent?.options?.indexAxis,
      // Dark mode support for text colors - apply to all scales
      scales: themedScales,
      plugins: {
        ...((chartContent?.options?.plugins ?? {}) as Record<string, unknown>),
        legend: {
          ...(((chartContent?.options?.plugins as Record<string, unknown>)?.legend ?? {}) as Record<string, unknown>),
          labels: {
            ...((((chartContent?.options?.plugins as Record<string, unknown>)?.legend as Record<string, unknown>)?.labels ?? {}) as Record<string, unknown>),
            color: colors.legendColor,
          },
        },
        title: {
          ...(((chartContent?.options?.plugins as Record<string, unknown>)?.title ?? {}) as Record<string, unknown>),
          color: colors.textColor,
        },
        tooltip: {
          ...(((chartContent?.options?.plugins as Record<string, unknown>)?.tooltip ?? {}) as Record<string, unknown>),
          backgroundColor: colors.tooltipBg,
          titleColor: colors.tooltipText,
          bodyColor: colors.tooltipText,
          borderColor: colors.tooltipBorder,
          borderWidth: 1,
        },
      },
    },
  };

    // Restore tooltip callback if it’s missing or a string placeholder
    const plugins = chartConfigData.options?.plugins as Record<string, Record<string, unknown>> | undefined;
    const tooltipCallbacks = plugins?.tooltip?.callbacks as Record<string, unknown> | undefined;
    const tooltipCb = tooltipCallbacks?.label;

    if (typeof tooltipCb !== "function") {
      if (tooltipCallbacks) {
        tooltipCallbacks.label = (tooltipItem: { label?: string; raw?: unknown }) => {
          try {
            const label = tooltipItem.label || "";
            const value =
              typeof tooltipItem.raw === "number"
                ? tooltipItem.raw.toLocaleString()
                : tooltipItem.raw;
            return `${label}: ${value}`;
          } catch {
            return tooltipItem.label ?? "";
          }
        };
      }
    }

    const myChart = new ChartJS(chartRefCurrent, chartConfigData as unknown as ChartConfiguration);
    chartInstanceRef.current = myChart;

    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        if (chartRefCurrent && myChart) {
          myChart?.resize();
          myChart?.update();
        }
      });
    });

    if (chartRefCurrent?.parentElement) {
      resizeObserver.observe(chartRefCurrent.parentElement);
    }

    return () => {
      if (chartRefCurrent?.parentElement) {
        resizeObserver.unobserve(chartRefCurrent.parentElement);
      }
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
  // Use chartSignature as dependency - chart only re-creates when actual data changes
  }, [chartSignature, validChart, chartContent, themeMode]);

  return (
    <div style={{ maxHeight: 350, borderRadius: 'var(--radius-md, 10px)', overflow: 'hidden' }}>
      {validChart ? (
        <canvas ref={chartRef} />
      ) : (
        <div style={{
          padding: 16,
          color: 'var(--color-accent-error, #b71c1c)',
          background: 'var(--color-accent-error-light, #fff3f3)',
          borderRadius: 8
        }}>
          <strong>Unable to render chart. Here is the raw response:</strong>
          <pre style={{
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            marginTop: 8,
            color: 'var(--color-text-secondary, #666)'
          }}>
            {JSON.stringify(chartContent, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
});

ChatChart.displayName = 'ChatChart';

export default ChatChart;
