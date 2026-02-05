
export type FilterObject = {
  key: string;
  displayValue: string;
};
export type FilterMetaData = Record<string, FilterObject[]>;
export type SelectedFilters = Record<string, string | string[]>;

export type Roles = "assistant" | "user" | "error";

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

// Model types available for selection
export type ModelType = "gpt-5" | "gpt-4o-mini";

// Model parameters that can be adjusted via UI
export interface ModelParameters {
  model: ModelType;
  temperature?: number;        // 0.0-2.0, for gpt-4o-mini
  reasoningEffort?: ReasoningEffort; // for gpt-5
}

export type ConversationRequest = {
  id?: string;
  query: string;
  agentMode?: AgentMode;
  reasoningEffort?: ReasoningEffort;
  model?: ModelType;
  temperature?: number;
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
// labelは完了後の表示用（「〜中」ではなく名詞形）
// categoryでグループ分け（MCP=ビジネス分析ツール）
export const TOOL_DISPLAY_CONFIG: Record<string, { icon: string; label: string; category?: string }> = {
  // Core tools (Agent内蔵)
  run_sql_query: { icon: "📊", label: "SQLクエリ", category: "データ取得" },
  search_web: { icon: "🌐", label: "Web検索", category: "情報検索" },
  search_documents: { icon: "🔍", label: "製品仕様書検索", category: "情報検索" },
  // MCP Business Analytics - Sales Analysis
  calculate_yoy_growth: { icon: "📈", label: "前年比成長率", category: "売上分析" },
  calculate_mom_growth: { icon: "📊", label: "前月比成長率", category: "売上分析" },
  calculate_moving_average: { icon: "📉", label: "移動平均", category: "売上分析" },
  calculate_abc_analysis: { icon: "🏷️", label: "ABC分析", category: "売上分析" },
  calculate_sales_forecast: { icon: "🔮", label: "売上予測", category: "売上分析" },
  // MCP Business Analytics - Customer Segmentation
  calculate_rfm_score: { icon: "👥", label: "RFMスコア", category: "顧客分析" },
  classify_customer_segment: { icon: "🎯", label: "顧客セグメント分類", category: "顧客分析" },
  calculate_clv: { icon: "💰", label: "顧客生涯価値", category: "顧客分析" },
  recommend_next_action: { icon: "💡", label: "次のアクション推奨", category: "顧客分析" },
  // MCP Business Analytics - Inventory Analysis
  calculate_inventory_turnover: { icon: "🔄", label: "在庫回転率", category: "在庫分析" },
  calculate_reorder_point: { icon: "📦", label: "再発注点", category: "在庫分析" },
  identify_slow_moving_inventory: { icon: "🐌", label: "滞留在庫特定", category: "在庫分析" },
  // MCP Business Analytics - Product Comparison
  compare_products: { icon: "⚖️", label: "製品比較", category: "製品分析" },
  calculate_price_performance: { icon: "💵", label: "価格性能比", category: "製品分析" },
  calculate_bundle_discount: { icon: "🎁", label: "バンドル割引", category: "製品分析" },
  // Legacy compatibility
  analyze_yoy_performance: { icon: "📈", label: "前年比分析", category: "売上分析" },
  analyze_rfm_segments: { icon: "👥", label: "顧客RFM分析", category: "顧客分析" },
  analyze_inventory: { icon: "📦", label: "在庫分析", category: "在庫分析" },
  analyze_seasonal_trends: { icon: "🗓️", label: "季節トレンド分析", category: "売上分析" },
  analyze_regional_performance: { icon: "🗺️", label: "地域分析", category: "売上分析" },
};
