"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import s from "./LandingPage.module.css";

function Icon({ name = "arrow", size = 20, ...props }) {
  const paths = {
    arrow: (
      <>
        <path d="M5 12h14M13 6l6 6-6 6" />
      </>
    ),
    bolt: <path d="m13 2-9 12h7l-1 8 10-12h-7l1-8Z" />,
    flow: (
      <>
        <rect x="3" y="3" width="6" height="6" rx="2" />
        <rect x="15" y="15" width="6" height="6" rx="2" />
        <path d="M6 9v6a3 3 0 0 0 3 3h6M15 6h6m-3-3v6" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z" />
        <path d="M20 2v4m-2-2h4" />
      </>
    ),
    book: (
      <>
        <path d="M12 5v16M12 5C8 2 3 3 3 3v16s5-1 9 2c4-3 9-2 9-2V3s-5-1-9 2Z" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    shield: (
      <>
        <path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    mail: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="3" />
        <path d="m3 6 9 7 9-7" />
      </>
    ),
    play: <path d="m9 5 11 7-11 7V5Z" />,
    pause: (
      <>
        <path d="M9 5v14M15 5v14" />
      </>
    ),
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    globe: (
      <>
        <circle cx="12" cy="12" r="9" />
        <ellipse cx="12" cy="12" rx="4" ry="9" />
        <path d="M3 12h18" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] || paths.arrow}
    </svg>
  );
}

function WorkflowMotion() {
  const motion = useRef(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setVisible(entry.isIntersecting);
      },
      { threshold: 0.35 },
    );
    observer.observe(motion.current);
    return () => observer.disconnect();
  }, []);
  return (
    <div
      ref={motion}
      className={`${s.workflowMotion} ${visible ? s.motionVisible : ""}`}
      tabIndex={0}
      role="region"
      aria-label="Workflow animation: receive a request, retrieve knowledge, decide, and complete the work. Focus or hover to pause."
    >
      <div className={s.motionHeading}>
        <span>A SMALL REQUEST. A COMPLETE WORKFLOW.</span>
        <span>RELAY IN MOTION</span>
      </div>
      <div className={s.motionEditorial}>
        <div className={s.requestSlip}>
          <span className={s.slipIcon}>
            <Icon name="bolt" size={19} />
          </span>
          <div>
            <small>INCOMING REQUEST</small>
            <p>“Can I return my order?”</p>
          </div>
          <span className={s.slipArrow} aria-hidden="true">
            ↗
          </span>
        </div>
        <div className={s.wordSequence} aria-hidden="true">
          <span>Understand.</span>
          <span>Decide.</span>
          <span>Done.</span>
          <i />
        </div>
      </div>
      <div className={s.motionLedger}>
        <div className={s.ledgerStatus}>
          <span className={s.ledgerDot} />
          <div>
            <span>Reading your request</span>
            <span>Finding the right policy</span>
            <span>Choosing the next action</span>
            <span>Work completed</span>
          </div>
        </div>
        <span className={s.ledgerNote}>Your knowledge. Your rules.</span>
        <div className={s.ledgerCounter} aria-hidden="true">
          <span>01 / 04</span>
          <span>02 / 04</span>
          <span>03 / 04</span>
          <span>04 / 04</span>
        </div>
      </div>
    </div>
  );
}

const connectedTools = [
  { name: "OpenAI", image: "/brand/openai.svg" },
  { name: "Claude", image: "/brand/claude.svg" },
  { name: "Gemini", image: "/brand/gemini.svg" },
  { name: "Gmail", image: "/brand/gmail.png" },
  { name: "Stripe", image: "/brand/stripe.svg", wordmark: true },
  { name: "HTTP APIs", icon: "globe" },
  { name: "Webhooks", icon: "bolt" },
];

