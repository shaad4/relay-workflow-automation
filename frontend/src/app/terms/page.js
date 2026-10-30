import PolicyPage, { privacyContact } from "@/components/legal/PolicyPage";

export const metadata = {
  title: "Terms of Service",
  description:
    "Terms for using Relay’s workflow automation, connected services, and AI features.",
  alternates: { canonical: "https://relay.shaad.site/terms" },
};

const sections = [
  {
    id: "acceptance",
    title: "Acceptance of terms",
    content: (
      <p>
        These terms govern your use of Relay at{" "}
        <a href="https://relay.shaad.site">relay.shaad.site</a>. By creating an
        account or using Relay, you agree to these terms. If you do not agree,
        do not use the service. You must have legal capacity to enter this
        agreement and authority to act for any organization or account you
        represent.
      </p>
    ),
  },
  {
    id: "service",
    title: "The service",
    content: (
      <p>
        Relay helps you build and run workflows that connect third-party tools,
        send email, call APIs, use AI providers, and retrieve information from
        uploaded knowledge bases. Workflow actions can occur automatically based
        on the triggers and schedules you configure. You are responsible for
        reviewing and testing workflows before enabling them and for monitoring
        their effects.
      </p>
    ),
  },
  {
    id: "accounts",
    title: "Accounts and responsibilities",
    content: (
      <p>
        Provide accurate account information, safeguard your credentials, and
        manage workspace membership and connected accounts responsibly. You are
        responsible for activity you authorize through your account and
        workspace. Notify us at {privacyContact} if you believe your account has
        been compromised. Do not share access you are not authorized to grant.
      </p>
    ),
  },
  {
    id: "acceptable-use",
    title: "Acceptable automation",
    content: (
      <>
        <p>
          Use Relay only for lawful purposes and with the permissions needed for
          the information, systems, and recipients involved. Obtain any required
          consent and honor applicable communication preferences and opt-out
          requests.
        </p>
        <p>
          Do not send spam, deceptive messages, phishing, or malware; access
          accounts or systems without authorization; infringe privacy or
          intellectual property rights; bypass provider limits or security
          controls; or disrupt, overload, or abuse Relay or connected services.
          Do not configure workflows to perform actions you would not be
          authorized to perform directly.
        </p>
      </>
    ),
  },
  {
    id: "third-parties",
    title: "Connected third-party services",
    content: (
      <>
        <p>
          Connecting a service authorizes Relay to use that connection for the
          workflow actions you configure. Gmail connections permit
          user-authorized sending through the Gmail API, not reading your inbox.
          You are responsible for recipients and content, including messages
          sent by automated workflows.
        </p>
        <p>
          Third-party services have their own terms, privacy policies,
          permissions, and limits. Their availability and behavior may change
          independently of Relay. You can disconnect a service in Relay and
          revoke OAuth access with the provider. Disconnecting does not undo
          completed actions or remove data already delivered to others.
        </p>
      </>
    ),
  },
  {
    id: "ai",
    title: "AI output and review",
    content: (
      <p>
        AI-generated content can be inaccurate, incomplete, biased, or
        unsuitable for your purpose. Knowledge-base retrieval does not guarantee
        accuracy. Review outputs before relying on them, sending them to others,
        or using them to make consequential decisions. Relay does not provide
        professional medical, legal, financial, or other regulated advice
        through generated outputs.
      </p>
    ),
  },
  {
    id: "usage",
    title: "API usage and provider charges",
    content: (
      <p>
        Your workflows may consume API quotas, AI tokens, storage, or other
        resources with connected providers. You are responsible for charges
        incurred under your agreements with those providers, including usage
        caused by schedules, retries, or repeated executions. Review provider
        pricing and limits before enabling workflows. These terms do not
        establish a Relay paid subscription or pricing plan.
      </p>
    ),
  },
  {
    id: "availability",
    title: "Availability and changes",
    content: (
      <p>
        Relay may change, add, restrict, or discontinue features. Maintenance,
        failures, provider outages, and usage limits may interrupt workflows or
        delay actions. We do not promise uninterrupted availability or that
        every execution will complete successfully. Keep appropriate copies of
        important content and review execution history for failures. We will
        provide notice of material service changes where reasonably practicable.
      </p>
    ),
  },
  {
    id: "ownership",
    title: "Intellectual property and content",
    content: (
      <p>
        You retain your rights in the content you submit. You grant Relay
        permission to host, process, transmit, and display that content as
        needed to provide the service and execute your workflows, as described
        in the <a href="/privacy">Privacy Policy</a>. You must hold the rights
        needed to grant that permission. Relay’s branding and service materials
        remain the property of their respective owners. Use of Relay does not
        grant ownership of those materials. Rights in third-party materials and
        AI outputs are subject to applicable law and provider terms.
      </p>
    ),
  },
  {
    id: "disclaimers",
    title: "Disclaimers and liability",
    content: (
      <>
        <p>
          To the extent permitted by applicable law, Relay is provided “as is”
          and “as available,” without warranties of merchantability, fitness for
          a particular purpose, or non-infringement. We do not warrant that
          workflows or outputs will be error-free or meet every requirement.
        </p>
        <p>
          To the extent permitted by law, Relay’s operator will not be liable
          for indirect, incidental, special, or consequential losses arising
          from use of the service, including lost profits or business
          interruption. Nothing in these terms excludes or limits liability for
          fraud, willful misconduct, gross negligence, or any liability or
          consumer right that cannot lawfully be excluded or limited. Any
          remaining liability is determined under applicable law.
        </p>
      </>
    ),
  },
  {
    id: "termination",
    title: "Suspension and termination",
    content: (
      <p>
        We may suspend or terminate access when reasonably necessary to address
        violations of these terms, security threats, abuse, or legal
        requirements. Where appropriate and practicable, we will provide notice
        and an opportunity to resolve the issue. You may stop using Relay,
        disconnect services, and request account deletion at {privacyContact}.
        Stop active workflows before leaving the service. Data handling
        following termination is described in the{" "}
        <a href="/privacy#retention">Privacy Policy</a>.
      </p>
    ),
  },
  {
    id: "updates",
    title: "Updates and contact",
    content: (
      <p>
        We may revise these terms and will update the date above. We will
        provide appropriate notice of material changes. If you do not accept
        revised terms, stop using Relay. For service questions, concerns, or
        requests relating to these terms, contact {privacyContact}.
      </p>
    ),
  },
];

export default function TermsPage() {
  return (
    <PolicyPage
      title="Terms of Service"
      introduction="These terms explain the responsibilities that come with building and running automations in Relay."
      sections={sections}
    />
  );
}
