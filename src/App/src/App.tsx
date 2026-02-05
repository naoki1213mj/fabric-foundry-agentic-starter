import {
    Avatar,
    Body2,
    FluentProvider,
    Subtitle2,
    webDarkTheme,
    webLightTheme
} from "@fluentui/react-components";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import "./App.css";
import Chat from "./components/Chat/Chat";
import { ChatHistoryPanel } from "./components/ChatHistoryPanel/ChatHistoryPanel";
import CitationPanel from "./components/CitationPanel/CitationPanel";
import CustomSpinner from "./components/CustomSpinner/CustomSpinner";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { AppLogo } from "./components/Svg/Svg";
import { changeLanguage, getCurrentLanguage } from "./i18n";
import { fetchUserInfo, setSelectedConversationId, startNewConversation } from "./store/appSlice";
import {
    deleteAllConversations,
    fetchChatHistory,
    fetchConversationMessages,
} from "./store/chatHistorySlice";
import { clearChat, setMessages } from "./store/chatSlice";
import { clearCitation } from "./store/citationSlice";
import { useAppDispatch, useAppSelector } from "./store/hooks";

// Preload Chart.js for faster chart rendering (non-blocking)
import("chart.js").catch(() => { /* ignore preload errors */ });

// Application version for display
const APP_VERSION = "2.7.0";
// Build info (reserved for future use)
// const BUILD_DATE = "2026-02-03";
// const BUILD_INFO = "Modern UI/UX refresh with dark mode";

// Theme icons
const SunIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
);

const MoonIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);

const panels = {
  CHAT: "CHAT",
  CHATHISTORY: "CHATHISTORY",
};

const defaultSingleColumnConfig: Record<string, number> = {
  [panels.CHAT]: 100,
  [panels.CHATHISTORY]: 30,
};

