"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import s from "./LandingPage.module.css";

const repository = "https://github.com/shaad4/relay-workflow-automation";
const cloneCommand = `git clone ${repository}.git`;
const mcpDocs = `${repository}/tree/dev/service/mcp-server`;

function Icon({ name = "arrow", size = 20, ...props }) {
  const paths = {
    arrow: <path d="M5 12h14m-6-6 6 6-6 6" />,
    external: <path d="M7 17 17 7M7 7h10v10" />,
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
      <path d="M12 5v16M12 5C8 2 3 3 3 3v16s5-1 9 2c4-3 9-2 9-2V3s-5-1-9 2Z" />
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
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    menu: <path d="M4 7h16M4 12h16M4 17h16" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    pause: <path d="M9 5v14M15 5v14" />,
    play: <path d="m9 5 11 7-11 7V5Z" />,
    globe: (
      <>
        <circle cx="12" cy="12" r="9" />
        <ellipse cx="12" cy="12" rx="4" ry="9" />
        <path d="M3 12h18" />
      </>
    ),
    code: <path d="m8 7-5 5 5 5m8-10 5 5-5 5m-3-14-2 18" />,
    copy: (
      <>
        <rect x="8" y="8" width="12" height="13" rx="2" />
        <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" />
      </>
    ),
    github: (
      <>
        <path d="M9 19c-4.3 1.3-4.3-2.5-6-3m12 6v-3.9a3.4 3.4 0 0 0-.9-2.7c3-.3 6.2-1.5 6.2-6.9a5.4 5.4 0 0 0-1.5-3.7 5 5 0 0 0-.1-3.7S17.5.7 15 2.5a13 13 0 0 0-7 0C5.5.7 4.3 1.1 4.3 1.1a5 5 0 0 0-.1 3.7 5.4 5.4 0 0 0-1.5 3.7c0 5.4 3.2 6.6 6.2 6.9a3.4 3.4 0 0 0-.9 2.7V22" />
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

function ExternalLink({ href, children, className }) {
  return (
    <a
      href={href}
      className={className}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
      <Icon name="external" size={16} />
      <span className={s.srOnly}> (opens in a new tab)</span>
    </a>
  );
}

const examples = [
  {
    name: "Customer support",
    title: "A little context. A better reply.",
    steps: [
      ["bolt", "A request arrives", "Webhook trigger", "Trigger"],
      ["book", "Find the context", "Your knowledge base", "Knowledge"],
      ["spark", "Make it useful.", "AI Generate", "AI"],
      ["mail", "A better reply", "Delivered with Gmail", "Action"],
    ],
  },
  {
    name: "Scheduled reports",
    title: "Your weekly update, connected.",
    steps: [
      ["clock", "Every Monday", "Scheduled trigger", "Trigger"],
      ["globe", "Gather the numbers", "Your HTTP API", "Data"],
      ["spark", "Find the story.", "AI Generate", "AI"],
      ["mail", "The weekly update", "Delivered with Gmail", "Action"],
    ],
  },
];

const workflowPaths = [
  "M145 190 V255 Q145 280 170 280 H181 Q206 280 206 305 V338",
  "M314 399 H340 Q370 399 370 369 V302 Q370 277 390 277",
  "M534 277 H557 Q582 277 582 252 V163 Q582 138 606 138",
];
const compactWorkflowPaths = [
  "M180 102 H192 Q204 102 204 114 V173 Q204 185 220 185",
  "M310 238 V255 Q310 270 295 270 H115 Q100 270 100 285 V294",
  "M180 364 H192 Q204 364 204 376 V446 Q204 458 220 458",
];

function WorkflowPaths({ compact = false }) {
  return (
    <svg
      className={`${s.flowPaths} ${compact ? s.compactPaths : s.widePaths}`}
      viewBox={compact ? "0 0 400 520" : "0 0 800 520"}
      preserveAspectRatio="none"
      fill="none"
      aria-hidden="true"
    >
      {(compact ? compactWorkflowPaths : workflowPaths).map((path, index) => (
        <g key={path} style={{ "--signal-delay": `${index * 1.5}s` }}>
          <path className={s.pathBase} d={path} />
          <path className={s.pathSignal} d={path} pathLength="100" />
        </g>
      ))}
    </svg>
  );
}

function WorkflowPreview() {
  const [selected, setSelected] = useState(0);
  const [motionPaused, setMotionPaused] = useState(false);
  const example = examples[selected];
  return (
    <div className={s.workflowPreview} data-motion-paused={motionPaused}>
      <div className={s.flowHeading}>
        <span className={s.flowEyebrow}>
          <span /> AN IDEA, CONNECTED.
        </span>
        <div className={s.previewControls}>
          <span className={s.exampleLabel}>WORKFLOW EXAMPLE</span>
          <button
            type="button"
            className={s.motionButton}
            onClick={() => setMotionPaused(!motionPaused)}
            aria-label={
              motionPaused
                ? "Resume workflow animation"
                : "Pause workflow animation"
            }
            aria-pressed={motionPaused}
          >
            <Icon name={motionPaused ? "play" : "pause"} size={13} />
          </button>
        </div>
      </div>
      <div className={s.flowStage} key={selected}>
        <div className={s.flowAtmosphere} aria-hidden="true" />
        <WorkflowPaths />
        <WorkflowPaths compact />
        <span
          className={`${s.pathCaption} ${s.contextCaption}`}
          aria-hidden="true"
        >
          add context
        </span>
        <span
          className={`${s.pathCaption} ${s.actionCaption}`}
          aria-hidden="true"
        >
          make a move
        </span>
        <ol className={s.flowNodes} aria-label={example.title}>
          {example.steps.map(([icon, title, detail, type], index) => (
            <li
              key={title}
              className={`${s.flowNode} ${s[`flowNode${index}`]}`}
              style={{ "--step-delay": `${index * 1.5}s` }}
            >
              {index === 2 ? (
                <>
                  <div className={s.intelligenceOrb}>
                    <span className={s.orbitRing} aria-hidden="true" />
                    <span className={s.orbitRingInner} aria-hidden="true" />
                    <span className={s.intelligenceIcon}>
                      <Icon name={icon} size={38} />
                    </span>
                    <span className={s.orbLabel}>03 / INTELLIGENCE</span>
                  </div>
                  <h3>{title}</h3>
                  <p>{detail}</p>
                </>
              ) : (
                <>
                  <div className={s.nodeTopline}>
                    <span>
                      0{index + 1} / {type}
                    </span>
                    <span className={s.nodeIndicator} />
                  </div>
                  <div className={s.nodeBody}>
                    <span className={s.nodeIcon}>
                      <Icon name={icon} size={21} />
                    </span>
                    <div>
                      <h3>{title}</h3>
                      <p>{detail}</p>
                    </div>
                  </div>
                  <div className={s.nodeDetail} aria-hidden="true">
                    {index === 0 ? (
                      <>
                        <span className={s.payloadBraces}>{"{ }"}</span>
                        <span>incoming event</span>
                        <span className={s.payloadDot} />
                      </>
                    ) : index === 1 ? (
                      <>
                        <span className={s.knowledgeLines}>
                          <i />
                          <i />
                          <i />
                        </span>
                        <span>context, connected</span>
                      </>
                    ) : (
                      <>
                        <Icon name="check" size={12} />
                        <span>ready to deliver</span>
                        <Icon name="external" size={12} />
                      </>
                    )}
                  </div>
                </>
              )}
              {index !== 0 && <span className={s.portIn} aria-hidden="true" />}
              {index !== 3 && <span className={s.portOut} aria-hidden="true" />}
            </li>
          ))}
        </ol>
      </div>
      <div className={s.flowDock}>
        <div
          className={s.exampleSwitcher}
          role="group"
          aria-label="Explore example workflows"
        >
          {examples.map((item, index) => (
            <button
              key={item.name}
              type="button"
              aria-pressed={selected === index}
              onClick={() => setSelected(index)}
            >
              <Icon name={index === 0 ? "mail" : "clock"} size={13} />
              {item.name}
            </button>
          ))}
        </div>
        <p className={s.flowCaption} aria-live="polite">
          {example.title}
        </p>
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
];

function Connections() {
  const [scrollPaused, setScrollPaused] = useState(false);
  return (
    <section
      className={s.connections}
      aria-label="Supported tools and providers"
    >
      <div className={s.toolsHeading}>
        <p>
          YOUR TOOLS. <br />
          WORKING TOGETHER.
        </p>
        <button
          type="button"
          className={s.motionButton}
          onClick={() => setScrollPaused(!scrollPaused)}
          aria-label={
            scrollPaused ? "Resume tools scrolling" : "Pause tools scrolling"
          }
          aria-pressed={scrollPaused}
          aria-controls="landing-tools"
        >
          <Icon name={scrollPaused ? "play" : "pause"} size={13} />
        </button>
      </div>
      <div
        id="landing-tools"
        className={s.toolsViewport}
        data-motion-paused={scrollPaused}
      >
        <div className={s.toolsTrack}>
          {[0, 1].map((copy) => (
            <ul
              key={copy}
              className={s.toolsGroup}
              aria-hidden={copy === 1 ? true : undefined}
            >
              {connectedTools.map((tool) => (
                <li key={tool.name}>
                  {tool.image ? (
                    <Image
                      className={`${tool.name === "OpenAI" ? s.openaiMark : ""} ${tool.wordmark ? s.wordmark : ""}`}
                      src={tool.image}
                      alt={tool.wordmark ? tool.name : ""}
                      width={tool.wordmark ? 58 : 23}
                      height={24}
                    />
                  ) : (
                    <Icon name={tool.icon} size={23} />
                  )}
                  {!tool.wordmark && <span>{tool.name}</span>}
                </li>
              ))}
            </ul>
          ))}
        </div>
      </div>
    </section>
  );
}

function ProductSection() {
  return (
    <section className={s.product} id="product" aria-labelledby="product-title">
      <div className={s.sectionHeading}>
        <div>
          <span className={s.kicker}>01 / THE POSSIBILITIES</span>
          <h2 id="product-title">
            A clear path from
            <br />
            trigger to done.
          </h2>
        </div>
        <p>
          Bring your tools, knowledge, and decisions into one visual workflow.
          Follow every step as the work moves forward.
        </p>
      </div>
      <div className={s.features}>
        <article>
          <span className={s.featureIcon}>
            <Icon name="bolt" size={24} />
          </span>
          <h3>Start with a signal.</h3>
          <p>
            A webhook, a schedule, or a manual run. Turn the moment something
            happens into the start of something useful.
          </p>
          <span className={s.featureDetail}>
            Webhooks · Schedules · Manual triggers
          </span>
        </article>
        <article>
          <span className={s.featureIcon}>
            <Icon name="book" size={24} />
          </span>
          <h3>Give AI the context.</h3>
          <p>
            Search your documents, retrieve relevant knowledge, and let AI
            generate content or choose the next step.
          </p>
          <span className={s.featureDetail}>
            Knowledge retrieval · AI decisions
          </span>
        </article>
        <article>
          <span className={s.featureIcon}>
            <Icon name="shield" size={24} />
          </span>
          <h3>Stay in the loop.</h3>
          <p>
            Pause for human approval, inspect execution history, and recover
            failed steps with the full picture in view.
          </p>
          <span className={s.featureDetail}>
            Approvals · Execution history · Recovery
          </span>
        </article>
      </div>
    </section>
  );
}

function McpSection() {
  return (
    <section className={s.mcp} id="mcp" aria-labelledby="mcp-title">
      <div className={s.mcpCopy}>
        <span className={s.kicker}>02 / MCP INTEGRATION</span>
        <h2 id="mcp-title">
          Your workflows.
          <br />
          <span>In the conversation.</span>
        </h2>
        <p>
          Connect Relay to ChatGPT or Claude through the Model Context Protocol.
          Build workflows, run automations, and explore results from your AI
          assistant.
        </p>
        <div className={s.assistants}>
          <span>
            <Image
              className={s.openaiMark}
              src="/brand/openai.svg"
              width={21}
              height={21}
              alt=""
            />{" "}
            ChatGPT
          </span>
          <span>
            <Image src="/brand/claude.svg" width={23} height={23} alt="" />{" "}
            Claude
          </span>
          <span className={s.protocol}>MCP</span>
        </div>
        <div className={s.mcpActions}>
          <Link href="/integrations" className={s.primary}>
            Set up MCP <Icon size={16} />
          </Link>
          <ExternalLink href={mcpDocs} className={s.textLink}>
            Read the docs
          </ExternalLink>
        </div>
        <p className={s.permissionNote}>
          <Icon name="shield" size={14} /> Sign in to connect. You choose the
          OAuth permissions.
        </p>
      </div>
      <div className={s.conversation}>
        <div className={s.conversationHeader}>
          <span>
            <Icon name="spark" size={16} /> Relay × your assistant
          </span>
          <span className={s.exampleLabel}>EXAMPLE</span>
        </div>
        <div className={s.conversationBody}>
          <div className={s.userMessage}>
            Show my recent workflow executions.
          </div>
          <div className={s.assistantMessage}>
            <span className={s.relayAvatar}>
              <Icon name="flow" size={19} />
            </span>
            <div className={s.assistantContent}>
              <span className={s.toolCall}>
                <Icon name="check" size={13} /> relay_list_executions
              </span>
              <p>Here’s what’s been running in your workspace.</p>
              <ul className={s.runList}>
                <li>
                  <span>
                    <Icon name="mail" size={15} /> Customer support
                  </span>
                  <span>
                    <i /> Completed
                  </span>
                </li>
                <li>
                  <span>
                    <Icon name="clock" size={15} /> Weekly report
                  </span>
                  <span>
                    <i /> Completed
                  </span>
                </li>
              </ul>
            </div>
          </div>
          <div className={s.conversationNote}>
            <Icon name="shield" size={14} />
            <span>Your workspace. Your approved permissions.</span>
          </div>
        </div>
        <div className={s.conversationFooter}>
          <span>Discover</span>
          <span>Build</span>
          <span>Execute</span>
          <span>Inspect</span>
        </div>
      </div>
    </section>
  );
}

function DeveloperSection() {
  const [copyStatus, setCopyStatus] = useState("");
  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(cloneCommand);
      setCopyStatus("Clone command copied.");
    } catch {
      setCopyStatus("Select the command to copy it manually.");
    }
  }
  return (
    <section
      className={s.developers}
      id="developers"
      aria-labelledby="developers-title"
    >
      <div className={s.sectionHeading}>
        <div>
          <span className={s.kicker}>03 / BEHIND THE BUILD</span>
          <h2 id="developers-title">Made for the curious.</h2>
        </div>
        <p>
          Explore how Relay works, run it yourself, or help shape what comes
          next. It starts with the source.
        </p>
      </div>
      <div className={s.developerGrid}>
        <article className={s.repositoryCard}>
          <div className={s.cardEyebrow}>
            <Icon name="github" size={22} />
            <span>THE GIT REPOSITORY</span>
            <span className={s.publicBadge}>Public</span>
          </div>
          <h3>
            <a href={repository} target="_blank" rel="noopener noreferrer">
              <span>shaad4 /</span> relay-workflow-automation
              <Icon name="external" size={19} />
              <span className={s.srOnly}> (opens in a new tab)</span>
            </a>
          </h3>
          <p>
            From the visual canvas to the execution engine. Explore the code,
            architecture, and deployment guides on GitHub.
          </p>
          <div className={s.cloneCommand}>
            <span aria-hidden="true">$</span>
            <code>{cloneCommand}</code>
            <button
              type="button"
              onClick={copyCommand}
              aria-label="Copy Git clone command"
              title="Copy Git clone command"
            >
              <Icon
                name={copyStatus === "Clone command copied." ? "check" : "copy"}
                size={17}
              />
            </button>
          </div>
          <span className={s.copyStatus} role="status">
            {copyStatus}
          </span>
          <ul className={s.stack} aria-label="Technology stack">
            {["Next.js", "Python", "FastAPI", "PostgreSQL", "Kafka"].map(
              (name) => (
                <li key={name}>{name}</li>
              ),
            )}
          </ul>
          <div className={s.repositoryLinks}>
            <ExternalLink href={repository} className={s.textLink}>
              Explore repository
            </ExternalLink>
            <ExternalLink
              href={`${repository}/tree/dev/deploy`}
              className={s.mutedLink}
            >
              Self-hosting guide
            </ExternalLink>
          </div>
        </article>
        <article className={s.developerCard}>
          <span className={s.kicker}>MEET THE DEVELOPER</span>
          <div className={s.developerIdentity}>
            <span className={s.developerAvatar}>
              <Image
                src="/brand/developer-shaad.jpg"
                alt="Mohammed Shaad N"
                width={80}
                height={80}
              />
              <span aria-hidden="true">
                <Icon name="code" size={15} />
              </span>
            </span>
            <div>
              <h3>Mohammed Shaad N</h3>
              <a
                href="https://github.com/shaad4"
                target="_blank"
                rel="noopener noreferrer"
              >
                @shaad4
                <span className={s.srOnly}>
                  {" "}
                  on GitHub (opens in a new tab)
                </span>
              </a>
            </div>
          </div>
          <p>
            The developer behind Relay. Follow the project, explore the
            implementation, or share an idea for what to build next.
          </p>
          <div className={s.developerLinks}>
            <ExternalLink
              href="https://github.com/shaad4"
              className={s.textLink}
            >
              GitHub profile
            </ExternalLink>
            <ExternalLink href={`${repository}/issues`} className={s.mutedLink}>
              Ideas & issues
            </ExternalLink>
          </div>
        </article>
      </div>
    </section>
  );
}

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef(null);
  function closeOnEscape(event) {
    if (event.key === "Escape" && menuOpen) {
      setMenuOpen(false);
      menuButton.current?.focus();
    }
  }
  return (
    <div className={s.page}>
      <a href="#main" className={s.skip}>
        Skip to content
      </a>
      <header className={s.header} onKeyDown={closeOnEscape}>
        <div className={s.navInner}>
          <Link href="/" aria-label="Relay home" className={s.logo}>
            <Image
              src="/brand/relay/relay-light.png"
              alt="Relay"
              width={110}
              height={45}
              priority
            />
          </Link>
          <nav
            id="landing-navigation"
            className={`${s.nav} ${menuOpen ? s.navOpen : ""}`}
            aria-label="Main navigation"
          >
            <a href="#product" onClick={() => setMenuOpen(false)}>
              Product
            </a>
            <a href="#mcp" onClick={() => setMenuOpen(false)}>
              MCP integration
            </a>
            <a href="#developers" onClick={() => setMenuOpen(false)}>
              Developers
            </a>
            <ExternalLink href={repository} className={s.navGithub}>
              <Icon name="github" size={15} /> GitHub
            </ExternalLink>
            <Link href="/login" className={s.mobileSignIn}>
              Sign in
            </Link>
          </nav>
          <div className={s.navActions}>
            <Link href="/login" className={s.signIn}>
              Sign in
            </Link>
            <Link href="/register" className={s.navCta}>
              Start building <Icon size={14} />
            </Link>
            <button
              ref={menuButton}
              type="button"
              className={s.menuToggle}
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              aria-controls="landing-navigation"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen(!menuOpen)}
            >
              <Icon name={menuOpen ? "close" : "menu"} />
            </button>
          </div>
        </div>
      </header>
      <main id="main" className={s.main}>
        <section className={s.hero} aria-labelledby="hero-title">
          <div className={s.heroCopy}>
            <a href="#mcp" className={s.announcement}>
              <span>MCP INTEGRATION</span> Meet Relay in your AI assistant{" "}
              <Icon name="arrow" size={14} />
            </a>
            <h1 id="hero-title">
              Give your ideas
              <br />a way to <span>work.</span>
            </h1>
            <p>
              Connect your tools. Bring your knowledge.
              <br className={s.desktopBreak} /> Build intelligent workflows that
              take care of the steps in between.
            </p>
            <div className={s.heroActions}>
              <Link href="/register" className={s.primary}>
                Start building <Icon size={16} />
              </Link>
              <ExternalLink href={repository} className={s.secondary}>
                <Icon name="github" size={17} /> View on GitHub
              </ExternalLink>
            </div>
            <div className={s.heroNote}>
              <span>
                <Icon name="flow" size={14} /> Visual by design
              </span>
              <span>
                <Icon name="spark" size={14} /> AI in the loop
              </span>
            </div>
          </div>
          <WorkflowPreview />
        </section>
        <Connections />
        <ProductSection />
        <McpSection />
        <DeveloperSection />
        <section className={s.finalCta} aria-labelledby="cta-title">
          <div>
            <span className={s.kicker}>LESS REPETITION. MORE POSSIBILITY.</span>
            <h2 id="cta-title">
              Make your next move
              <br />
              <span>a workflow.</span>
            </h2>
          </div>
          <div>
            <Link href="/register" className={s.primary}>
              Build your first workflow <Icon size={17} />
            </Link>
            <p>From the first trigger to the final action.</p>
          </div>
        </section>
      </main>
      <footer className={s.footer}>
        <div className={s.footerTop}>
          <div>
            <Link href="/" aria-label="Relay home">
              <Image
                src="/brand/relay/relay-light.png"
                alt="Relay"
                width={99}
                height={40}
              />
            </Link>
            <p>Intelligent workflows. Thoughtfully connected.</p>
          </div>
          <nav aria-label="Footer navigation">
            <a href="#product">Product</a>
            <a href="#mcp">MCP integration</a>
            <a href="#developers">Developer</a>
            <ExternalLink href={repository}>GitHub</ExternalLink>
          </nav>
        </div>
        <div className={s.footerBottom}>
          <small>
            © {new Date().getFullYear()} Relay. Built by{" "}
            <a
              href="https://github.com/shaad4"
              target="_blank"
              rel="noopener noreferrer"
            >
              Mohammed Shaad N
              <span className={s.srOnly}> (opens in a new tab)</span>
            </a>
            .
          </small>
          <div>
            <Link href="/privacy">Privacy Policy</Link>
            <Link href="/terms">Terms of Service</Link>
          </div>
          <a href="#main">Back to top ↑</a>
        </div>
      </footer>
    </div>
  );
}
