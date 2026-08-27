import React from "react";

export default class RuntimeErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    if (typeof console !== "undefined") {
      console.error("Sera UI render error", {
        error,
        componentStack: info?.componentStack,
        scope: this.props.scope || "unknown"
      });
    }
  }

  componentDidUpdate(previousProps) {
    if (this.state.error && previousProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  reset = () => {
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;
    const title = this.props.title || "This view could not be rendered.";
    const message = this.state.error?.message || "Unknown render error";
    return (
      <section className="panel runtime-error-panel" data-testid="runtime-error-boundary">
        <div className="panel-heading">
          <h2>{title}</h2>
          <span>render error</span>
        </div>
        <p>
          A UI component failed while rendering this generated result. The app shell is still running, so you can change
          tabs, generate again, or inspect the error below.
        </p>
        <code>{message}</code>
        <button className="secondary-action" onClick={this.reset} type="button">
          Retry this view
        </button>
      </section>
    );
  }
}
