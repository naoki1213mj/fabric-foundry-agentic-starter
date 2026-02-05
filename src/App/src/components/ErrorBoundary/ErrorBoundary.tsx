import { Body1, Button, Title1 } from "@fluentui/react-components";
import { Component, type ErrorInfo, type ReactNode } from "react";
import "./ErrorBoundary.css";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="error-boundary-container">
          <div className="error-boundary-content">
            <Title1 className="error-boundary-title">⚠️ エラーが発生しました</Title1>
            <Body1 className="error-boundary-message">
              予期しないエラーが発生しました。ページを再読み込みしてください。
            </Body1>
            {this.state.error && (
              <pre className="error-boundary-details">
                {this.state.error.message}
              </pre>
            )}
            <div className="error-boundary-actions">
              <Button appearance="primary" onClick={this.handleReload}>
                ページを再読み込み
              </Button>
              <Button appearance="secondary" onClick={this.handleReset}>
                再試行
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
