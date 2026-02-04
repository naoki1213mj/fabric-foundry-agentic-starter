
export type FilterObject = {
  key: string;
  displayValue: string;
};
export type FilterMetaData = Record<string, FilterObject[]>;
export type SelectedFilters = Record<string, string | string[]>;

type Roles = "assistant" | "user" | "error";

export enum Feedback {
  Neutral = "neutral",
  Positive = "positive",
  Negative = "negative",
  MissingCitation = "missing_citation",
  WrongCitation = "wrong_citation",
  OutOfScope = "out_of_scope",
  InaccurateOrIrrelevant = "inaccurate_or_irrelevant",
  OtherUnhelpful = "other_unhelpful",
  HateSpeech = "hate_speech",
  Violent = "violent",
  Sexual = "sexual",
  Manipulative = "manipulative",
  OtherHarmful = "other_harmlful",
}

export type ChatMessage = {
  id: string;
  role: string;
  content: string | ChartDataResponse;
  end_turn?: boolean;
  date: string;
  feedback?: Feedback;
  context?: string;
  contentType?: "text" | "image";
  citations?: string
};

export type AgentMode = "sql_only" | "multi_tool" | "handoff" | "magentic";

export type ReasoningEffort = "minimal" | "low" | "medium";

export type ConversationRequest = {
  id?: string;
  query: string;
  agentMode?: AgentMode;
  reasoningEffort?: ReasoningEffort;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
  error?: string;
};

export type Conversation = {
  id: string;
  title: string;
  messages: ChatMessage[];
  date: string;
  updatedAt?: string;
};

export type AppConfig = Record<
  string,
  Record<string, number> | Record<string, Record<string, number>>
> | null;

export interface ChartLayout {
  row: number;
  col: number;
  width?: string;
}
export interface ChartDataItem {
  [x: string]: any;
  name: string;
  count: number;
  value: string;
  text: string;
  size: number;
  color?: string;
  percentage?: number;
  description?: string;
  unit_of_measurement?: string;
  average_sentiment: "positive" | "negative" | "neutral";
}
export interface ChartConfigItem {
  type: string;
  title: string;
  data: ChartDataItem[];
  layout: ChartLayout;
  id: string;
  domId: string;
}

export enum ChatCompletionType {
  ChatCompletion = "chat.completion",
  ChatCompletionChunk = "chat.completion.chunk",
}

export type ChatResponseChoice = {
  messages: ChatMessage[];
};

export type ChartDataResponse = {
  answer: string;
  data: any,
  options: any,
  type: string
};

export type ChatResponse = {
  id: string;
  model: string;
  created: number;
  object: ChatCompletionType | any;
  choices: ChatResponseChoice[];
  history_metadata: {
    conversation_id: string;
    title: string;
    date: string;
  };
  error?: any;
  chartType?: string;
  chartOptions: any;
  chartData: {
    datasets?: any[];
    labels: any[];
  };
};

export enum CosmosDBStatus {
  NotConfigured = "CosmosDB is not configured",
  NotWorking = "CosmosDB is not working",
  InvalidCredentials = "CosmosDB has invalid credentials",
  InvalidDatabase = "Invalid CosmosDB database name",
  InvalidContainer = "Invalid CosmosDB container name",
  Working = "CosmosDB is configured and working",
}

export type CosmosDBHealth = {
  cosmosDB: boolean;
  status: string;
};

export type HistoryMetaData = {
  conversation_id: string;
  title: string;
  date: string;
};

export type ParsedChunk = {
  error?: string;
  id: string;
  model: string;
  created: number;
  object: string;
  choices: [
    {
      messages: [
        {
          content: string;
          role: string;
          citations?: string;
        }
      ];
      history_metadata: object;
    }
  ];
  "apim-request-id": string;
};

export type ToolMessageContent = {
  citations: Citation[]
}

export type Citation = {
  content: string;
  id: string;
  title: string | null;
  filepath: string | null;
  url: string | null;
  metadata: string | null;
  chunk_id: string | null;
  reindex_id: string | null;
}

// Tool status event for real-time tool usage visualization
export type ToolStatus = "started" | "completed" | "error";

export type ToolEvent = {
  type: "tool_event";
  tool: string;
  status: ToolStatus;
  message?: string;
  timestamp: string;
}

// Tool display configuration
export const TOOL_DISPLAY_CONFIG: Record<string, { icon: string; label: string }> = {
  // Core tools
  run_sql_query: { icon: "📊", label: "SQLクエリを実行中" },
  search_web: { icon: "🌐", label: "Web検索中" },
  search_documents: { icon: "🔍", label: "製品仕様書を検索中" },
  // MCP Business Analytics - Sales Analysis
  calculate_yoy_growth: { icon: "📈", label: "前年比成長率を計算中" },
  calculate_mom_growth: { icon: "📊", label: "前月比成長率を計算中" },
  calculate_moving_average: { icon: "📉", label: "移動平均を計算中" },
  calculate_abc_analysis: { icon: "🏷️", label: "ABC分析を実行中" },
  calculate_sales_forecast: { icon: "🔮", label: "売上予測を実行中" },
  // MCP Business Analytics - Customer Segmentation
  calculate_rfm_score: { icon: "👥", label: "RFMスコアを計算中" },
  classify_customer_segment: { icon: "🎯", label: "顧客セグメントを分類中" },
  calculate_clv: { icon: "💰", label: "顧客生涯価値を計算中" },
  recommend_next_action: { icon: "💡", label: "次のアクションを推奨中" },
  // MCP Business Analytics - Inventory Analysis
  calculate_inventory_turnover: { icon: "🔄", label: "在庫回転率を計算中" },
  calculate_reorder_point: { icon: "📦", label: "再発注点を計算中" },
  identify_slow_moving_inventory: { icon: "🐌", label: "滞留在庫を特定中" },
  // MCP Business Analytics - Product Comparison
  compare_products: { icon: "⚖️", label: "製品比較を実行中" },
  calculate_price_performance: { icon: "💵", label: "価格性能比を計算中" },
  calculate_bundle_discount: { icon: "🎁", label: "バンドル割引を計算中" },
  // Legacy compatibility (from previous config)
  analyze_yoy_performance: { icon: "📈", label: "前年比分析を実行中" },
  analyze_rfm_segments: { icon: "👥", label: "顧客RFM分析を実行中" },
  analyze_inventory: { icon: "📦", label: "在庫分析を実行中" },
  analyze_seasonal_trends: { icon: "🗓️", label: "季節トレンド分析を実行中" },
  analyze_regional_performance: { icon: "🗺️", label: "地域分析を実行中" },
};
