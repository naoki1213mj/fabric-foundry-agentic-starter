import { memo, useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchCitationContent } from '../../store/citationSlice';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { AskResponse, Citation } from '../../types/AppTypes';
import { parseAnswer } from './AnswerParser';
import "./Citations.css";

interface Props {
    answer: AskResponse;
    onSpeak?: any;
    isActive?: boolean;
    index: number;
}

const Citations = memo(({ answer, index }: Props) => {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const selectedConversationId = useAppSelector((state) => state.app.selectedConversationId);
    const parsedAnswer = useMemo(() => parseAnswer(answer), [answer]);
    const [isExpanded, setIsExpanded] = useState(false);

    const createCitationFilepath = (
        citation: Citation,
        index: number,
        truncate: boolean = false
    ) => {
        let citationFilename = "";
            citationFilename =  citation.title ? (citation.title ?? `Citation ${index}`) : `Citation ${index}`;
        return citationFilename;
    };

    const onCitationClicked = useCallback(async (
        citation: Citation,
        e: React.MouseEvent | React.KeyboardEvent
    ) => {
        // If citation has a URL, open it directly in a new tab
        if (citation.url) {
            e.preventDefault();
            window.open(citation.url, '_blank', 'noopener,noreferrer');
            return;
        }
        // Otherwise, fetch content via Redux (legacy behavior)
        dispatch(fetchCitationContent({ citation, conversationId: selectedConversationId }));
    }, [dispatch, selectedConversationId]);

    const toggleExpanded = useCallback(() => {
        setIsExpanded(prev => !prev);
    }, []);

    // Don't render if no citations
    if (!parsedAnswer.citations || parsedAnswer.citations.length === 0) {
        return null;
    }

    // Deduplicate citations by URL or filepath
    const seenUrls = new Set<string>();
    const uniqueCitations = parsedAnswer.citations.filter(citation => {
        const key = citation.url || citation.filepath || citation.title || '';
        if (!key || seenUrls.has(key)) {
            return false;
        }
        seenUrls.add(key);
        return true;
    });

    const citationCount = uniqueCitations.length;

    return (
        <div className="citations-wrapper">
            <button
                className="citations-toggle"
                onClick={toggleExpanded}
                aria-expanded={isExpanded}
                aria-controls={`citations-list-${index}`}
            >
                <span className="citations-toggle-icon">
                    {isExpanded ? '▼' : '▶'}
                </span>
                <span className="citations-toggle-text">
                    {t("citations.references", { count: citationCount }) || `参考リンク (${citationCount}件)`}
                </span>
            </button>

            {isExpanded && (
                <div
                    id={`citations-list-${index}`}
                    className="citations-list"
                >
                    {uniqueCitations.map((citation, idx) => {
                        const displayIdx = idx + 1;
                        const hasUrl = !!citation.url;

                        return hasUrl ? (
                            // Web search results with URL - render as direct link
                            <a
                                key={idx}
                                href={citation.url || '#'}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="citationContainer citationLink"
                                title={citation.url || createCitationFilepath(citation, displayIdx)}
                            >
                                <div className="citation">
                                    {displayIdx}
                                </div>
                                <span className="citation-title">
                                    {createCitationFilepath(citation, displayIdx, true)}
                                </span>
                                <span className="citation-external-icon">↗</span>
                            </a>
                        ) : (
                            // Document citations without URL - use click handler
                            <span
                                role="button"
                                onKeyDown={(e) =>
                                    e.key === " " || e.key === "Enter"
                                        ? onCitationClicked(citation, e)
                                        : undefined
                                }
                                tabIndex={0}
                                title={createCitationFilepath(citation, displayIdx)}
                                key={idx}
                                onClick={(e) => onCitationClicked(citation, e)}
                                className="citationContainer"
                            >
                                <div className="citation">
                                    {displayIdx}
                                </div>
                                <span className="citation-title">
                                    {createCitationFilepath(citation, displayIdx, true)}
                                </span>
                            </span>
                        );
                    })}
                </div>
            )}
        </div>
    );
});

Citations.displayName = 'Citations';

export default Citations;
