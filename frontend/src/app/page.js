import Link from "next/link";
import Image from "next/image";

const steps = [
  { config: "stripe · refund.created", kind: "WEBHOOK", icon: "↗", title: "Refund request", key: "request" },
  { config: "GET /v1/customers/{id}", kind: "HTTP REQUEST", icon: "⌘", title: "Get customer & order data", key: "data" },
  { config: "relay reasoning · policy v3", kind: "AI DECISION", icon: "✳", title: "Review refund", key: "ai" },
  { config: "amount ≤ $500.00", kind: "IF / ELSE", icon: "≤", title: "Check refund limit", key: "condition" },
  { config: "stripe · acct_•••8421", kind: "PAYMENT ACTION", icon: "$", title: "Issue refund", key: "payment" },
  { config: "refund receipt · email", kind: "NOTIFICATION", icon: "↗", title: "Send confirmation", key: "email" },
];

function DemoStatus({ step }) {
  return <span className={`demo-status status-${step}`} aria-hidden="true" />;
}

function RefundDemo() {
  return (
    <div className="refund-demo" aria-label="An animated six-step automatic refund workflow, alternating between two fictional customer refunds">
      <div className="demo-heading"><span><i /> LIVE WORKFLOW <b>/</b> E-COMMERCE REFUNDS</span><span className="demo-scenario demo-john">RUN 01 <i>·</i> JOHN ANDERSON</span><span className="demo-scenario demo-sarah">RUN 02 <i>·</i> SARAH MITCHELL</span></div>
      <div className="workflow-rail">
        {steps.map((step, index) => (
          <div className="workflow-slot" key={step.key}>
            <article className={`workflow-card workflow-${step.key}`}>
              <div className="workflow-top"><span className={`step-icon step-icon-${step.key}`}>{step.icon}</span><span className="node-config-label">{step.config}</span><DemoStatus step={step.key} /></div>
              <small>{step.kind}</small>
              <h2>{step.title}{step.key === "ai" && <b className="confidence">97%</b>}</h2>
              {step.key === "request" && <><p>Event payload · <span className="payload-state">verified</span></p><div className="workflow-detail"><span className="john-order">ORD-18492</span><span className="sarah-order">ORD-19384</span><b className="john-name">John Anderson</b><b className="sarah-name">Sarah Mitchell</b><strong className="john-amount">$249.00</strong><strong className="sarah-amount">$89.00</strong></div></>}
              {step.key === "data" && <><p className="data-fetching">Fetching customer context…</p><p className="data-found">✓ Customer · order · payment found</p><div className="workflow-detail data-summary"><span className="john-summary">John Anderson · ORD-18492</span><span className="sarah-summary">Sarah Mitchell · ORD-19384</span><b>Order total</b><strong className="john-amount">$249.00</strong><strong className="sarah-amount">$89.00</strong><b>Previous refunds</b><strong>1</strong></div></>}
              {step.key === "ai" && <><p className="ai-evaluating">Comparing request with policy…</p><p className="ai-approved">✓ Refund approved</p><div className="workflow-detail ai-inputs"><span>Inputs</span><b>Order</b><b>History</b><b>Policy</b><strong>97%</strong></div></>}
              {step.key === "condition" && <><p><strong className="john-amount">$249.00</strong><strong className="sarah-amount">$89.00</strong> <span>≤ $500</span></p><div className="workflow-detail eligible"><i>✓</i> Eligible for automatic refund</div></>}
              {step.key === "payment" && <><p className="payment-processing">Creating Stripe refund…</p><p className="payment-processed">✓ Refund processed</p><div className="workflow-detail refund-done"><i>✓</i><strong className="john-amount">$249 refunded</strong><strong className="sarah-amount">$89 refunded</strong><span>Idempotency · ref_18492</span></div></>}
              {step.key === "email" && <><p className="email-generating">Preparing receipt for customer…</p><p className="email-sent">✓ Email sent</p><div className="workflow-detail email-preview"><span className="john-amount">john.a@example.com</span><span className="sarah-amount">sarah.m@example.com</span><b>Template · refund receipt</b></div></>}
            </article>
            {index < steps.length - 1 && <div className={`workflow-edge edge-${index + 1}`}><span /></div>}
          </div>
        ))}
      </div>
      <div className="workflow-complete"><span>✓</span><strong>Workflow completed</strong><i /><span className="john-amount">Refund: $249.00</span><span className="sarah-amount">Refund: $89.00</span><i /><span>6 steps</span><i /><span>4.2s</span></div>
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="relay-home">
      <header className="home-nav">
        <div className="home-nav-inner">
          <Link href="/" className="home-logo" aria-label="Relay home"><Image src="/brand/relay/relay-light.png" alt="Relay" width={132} height={53} priority /></Link>
          <nav aria-label="Main navigation"><a href="#workflow">Product</a><a href="#how-it-works">How it works</a></nav>
          <div className="home-nav-actions"><Link className="nav-signin" href="/login">Sign in</Link><Link className="home-cta nav-cta" href="/register">Start building <span>↗</span></Link></div>
        </div>
      </header>
      <section className="home-hero">
        <div className="hero-message">
          <div className="hero-main-copy"><p className="home-eyebrow"><i /> AI-POWERED WORKFLOW AUTOMATION</p><h1>Connect tools.<br /><span>Let AI do the work.</span></h1></div>
          <div className="hero-side-copy"><p>Relay brings your apps and data together, understands the context, and completes the work automatically.</p><div className="hero-cta-row"><Link className="home-cta" href="/register">Start building <span>↗</span></Link><a href="#workflow">Explore the workflow <span>↓</span></a></div></div>
        </div>
        <div className="hero-divider"><span>FROM REQUEST TO RESOLUTION</span><span>ONE CONNECTED WORKFLOW <i>✳</i></span></div>
        <div id="workflow"><RefundDemo /></div>
        <div className="hero-caption"><span><i /> Built for work that needs context</span><span>TRIGGER <b>→</b> DATA <b>→</b> AI <b>→</b> ACTION</span></div>
      </section>
      <section className="home-followup" id="how-it-works"><p className="home-eyebrow">AUTOMATION WITH CONTEXT</p><h2>Workflows that understand,<br />decide, and act.</h2><p>Traditional automation moves data between systems. Relay gives workflows the context to choose the right action and carry it through.</p><Link href="/register" className="home-cta">Build your first workflow <span>↗</span></Link></section>
      <footer className="home-footer"><Link href="/" className="home-logo"><Image src="/brand/relay/relay-light.png" alt="Relay" width={110} height={44} /></Link><span>AI-powered workflow automation.</span><small>© 2026 Relay</small></footer>
    </main>
  );
}