function ToolStrip() {
  return (
    <section className={s.connections} id="connections">
      <div className={s.stripHeading}>
        <p>WORKS WITH YOUR TOOLS</p>
      </div>
      <div
        className={s.toolsViewport}
        tabIndex={0}
        role="region"
        aria-label="Connected tools. Focus or hover to pause scrolling."
      >
        <div className={s.toolsTrack}>
          {[0, 1].map((copy) => (
            <div
              className={s.toolsGroup}
              key={copy}
              aria-hidden={copy === 1 ? true : undefined}
            >
              {connectedTools.map((tool) => (
                <div className={s.toolItem} key={tool.name}>
                  {tool.image ? (
                    <Image
                      loading="eager"
                      className={tool.wordmark ? s.stripeWordmark : undefined}
                      src={tool.image}
                      alt={tool.wordmark ? tool.name : ""}
                      width={tool.wordmark ? 70 : 25}
                      height={25}
                    />
                  ) : (
                    <Icon name={tool.icon} size={24} />
                  )}
                  {!tool.wordmark && <span>{tool.name}</span>}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function KnowledgeSection() {
  return (
    <section className={s.knowledge} id="how-it-works">
      <div className={s.knowledgeCopy}>
        <span className={s.kicker}>YOUR KNOWLEDGE, CONNECTED.</span>
        <h2>
          The right context.
          <br />
          <span>The next step.</span>
        </h2>
        <p>
          Relay uses RAG to find relevant passages in your documents and give AI
          the context to decide.
        </p>
        <ul>
          <li>
            <span>01</span> Add your documents
          </li>
          <li>
            <span>02</span> Retrieve relevant knowledge
          </li>
          <li>
            <span>03</span> Decide, approve, and act
          </li>
        </ul>
      </div>
      <div className={s.knowledgeExample}>
        <div className={s.exampleHeader}>
          <Icon name="book" size={16} />
          <span>Knowledge in action</span>
          <small>EXAMPLE</small>
        </div>
        <p className={s.question}>“Can I return an order from 12 days ago?”</p>
        <blockquote>
          Orders are eligible for a refund within 30 days of purchase.
          <cite>refund-policy.pdf · Retrieved passage</cite>
        </blockquote>
        <div className={s.exampleResult}>
          <Icon name="check" size={15} />
          <span>Relevant context, ready for the next step.</span>
        </div>
      </div>
    </section>
  );
}

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className={s.page}>
      <a href="#main" className={s.skip}>
        Skip to content
      </a>
      <header className={s.header}>
        <div className={s.navInner}>
          <Link href="/" aria-label="Relay home" className={s.logo}>
            <Image
              src="/brand/relay/relay-light.png"
              alt="Relay"
              width={114}
              height={46}
              priority
            />
          </Link>
          <nav
            className={`${s.nav} ${menuOpen ? s.navOpen : ""}`}
            aria-label="Main navigation"
          >
            <a href="#product" onClick={() => setMenuOpen(false)}>
              Product
            </a>
            <a href="#how-it-works" onClick={() => setMenuOpen(false)}>
              How it works
            </a>
            <a href="#connections" onClick={() => setMenuOpen(false)}>
              Connections
            </a>
          </nav>
          <div className={s.navActions}>
            <Link href="/login" className={s.signIn}>
              Sign in
            </Link>
            <Link href="/register" className={s.navCta}>
              Start building <Icon size={14} />
            </Link>
            <button
              className={s.menuToggle}
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <Icon name={menuOpen ? "close" : "menu"} />
            </button>
          </div>
        </div>
      </header>
      <main id="main">
        <div className={s.firstScreen}>
          <section className={s.hero}>
            <div className={s.heroStage}>
              <div>
                <span className={s.kicker}>
                  INTELLIGENT WORKFLOW AUTOMATION
                </span>
                <h1>
                  Less back and forth.
                  <br />
                  <span>More forward.</span>
                </h1>
              </div>
              <div className={s.heroCopy}>
                <p>
                  Connect your tools and knowledge.
                  <br />
                  Let Relay move the work forward.
                </p>
                <Link href="/register" className={s.primary}>
                  Start building <Icon size={16} />
                </Link>
              </div>
            </div>
            <div id="product" className={s.preview}>
              <WorkflowMotion />
            </div>
          </section>
          <ToolStrip />
        </div>
        <KnowledgeSection />
        <section className={s.finalCta}>
          <div>
            <h2>Make room for better work.</h2>
            <p>Build your first workflow with Relay.</p>
          </div>
          <Link href="/register" className={s.primary}>
            Get started <Icon size={16} />
          </Link>
        </section>
      </main>
      <footer className={s.footer}>
        <Link href="/" aria-label="Relay home">
          <Image
            src="/brand/relay/relay-light.png"
            alt="Relay"
            width={96}
            height={39}
          />
        </Link>
        <nav aria-label="Footer navigation">
          <a href="#product">Product</a>
          <a href="#how-it-works">How it works</a>
          <Link href="/login">Sign in</Link>
          <Link href="/privacy">Privacy Policy</Link>
          <Link href="/terms">Terms of Service</Link>
        </nav>
        <small>© {new Date().getFullYear()} Relay</small>
      </footer>
    </div>
  );
}
