import {
    Chart as ChartJS,
    type ChartTypeRegistry,
    type Plugin,
    registerables,
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
    const bgColor = (chart.config.options as any)?._bgColor;
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
    data: any;
    options: any;
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
    const datasets = chartContent?.data?.datasets?.map((ds: any) =>
      ds?.data?.join(',') || ''
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
  const themedScales: Record<string, any> = {};
  const originalScales = chartContent?.options?.scales || {};

  // Process all scales (x, y, y1, y2, etc.)
  for (const scaleKey of Object.keys(originalScales)) {
    themedScales[scaleKey] = {
      ...originalScales[scaleKey],
      ticks: {
        ...originalScales[scaleKey]?.ticks,
        color: colors.textColor,
      },
      grid: {
        ...originalScales[scaleKey]?.grid,
        color: colors.gridColor,
      },
      title: {
        ...originalScales[scaleKey]?.title,
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
        ...chartContent?.options?.plugins,
        legend: {
          ...chartContent?.options?.plugins?.legend,
          labels: {
            ...chartContent?.options?.plugins?.legend?.labels,
            color: colors.legendColor,
          },
        },
        title: {
          ...chartContent?.options?.plugins?.title,
          color: colors.textColor,
        },
        tooltip: {
          ...chartContent?.options?.plugins?.tooltip,
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
    const tooltipCallbacks =
      chartConfigData.options?.plugins?.tooltip?.callbacks;
    const tooltipCb = tooltipCallbacks?.label;

    if (typeof tooltipCb !== "function") {
      if (tooltipCallbacks) {
        tooltipCallbacks.label = (tooltipItem: any) => {
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

    const myChart = new ChartJS(chartRefCurrent, chartConfigData);
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
