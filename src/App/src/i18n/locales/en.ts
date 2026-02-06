export const en = {
  translation: {
    // Header
    header: {
      title: "Contoso",
      subtitle: "Unified Data Analysis Agents",
      settings: "Settings",
      help: "Help",
      logout: "Logout",
      version: "v2.1.0",
      buildDate: "Jan 16, 2026",
    },

    // Chat
    chat: {
      title: "Chat",
      placeholder: "Ask a question...",
      send: "Send",
      stop: "Stop",
      newChat: "New Chat",
      clearHistory: "Clear History",
      clearAll: "Clear All",
      thinking: "Thinking...",
      generating: "Generating answer",
      generatingChart: "Generating chart if possible with the provided data",
      typing: "Typing...",
      showHistory: "Show Chat History",
      hideHistory: "Hide Chat History",
      startChatting: "Start Chatting",
      landingText: "You can ask questions around sales, products and orders.",
      searchPlaceholder: "Search in conversation…",
      clearSearch: "Clear",
      noSearchResultsTitle: "No results",
      noSearchResultsBody: "No messages matched \"{{query}}\".",
      editMessage: "Edit",
      resendMessage: "Resend",
      exportMarkdown: "Export Markdown",
      exportJson: "Export JSON",
      sendQuestion: "Send Question",
      processing: "Processing...",
      processingDetails: "Processing Details",
      reasoning: "Reasoning",
      toolCount: "Tools: {{count}}",
      stopGenerating: "Stop Generating",
    },

    // Agent
    agent: {
      selectTitle: "Select an Agent",
      selectDescription: "Choose an agent to start the conversation",
      salesAnalyst: "Sales Analyst Agent",
      salesAnalystDesc: "Provides sales data analysis and insights",
      capabilities: "Capabilities",
      tools: "Available Tools",
    },

    // Agent Mode
    agentMode: {
      label: "Agent Mode",
      sqlOnly: "Fast, SQL queries only",
      multiTool: "All tools, balanced",
      handoff: "Expert agent delegation",
      magentic: "Complex planning, manager",
    },

    // Doc Search
    docSearch: {
      label: "Doc Search Reasoning (Foundry IQ)",
      minimal: "Fast, direct search (no LLM)",
      low: "Single pass, balanced",
      medium: "Iterative search, best quality",
    },

    // Model Settings
    modelSettings: {
      label: "AI Model",
      gpt5Desc: "High accuracy, reasoning",
      gpt4oMiniDesc: "Fast, cost effective",
      temperatureLabel: "Creativity (0=precise, 2=creative)",
      reasoningLabel: "GPT-5 reasoning depth",
      reasoningLow: "Fast, simple reasoning",
      reasoningMedium: "Balanced",
      reasoningHigh: "Deep reasoning, best quality",
      summaryLabel: "GPT-5 thinking display",
      summaryOff: "Hide thinking",
      summaryAuto: "Auto",
      summaryConcise: "Concise",
      summaryDetailed: "Detailed",
      thinkingDisplay: "Thinking Display",
    },

    // Chat History
    history: {
      title: "Chat history",
      today: "Today",
      yesterday: "Yesterday",
      last7Days: "Last 7 days",
      older: "Older",
      noHistory: "No chat history.",
      deleteConfirm: "Delete this conversation?",
      clearAllConfirm: "Are you sure you want to clear all chat history?",
      clearAllSubtext: "All chat history will be permanently removed.",
      clearAllError: "Error deleting all of chat history",
      clearAllErrorSubtext: "Please try again. If the problem persists, please contact the site administrator.",
      clearing: "Clearing chat history...",
      loading: "Loading chat history",
      loadingMore: "loading more chat history",
    },

    // Loading
    loading: {
      default: "Loading...",
      pleaseWait: "Please wait.....!",
      agents: "Loading agents...",
      history: "Loading history...",
      sending: "Sending...",
      fetchingMessages: "Fetching Chat messages",
    },

    // Error
    error: {
      default: "An error occurred",
      network: "Network error occurred",
      timeout: "Request timed out",
      unauthorized: "Authentication required",
      forbidden: "Access denied",
      notFound: "Resource not found",
      serverError: "Server error occurred",
      retry: "Retry",
      dismiss: "Dismiss",
      tryAgain: "Please try again",
      tryAgainLater: "An error occurred. Please try again later.",
      contactAdmin: "If the problem persists, please contact the site administrator.",
      chartGeneration: "Chart can't be generated, please try again.",
      chartDisplay: "Sorry, we couldn't display the chart for this response.",
    },

    // Settings
    settings: {
      title: "Settings",
      language: "Language",
      theme: "Theme",
      themeLight: "Light",
      themeDark: "Dark",
      themeSystem: "System",
      save: "Save",
      cancel: "Cancel",
    },

    // Common
    common: {
      confirm: "Confirm",
      cancel: "Cancel",
      save: "Save",
      delete: "Delete",
      edit: "Edit",
      close: "Close",
      yes: "Yes",
      no: "No",
      ok: "OK",
      back: "Back",
      next: "Next",
      submit: "Submit",
      reset: "Reset",
      clearAll: "Clear All",
      recommended: "Recommended",
    },

    // Date Format
    date: {
      format: "MM/DD/YYYY",
      timeFormat: "HH:mm",
      dateTimeFormat: "MM/DD/YYYY HH:mm",
    },

    // SQL Results
    sql: {
      results: "Query Results",
      rowCount: "{{count}} records",
      noResults: "No results",
      exportCsv: "Export CSV",
    },

    // Message
    message: {
      aiDisclaimer: "AI-generated content may be incorrect",
      noDataAvailable: "No Data Available",
      copy: "Copy",
      copied: "Copied",
    },

    // Reaction
    reaction: {
      helpful: "Helpful",
      notHelpful: "Not helpful",
      thanks: "Thanks for your feedback",
    },

    // Keyboard shortcuts
    shortcuts: {
      send: "Send (Enter)",
      newChat: "New Chat (Ctrl+K)",
      stop: "Stop (Esc)",
    },

    // Citation
    citation: {
      references: "References",
      source: "Source",
    },

    // Citations (toggle)
    citations: {
      references: "References ({{count}})",
      showReferences: "Show references",
      hideReferences: "Hide references",
    },

    // Suggested Questions
    suggestions: {
      title: "Try asking",
      salesAnalysis: "Show top 10 products",
      customerInsights: "Customer segment analysis",
      trendAnalysis: "Analyze sales trends",
      productSpecs: "Search product specs",
    },

    // Model Selection
    model: {
      title: "Model",
      gpt5: "GPT-5 (High Quality)",
      gpt4oMini: "GPT-4o-mini (Fast)",
      temperature: "Creativity",
      reasoningEffort: "Reasoning Effort",
    },
  },
};
