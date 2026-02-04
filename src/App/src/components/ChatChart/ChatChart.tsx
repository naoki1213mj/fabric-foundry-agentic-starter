import {
    Chart as ChartJS,
    type ChartTypeRegistry,
    registerables,
} from "chart.js";
import React, { memo, useEffect, useMemo, useRef } from "react";

const chartTypes = {
  barChart: "bar",
  pieChart: "pie",
  doughNutChart: "doughnut",
  lineChart: "line",
};

// Get theme-aware colors for chart text
const getChartColors = () => {
  const isDarkMode = document.documentElement.getAttribute('data-theme') === 'dark';
  return {
    textColor: isDarkMode ? '#f8fafc' : '#1e293b',
    gridColor: isDarkMode ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0, 0, 0, 0.1)',
    legendColor: isDarkMode ? '#cbd5e1' : '#475569',
  };
};
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

  // Memoize the chart data signature to prevent unnecessary re-renders
  const chartSignature = useMemo(() => getChartDataSignature(chartContent), [chartContent]);

useEffect(() => {
  // Skip if chart data hasn't actually changed
  if (!validChart || !chartRef.current || !chartContent.data || !chartContent?.type) {
    return;
  }

  // Destroy existing chart before creating new one
  if (chartInstanceRef.current) {
    chartInstanceRef.current.destroy();
    chartInstanceRef.current = null;
  }

  ChartJS.register(...registerables);

  // Get theme-aware colors
  const colors = getChartColors();

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

    const myChart = new ChartJS(chartRef.current, chartConfigData);
    chartInstanceRef.current = myChart;

    const resizeObserver = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        if (chartRef?.current && myChart) {
          myChart?.resize();
          myChart?.update();
        }
      });
    });

    if (chartRef?.current?.parentElement !== null) {
      resizeObserver.observe(chartRef.current.parentElement);
    }

    return () => {
      if (
        chartRef?.current !== null &&
        chartRef?.current?.parentElement !== null
      ) {
        resizeObserver.unobserve(chartRef?.current?.parentElement);
      }
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy();
        chartInstanceRef.current = null;
      }
    };
  // Use chartSignature as dependency - chart only re-creates when actual data changes
}, [chartSignature, validChart]);

  return (
    <div style={{ maxHeight: 350 }}>
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
