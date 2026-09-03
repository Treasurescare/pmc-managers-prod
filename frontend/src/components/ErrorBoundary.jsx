import { Component } from "react";

/**
 * ErrorBoundary — catches unhandled render errors so a single panel-level
 * bug (Bug 28/39/52/57/58) never blanks the app or logs the user out.
 * Shows a soft fallback with "Reload" button; preserves auth cookies.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("[PMC ErrorBoundary]", error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    const msg = this.state.error?.message || "Something went wrong";
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-brand-pale"
           data-testid="error-boundary">
        <div className="max-w-lg w-full border border-red-200 bg-white p-8">
          <div className="pmc-label text-red-700">Something crashed on this screen</div>
          <h2 className="font-display text-2xl text-brand-navy mt-2">
            Your session is still active
          </h2>
          <p className="text-sm text-brand-navy/70 mt-3">
            The panel encountered an error but your login is preserved. Click
            reload to return to the dashboard — no data was lost.
          </p>
          <details className="mt-4 text-xs text-brand-navy/50 font-mono">
            <summary className="cursor-pointer">Show technical details</summary>
            <div className="mt-2 bg-slate-50 p-3 whitespace-pre-wrap break-words">
              {msg}
            </div>
          </details>
          <div className="mt-6 flex gap-2">
            <button
              onClick={() => window.location.assign(window.location.pathname)}
              data-testid="error-boundary-reload"
              className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white">
              Reload panel
            </button>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              data-testid="error-boundary-retry"
              className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5">
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }
}
