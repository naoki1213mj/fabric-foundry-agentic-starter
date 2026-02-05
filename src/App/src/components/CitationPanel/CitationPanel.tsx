import { Stack } from '@fluentui/react';
import { DismissRegular } from '@fluentui/react-icons';
import { memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from "rehype-raw";
import remarkGfm from "remark-gfm";
import { clearCitation } from '../../store/citationSlice';
import { useAppDispatch } from '../../store/hooks';
import "./CitationPanel.css";
interface Props {
    activeCitation: any
}

const CitationPanel = memo(({ activeCitation }: Props) => {
    const dispatch = useAppDispatch();

    // Custom link component to open external links in new tab
    const markdownComponents = useMemo(() => ({
      a: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
        <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
          {children}
        </a>
      ),
    }), []);

    const onCloseCitation = () => {
        dispatch(clearCitation());
    }
    return (
        <div className='citationPanel'>

            <Stack.Item

            >
                <Stack
                    horizontal
                    horizontalAlign="space-between"
                    verticalAlign="center"
                >
                    <div
                        role="heading"
                        aria-level={2}
                        style={{
                            fontWeight: "600",
                            fontSize: '16px'
                        }}
                        >

                    Citations
                    </div>
                    <DismissRegular
                        role="button"
                        onKeyDown={(e) =>
                            e.key === " " || e.key === "Enter"
                                ? onCloseCitation()
                                : () => { }
                        }
                        tabIndex={0}
                        onClick={onCloseCitation}
                    />
                </Stack>
                <h5

                >
                    {activeCitation.title}
                </h5>

                <ReactMarkdown
                children={activeCitation?.content}
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={markdownComponents}
              />
            </Stack.Item>
        </div>)
});

CitationPanel.displayName = 'CitationPanel';

export default CitationPanel;