const defaultPanelShowStates = {
  [panels.CHAT]: true,
  [panels.CHATHISTORY]: false,
};

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const { appConfig } = useAppSelector((state) => state.app.config);
  const showAppSpinner = useAppSelector((state) => state.app.showAppSpinner);
  const citation = useAppSelector((state) => state.citation);

  // Dark mode state
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Language state
  const [currentLang, setCurrentLang] = useState<"ja" | "en">(() => {
    return getCurrentLanguage() as "ja" | "en";
  });

  const [panelShowStates, setPanelShowStates] = useState<
    Record<string, boolean>
  >({ ...defaultPanelShowStates });
  const [panelWidths, setPanelWidths] = useState<Record<string, number>>({
    ...defaultSingleColumnConfig,
  });
  const [showClearAllConfirmationDialog, setChowClearAllConfirmationDialog] =
    useState(false);
  const [clearing, setClearing] = React.useState(false);
  const [clearingError, setClearingError] = React.useState(false);
  const [isInitialAPItriggered, setIsInitialAPItriggered] = useState(false);
  const [offset, setOffset] = useState<number>(0);
  const OFFSET_INCREMENT = 25;
  const [hasMoreRecords, setHasMoreRecords] = useState<boolean>(true);
  const [name, setName] = useState<string>("");
  const isInitialFetchStarted = useRef(false);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(prev => !prev);
  };

  const toggleLanguage = () => {
    const newLang = currentLang === "ja" ? "en" : "ja";
    changeLanguage(newLang);
    setCurrentLang(newLang);
  };

  useEffect(() => {
    dispatch(fetchUserInfo())
      .unwrap()
      .then((res) => {
        const displayName: string =
          res[0]?.user_claims?.find((claim: any) => claim.typ === "name")?.val ?? "";
        setName(displayName);
      })
      .catch(() => {
        // Error fetching user info - silent fail
      });
  }, [dispatch]);

  const updateLayoutWidths = useCallback((newState: Record<string, boolean>) => {
    const noOfWidgetsOpen = Object.values(newState).filter((val) => val).length;
    if (appConfig === null) {
      return;
    }

    if (
      noOfWidgetsOpen === 1 ||
      (noOfWidgetsOpen === 2 && !newState[panels.CHAT])
    ) {
      setPanelWidths(defaultSingleColumnConfig);
    } else if (noOfWidgetsOpen === 2 && newState[panels.CHAT]) {
      const panelsInOpenState = Object.keys(newState).filter(
        (key) => newState[key]
      );
      const twoColLayouts = Object.keys(appConfig.TWO_COLUMN) as string[];
      for (let i = 0; i < twoColLayouts.length; i++) {
        const key = twoColLayouts[i] as string;
        const panelNames = key.split("_");
        const isMatched = panelsInOpenState.every((val) =>
          panelNames.includes(val)
        );
        const TWO_COLUMN = appConfig.TWO_COLUMN as Record<
          string,
          Record<string, number>
        >;
        if (isMatched) {
          setPanelWidths({ ...TWO_COLUMN[key] });
          break;
        }
      }
    }
  }, [appConfig]);

  useEffect(() => {
    updateLayoutWidths(panelShowStates);
  }, [appConfig, panelShowStates, updateLayoutWidths]);

  const onHandlePanelStates = (panelName: string) => {
    dispatch(clearCitation());
    const newState = {
      ...panelShowStates,
      [panelName]: !panelShowStates[panelName],
    };
    updateLayoutWidths(newState);
    setPanelShowStates(newState);
  };

  const getHistoryListData = useCallback(async () => {
    if (!hasMoreRecords) {
      return;
    }
    isInitialFetchStarted.current = true;
    const result = await dispatch(fetchChatHistory(offset));
    if (result.payload) {
      const payload = result.payload as { conversations: any[] | null; offset: number };
      const conversations = payload.conversations;
      if (conversations && conversations.length === OFFSET_INCREMENT) {
        setOffset((offset) => (offset += OFFSET_INCREMENT));
        // Stopping offset increment if there were no records
      } else if (conversations && conversations.length < OFFSET_INCREMENT) {
        setHasMoreRecords(false);
      }
    }
  }, [dispatch, hasMoreRecords, offset, OFFSET_INCREMENT]);

  const onClearAllChatHistory = async () => {
    setChowClearAllConfirmationDialog(false);
    dispatch(clearCitation());
    setClearing(true);
    try {
      await dispatch(deleteAllConversations()).unwrap();

      dispatch(startNewConversation());
      dispatch(clearChat());
      setOffset(0);
      setHasMoreRecords(true);
    } catch {
      setClearingError(true);
    }
    setClearing(false);
  };

  useEffect(() => {
    setIsInitialAPItriggered(true);
  }, []);

  useEffect(() => {
    if (isInitialAPItriggered && !isInitialFetchStarted.current) {
      getHistoryListData();
    }
  }, [getHistoryListData, isInitialAPItriggered]);

  const onSelectConversation = async (id: string) => {
    if (!id) return;
    dispatch(setSelectedConversationId(id));

    try {
      const result = await dispatch(fetchConversationMessages(id)).unwrap();
      if (result && result.messages) {
        dispatch(setMessages(result.messages));
      }
    } catch {
      // Error fetching conversation messages
    }
  };

  const onClickClearAllOption = () => {
    setChowClearAllConfirmationDialog((prevFlag) => !prevFlag);
  };

  const onHideClearAllDialog = () => {
    setChowClearAllConfirmationDialog((prevFlag) => !prevFlag);
    setTimeout(() => {
      setClearingError(false);
    }, 1000);
  };

  return (
    <FluentProvider
      theme={isDarkMode ? webDarkTheme : webLightTheme}
      style={{ height: "100%", backgroundColor: "var(--color-bg-primary)" }}
    >
      <CustomSpinner loading={showAppSpinner} label={t("loading.pleaseWait")} />
      <div className="header">
        <div className="header-left-section">
          <AppLogo />
          <Subtitle2 className="header-title">
            {t("header.title")} <Body2 style={{ gap: "10px" }}>| {t("header.subtitle")}</Body2>
          </Subtitle2>
        </div>
        <div className="header-right-section">
          <span className="version-badge">
            v{APP_VERSION}
          </span>
          <button
            className="lang-toggle-btn"
            onClick={toggleLanguage}
            title={currentLang === "ja" ? "Switch to English" : "日本語に切替"}
            aria-label={currentLang === "ja" ? "Switch to English" : "Switch to Japanese"}
          >
            {currentLang === "ja" ? "EN" : "日本語"}
          </button>
          <button
            className="theme-toggle-btn"
            onClick={toggleTheme}
            title={isDarkMode ? t("theme.switchToLight") || "ライトモードに切替" : t("theme.switchToDark") || "ダークモードに切替"}
            aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
          >
            {isDarkMode ? <SunIcon /> : <MoonIcon />}
          </button>
          <div>
            <Avatar name={name} title={name} />
          </div>
        </div>
      </div>
      <ErrorBoundary>
        <div className="main-container">
          {/* LEFT PANEL:  CHAT */}
          {panelShowStates?.[panels.CHAT] && (
            <div
              style={{
                width: `${panelWidths[panels.CHAT]}%`,
            }}
          >
            <Chat
              onHandlePanelStates={onHandlePanelStates}
              panels={panels}
              panelShowStates={panelShowStates}
            />
          </div>
        )}
        {citation.showCitation && citation.currentConversationIdForCitation !== "" && (
          <div
            style={{
              // width: `${panelWidths[panels.DASHBOARD]}%`,
              width: `${panelWidths[panels.CHATHISTORY] || 17}%`,
              // minWidth: '30%'
            }}
          >
            <CitationPanel activeCitation={citation.activeCitation}  />

          </div>
        )}
        {/* RIGHT PANEL: CHAT HISTORY */}
        {panelShowStates?.[panels.CHAT] &&
          panelShowStates?.[panels.CHATHISTORY] && (
            <div
              style={{
                width: `${panelWidths[panels.CHATHISTORY]}%`,
              }}
            >
              <ChatHistoryPanel
                clearing={clearing}
                clearingError={clearingError}
                handleFetchHistory={() => getHistoryListData()}
                onClearAllChatHistory={onClearAllChatHistory}
                onClickClearAllOption={onClickClearAllOption}
                onHideClearAllDialog={onHideClearAllDialog}
                onSelectConversation={onSelectConversation}
                showClearAllConfirmationDialog={showClearAllConfirmationDialog}
              />
              {/* {useAppContext?.state.isChatHistoryOpen &&
            useAppContext?.state.isCosmosDBAvailable?.status !== CosmosDBStatus.NotConfigured && <ChatHistoryPanel />} */}
            </div>
          )}
        </div>
      </ErrorBoundary>
    </FluentProvider>
  );
};

export default Dashboard;

// Build trigger: 2026-02-03 UI/UX Modernization
