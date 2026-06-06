"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  motion,
  AnimatePresence,
  useScroll,
  useTransform,
  useInView,
  useSpring,
  useMotionValue,
} from "framer-motion";
import {
  Shield,
  Zap,
  Globe,
  Download,
  ChevronRight,
  Terminal,
  ArrowRight,
  Server,
  Lock,
  Activity,
  Layers,
  Cpu,
  Wifi,
  Copy,
  Check,
  ChevronDown,
  ExternalLink,
  FileCode,
  Settings,
  Monitor,
  Play,
  Pause,
  Eye,
  BookOpen,
  Command,
  Database,
  Network,
  Rocket,
  Sparkles,
  CheckCircle2,
  Clock,
  RefreshCw,
  Search,
  X,
  Menu,
  ArrowUpRight,
  Code2,
  GitBranch,
  Box,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

/* ═══════════════════════════════════════════════════════════
   TYPES
   ═══════════════════════════════════════════════════════════ */

interface InstallerFile {
  name: string;
  desc: string;
  version: string;
  size: string;
  icon: LucideIcon;
  color: string;
  glowClass: string;
  badge: string;
  badgeColor: string;
  category: string;
}

interface ArchLayer {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  color: string;
  items: string[];
}

interface WalkthroughStep {
  step: number;
  title: string;
  desc: string;
  command: string;
  icon: LucideIcon;
  color: string;
}

interface FaqItem {
  q: string;
  a: string;
}

interface SkillCard {
  name: string;
  desc: string;
  icon: LucideIcon;
  color: string;
}

/* ═══════════════════════════════════════════════════════════
   DATA
   ═══════════════════════════════════════════════════════════ */

const NAV_ITEMS = [
  { id: "hero", label: "Home", icon: Box },
  { id: "download", label: "Download", icon: Download },
  { id: "architecture", label: "Architecture", icon: Layers },
  { id: "walkthrough", label: "Walkthrough", icon: Rocket },
  { id: "knowledge", label: "Knowledge", icon: BookOpen },
];

const INSTALLER_FILES: InstallerFile[] = [
  {
    name: "install_owl_unified.sh",
    desc: "Complete unified installer — all components in one script",
    version: "v6.0",
    size: "~45KB",
    icon: Terminal,
    color: "#BFFF00",
    glowClass: "glow-lime",
    badge: "MAIN",
    badgeColor: "bg-owl-lime/15 text-owl-lime border-owl-lime/20",
    category: "installer",
  },
  {
    name: "validate_owl.sh",
    desc: "Post-install validation & mock test suite with 8 checks",
    version: "v1.0",
    size: "~12KB",
    icon: CheckCircle2,
    color: "#00F0FF",
    glowClass: "glow-cyan",
    badge: "QA",
    badgeColor: "bg-owl-cyan/15 text-owl-cyan border-owl-cyan/20",
    category: "installer",
  },
  {
    name: "forward_proxy.py",
    desc: "HTTP/HTTPS forward proxy with domain bypass & upstream chaining",
    version: "v2.0",
    size: "~8KB",
    icon: Network,
    color: "#A855F7",
    glowClass: "glow-violet",
    badge: "CORE",
    badgeColor: "bg-owl-violet/15 text-owl-violet border-owl-violet/20",
    category: "python",
  },
  {
    name: "proxy_defense_fixed_v3.py",
    desc: "Resilient client: circuit breaker, proxy rotation, caching, dedup",
    version: "v3.3",
    size: "~18KB",
    icon: Shield,
    color: "#FF3E9A",
    glowClass: "glow-pink",
    badge: "DEFENSE",
    badgeColor: "bg-owl-pink/15 text-owl-pink border-owl-pink/20",
    category: "python",
  },
  {
    name: "owl_resilient_mcp.py",
    desc: "MCP server exposing resilient HTTP tools for AI agents",
    version: "v1.1",
    size: "~22KB",
    icon: Cpu,
    color: "#FFB800",
    glowClass: "glow-amber",
    badge: "MCP",
    badgeColor: "bg-owl-amber/15 text-owl-amber border-owl-amber/20",
    category: "python",
  },
  {
    name: "proxy_sources.json",
    desc: "Auto-discovery enrichment proxy source configuration",
    version: "v1.0",
    size: "~1KB",
    icon: Globe,
    color: "#00FF88",
    glowClass: "",
    badge: "CONFIG",
    badgeColor: "bg-owl-green/15 text-owl-green border-owl-green/20",
    category: "config",
  },
];

const ARCHITECTURE_LAYERS: ArchLayer[] = [
  {
    title: "Unified Gateway",
    subtitle: "kiro-gateway core",
    icon: Server,
    color: "#BFFF00",
    items: ["OpenAI/Anthropic-compatible API", "Single stable API key", "Port 8333"],
  },
  {
    title: "Proxy Router",
    subtitle: "Intelligent request routing",
    icon: Zap,
    color: "#00F0FF",
    items: ["Model-aware routing", "Quota-aware selection", "Health-based failover"],
  },
  {
    title: "Credential Stitcher",
    subtitle: "Free-tier credential pool",
    icon: Lock,
    color: "#A855F7",
    items: ["Kiro Developer Tokens", "Claude Max Sessions", "OpenCode API Keys"],
  },
  {
    title: "Skill Orchestrator",
    subtitle: "Ecosystem skill delegation",
    icon: Layers,
    color: "#FF3E9A",
    items: ["find-skills discovery", "SKILL.md execution", "Modular access methods"],
  },
  {
    title: "Billing Abstraction",
    subtitle: "Unified usage tracking",
    icon: Database,
    color: "#FFB800",
    items: ["Aggregate usage from all backends", "Free-tier limit enforcement", "Cost fallback chain"],
  },
  {
    title: "Forward Proxy",
    subtitle: "Domain bypass & upstream",
    icon: Wifi,
    color: "#00FF88",
    items: ["Port 60000", "NVIDIA/OpenCode bypass", "Upstream chaining (Mihomo)"],
  },
];

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    step: 1,
    title: "Install the Stack",
    desc: "Run the unified installer. It handles Python venv, system deps, Kiro gateway, MCP server, and systemd services automatically.",
    command: "chmod +x install_owl_unified.sh && ./install_owl_unified.sh",
    icon: Rocket,
    color: "#BFFF00",
  },
  {
    step: 2,
    title: "Validate Everything",
    desc: "Run the validation suite to confirm all components are installed, services are running, and bypass logic works correctly.",
    command: "chmod +x validate_owl.sh && ./validate_owl.sh",
    icon: CheckCircle2,
    color: "#00F0FF",
  },
  {
    step: 3,
    title: "Configure Your Agent",
    desc: "The installer auto-injects Kiro provider into OpenCode config and adds the owl-resilient-http MCP server. Restart your IDE.",
    command: "# Auto-configured. Just restart OpenCode/Copilot.",
    icon: Settings,
    color: "#A855F7",
  },
  {
    step: 4,
    title: "Start Building",
    desc: "Point any OpenAI/Anthropic-compatible client to http://localhost:8333/v1 with API key kiro-gateway-8333. Free-tier AI access is now unified.",
    command:
      'curl http://localhost:8333/v1/chat/completions \\\n  -H "Authorization: Bearer kiro-gateway-8333" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model":"auto","messages":[{"role":"user","content":"Hello"}]}\'',
    icon: Sparkles,
    color: "#FF3E9A",
  },
];

const FAQ_ITEMS: FaqItem[] = [
  {
    q: "What does OWL-AGENT actually do?",
    a: "OWL-AGENT is a unified proxy gateway that aggregates free-tier access across multiple AI providers (Kiro, Claude Max, OpenCode). It stitches credentials, routes requests intelligently, and presents a single API endpoint — so you get free AI model access without managing multiple accounts or API keys.",
  },
  {
    q: "Is this really free?",
    a: "Yes — it maximizes free-tier quotas across providers. The credential stitcher rotates through Kiro Developer Tokens, Claude Max free trials, and OpenCode community keys. When one quota exhausts, it automatically falls back to the next. Paid fallback exists but is never the default.",
  },
  {
    q: "What's the difference between the Forward Proxy and the Gateway?",
    a: "The Forward Proxy (port 60000) is a raw HTTP proxy that handles domain bypass (NVIDIA, OpenCode go direct, everything else routes upstream). The Kiro Gateway (port 8333) is an API-compatible server that translates OpenAI/Anthropic API calls to backend providers. They work together: agents → Gateway → Forward Proxy → Internet.",
  },
  {
    q: "Can I use this with GitHub Copilot or Cursor?",
    a: "Yes! The installer auto-configures MCP servers (owl-resilient-http and parallel-web-search) into OpenCode/Copilot config. For Cursor or other tools, set HTTP_PROXY=http://127.0.0.1:60000 and point your API base URL to http://localhost:8333/v1.",
  },
  {
    q: "What if I already have v3.1 installed?",
    a: "v6.0 is a full upgrade, not a breakage. It overwrites the old proxy_defense_fixed_v2.py with v3.3 (which includes the missing forward_proxy.py on port 60000). Without this, all CLI wrappers will fail with connection refused. You MUST upgrade to use the wrappers.",
  },
  {
    q: "What are the system requirements?",
    a: "Linux (Ubuntu/Debian recommended), Python 3.8+, and internet access. The installer handles all dependencies (aiohttp, httpx, etc.). For the Kiro Gateway, you need Node.js if you want the MCP parallel-web-search tool.",
  },
];

const SKILL_CARDS: SkillCard[] = [
  { name: "Silent Protocol", desc: "Pre-response diagnostic layer that routes speed vs depth", icon: Eye, color: "#BFFF00" },
  { name: "Depth-Seeking Mode", desc: "Recursive first-principals analysis for complex problems", icon: Search, color: "#00F0FF" },
  { name: "Compounding Editions", desc: "Build on existing work. Integration over reinvention.", icon: Layers, color: "#A855F7" },
  { name: "Proxy Defense Stack", desc: "5-tier: weighted rotation, circuit breaker, dedup, caching, rate limit", icon: Shield, color: "#FF3E9A" },
  { name: "MCP Resilient HTTP", desc: "AI agent middleware with cache, circuit breaker, offline queue", icon: Cpu, color: "#FFB800" },
  { name: "find-skills", desc: "Discover and install agent skills from the ecosystem", icon: Command, color: "#00FF88" },
  { name: "7-Agent Pipeline", desc: "Decision → Simulator → Impl → Auditor → Profiler → Optimizer → Maint", icon: RefreshCw, color: "#BFFF00" },
  { name: "Credential Stitcher", desc: "Pool management and rotation for free-tier credentials", icon: Lock, color: "#00F0FF" },
];

const FLOW_NODES = [
  { label: "Client", color: "#F0F0F5", x: 0 },
  { label: "Gateway", color: "#BFFF00", x: 1 },
  { label: "Router", color: "#00F0FF", x: 2 },
  { label: "Creds", color: "#A855F7", x: 3 },
  { label: "Proxy", color: "#00FF88", x: 4 },
  { label: "APIs", color: "#FF3E9A", x: 5 },
];

/* ═══════════════════════════════════════════════════════════
   ANIMATION VARIANTS
   ═══════════════════════════════════════════════════════════ */

const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] } },
};

const fadeUpFast = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.06 } },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

const slideInLeft = {
  hidden: { opacity: 0, x: -40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

const slideInRight = {
  hidden: { opacity: 0, x: 40 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

/* ═══════════════════════════════════════════════════════════
   UTILITY COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function AnimatedSection({
  children,
  className = "",
  id = "",
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.section
      ref={ref}
      id={id}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      variants={stagger}
      className={className}
    >
      {children}
    </motion.section>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-md hover:bg-white/10 transition-colors focus-ring"
      aria-label={copied ? "Copied" : "Copy code"}
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-owl-green" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-muted-foreground" />
      )}
    </button>
  );
}

function TerminalBlock({
  code,
  language = "bash",
  title,
}: {
  code: string;
  language?: string;
  title?: string;
}) {
  return (
    <div className="relative group rounded-xl bg-[#08080D] border border-owl-border/60 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-owl-border/40 bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-[#28C840]/60" />
          </div>
          {title && (
            <span className="text-[11px] font-mono text-muted-foreground/60 ml-2">
              {title}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-muted-foreground/40 uppercase">
            {language}
          </span>
          <CopyButton text={code} />
        </div>
      </div>
      <pre className="p-4 overflow-x-auto text-[13px] font-mono leading-[1.7]">
        <code className="text-owl-lime/85">{code}</code>
      </pre>
    </div>
  );
}

function SectionBadge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <motion.div variants={fadeUpFast} className="flex justify-center mb-5">
      <div
        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-[0.15em]"
        style={{
          backgroundColor: `${color}10`,
          color: color,
          border: `1px solid ${color}25`,
        }}
      >
        {children}
      </div>
    </motion.div>
  );
}

/* ═══════════════════════════════════════════════════════════
   NAVIGATION
   ═══════════════════════════════════════════════════════════ */

function Navbar({ activeSection }: { activeSection: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { scrollY } = useScroll();

  useEffect(() => {
    const unsubscribe = scrollY.on("change", (v) => setScrolled(v > 50));
    return () => unsubscribe();
  }, [scrollY]);

  // Close mobile nav on escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <>
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled ? "glass-strong shadow-lg shadow-black/20" : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14 sm:h-16">
            {/* Logo */}
            <a href="#hero" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-owl-lime/10 flex items-center justify-center group-hover:bg-owl-lime/20 transition-colors">
                <span className="text-base">🦉</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-black text-base sm:text-lg tracking-tight">
                  OWL-AGENT
                </span>
                <Badge
                  variant="outline"
                  className="text-[9px] px-1.5 py-0 border-owl-lime/30 text-owl-lime font-mono hidden sm:inline-flex"
                >
                  v6.0
                </Badge>
              </div>
            </a>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-0.5 p-1 rounded-xl bg-white/[0.03] border border-owl-border/30">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`relative px-3.5 py-1.5 rounded-lg text-[13px] font-medium transition-all duration-300 focus-ring ${
                    activeSection === item.id
                      ? "text-owl-dark"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {activeSection === item.id && (
                    <motion.div
                      layoutId="activeNav"
                      className="absolute inset-0 rounded-lg bg-owl-lime"
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{item.label}</span>
                </a>
              ))}
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-xl hover:bg-white/5 transition-colors focus-ring"
              aria-label="Toggle navigation"
            >
              {mobileOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile Nav Overlay */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 35 }}
              className="fixed top-0 right-0 bottom-0 z-50 w-[260px] glass-strong md:hidden"
            >
              <div className="flex flex-col h-full pt-20 pb-8 px-6">
                <div className="space-y-1 flex-1">
                  {NAV_ITEMS.map((item, i) => (
                    <motion.a
                      key={item.id}
                      href={`#${item.id}`}
                      onClick={() => setMobileOpen(false)}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                        activeSection === item.id
                          ? "text-owl-lime bg-owl-lime/10"
                          : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                      }`}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </motion.a>
                  ))}
                </div>
                <div className="pt-6 border-t border-owl-border">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>🦉</span>
                    <span>OWL-AGENT v6.0</span>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════
   HERO
   ═══════════════════════════════════════════════════════════ */

function HeroSection() {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [0, -150]);
  const opacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);

  // Animated orbs
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const rect = e.currentTarget.getBoundingClientRect();
      setMousePos({
        x: (e.clientX - rect.left) / rect.width - 0.5,
        y: (e.clientY - rect.top) / rect.height - 0.5,
      });
    },
    []
  );

  return (
    <section
      ref={containerRef}
      id="hero"
      className="relative min-h-screen flex items-center overflow-hidden noise"
      onMouseMove={handleMouseMove}
    >
      {/* Background effects */}
      <div className="absolute inset-0 mesh-gradient" />
      <div className="absolute inset-0 dot-grid opacity-30" />

      {/* Animated orbs */}
      <motion.div
        className="absolute top-[20%] left-[15%] w-[500px] h-[500px] bg-owl-lime/[0.04] rounded-full blur-[150px]"
        animate={{ x: mousePos.x * 40, y: mousePos.y * 40 }}
        transition={{ type: "spring", stiffness: 50, damping: 30 }}
      />
      <motion.div
        className="absolute bottom-[20%] right-[10%] w-[400px] h-[400px] bg-owl-violet/[0.04] rounded-full blur-[150px]"
        animate={{ x: mousePos.x * -30, y: mousePos.y * -30 }}
        transition={{ type: "spring", stiffness: 50, damping: 30 }}
      />
      <motion.div
        className="absolute top-[50%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] bg-owl-cyan/[0.02] rounded-full blur-[200px]"
        animate={{ x: mousePos.x * 20, y: mousePos.y * 20 }}
        transition={{ type: "spring", stiffness: 40, damping: 25 }}
      />

      <motion.div
        style={{ y, opacity }}
        className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 w-full"
      >
        <div className="flex flex-col items-center text-center">
          {/* Status badge */}
          <motion.div
            variants={fadeUp}
            className="inline-flex items-center gap-2.5 px-5 py-2 rounded-full glass mb-10"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-owl-green opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-owl-green" />
            </span>
            <span className="text-[11px] font-mono text-muted-foreground tracking-wider">
              v6.0 — ALL SYSTEMS OPERATIONAL
            </span>
          </motion.div>

          {/* Main headline */}
          <motion.h1
            variants={fadeUp}
            className="text-[clamp(2.5rem,8vw,7rem)] font-black tracking-[-0.04em] leading-[0.9]"
          >
            <span className="block">ONE GATEWAY</span>
            <span className="block text-gradient-multi">ALL AI MODELS</span>
            <span className="block text-[clamp(1.5rem,4vw,4rem)] font-bold text-muted-foreground/70 mt-1">
              ZERO COST
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            variants={fadeUp}
            className="mt-6 sm:mt-8 max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed px-4"
          >
            The unified free-tier proxy stack for{" "}
            <span className="text-owl-cyan font-semibold">Hermes</span>,{" "}
            <span className="text-owl-violet font-semibold">Claude</span>,{" "}
            <span className="text-owl-pink font-semibold">OpenCode</span> &{" "}
            <span className="text-owl-amber font-semibold">Kiro</span>.
            <br className="hidden sm:block" />
            One API endpoint. Intelligent routing. Credential stitching. Resilient
            by default.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            variants={fadeUp}
            className="flex flex-col sm:flex-row items-center gap-3 mt-8 sm:mt-10"
          >
            <a href="#download">
              <Button
                size="lg"
                className="bg-owl-lime text-owl-dark hover:bg-owl-lime/90 font-bold text-[15px] px-8 h-12 rounded-xl glow-lime magnetic-btn group"
              >
                <Download className="w-4 h-4 mr-2 group-hover:animate-bounce" />
                Download Installer
                <ArrowRight className="w-4 h-4 ml-2 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
              </Button>
            </a>
            <a href="#architecture">
              <Button
                size="lg"
                variant="outline"
                className="border-owl-border/60 text-foreground hover:bg-white/5 hover:border-owl-border font-medium text-[15px] px-8 h-12 rounded-xl magnetic-btn"
              >
                <Eye className="w-4 h-4 mr-2" />
                View Architecture
              </Button>
            </a>
          </motion.div>

          {/* Quick stats */}
          <motion.div
            variants={fadeUp}
            className="grid grid-cols-3 gap-6 sm:gap-12 mt-14 sm:mt-20 w-full max-w-md"
          >
            {[
              { value: "6", label: "Core Files", color: "#BFFF00" },
              { value: "6", label: "Arch Layers", color: "#00F0FF" },
              { value: "4", label: "AI Providers", color: "#A855F7" },
            ].map((stat, i) => (
              <div key={stat.label} className="text-center group cursor-default">
                <div
                  className="text-3xl sm:text-4xl font-black transition-transform group-hover:scale-110"
                  style={{ color: stat.color }}
                >
                  {stat.value}
                </div>
                <div className="text-[11px] sm:text-xs text-muted-foreground mt-1.5 uppercase tracking-wider">
                  {stat.label}
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        animate={{ y: [0, 10, 0] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-[10px] font-mono text-muted-foreground/40 uppercase tracking-[0.2em]">
          Scroll
        </span>
        <ChevronDown className="w-4 h-4 text-muted-foreground/30" />
      </motion.div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD HUB
   ═══════════════════════════════════════════════════════════ */

function DownloadSection() {
  const [activeCategory, setActiveCategory] = useState<string>("all");

  const categories = useMemo(
    () => ["all", "installer", "python", "config"],
    []
  );

  const filteredFiles = useMemo(
    () =>
      activeCategory === "all"
        ? INSTALLER_FILES
        : INSTALLER_FILES.filter((f) => f.category === activeCategory),
    [activeCategory]
  );

  return (
    <AnimatedSection id="download" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div variants={fadeUp} className="text-center mb-10 sm:mb-14">
          <SectionBadge color="#BFFF00">
            <Download className="w-3 h-3 mr-1.5" />
            Download Center
          </SectionBadge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Grab the <span className="text-gradient-lime">Stack</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base leading-relaxed">
            Every file you need. One command to install. Full validation included.
          </p>
        </motion.div>

        {/* Main installer highlight */}
        <motion.div variants={scaleIn} className="mb-8">
          <div className="relative rounded-2xl overflow-hidden">
            {/* Animated border gradient */}
            <div className="absolute inset-0 rounded-2xl border-gradient" />
            <div className="relative glass glow-lime rounded-2xl p-6 sm:p-8">
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-5">
                <div className="flex items-start gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-owl-lime/10 flex items-center justify-center shrink-0">
                    <Terminal className="w-7 h-7 text-owl-lime" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5 mb-1.5">
                      <span className="font-black text-lg tracking-tight">
                        install_owl_unified.sh
                      </span>
                      <Badge
                        className={`${INSTALLER_FILES[0].badgeColor} text-[9px] border font-bold`}
                      >
                        MAIN INSTALLER
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      Complete stack: Forward Proxy + Proxy Defense + MCP Server +
                      Kiro Gateway + Systemd + Wrappers
                    </p>
                    {/* Feature flags */}
                    <div className="flex flex-wrap gap-2 mt-3">
                      {["--skip-kiro", "--skip-gateway", "--enrich", "--dry-run"].map(
                        (flag) => (
                          <span
                            key={flag}
                            className="px-2.5 py-0.5 rounded-md bg-white/[0.04] text-[11px] font-mono text-muted-foreground border border-owl-border/50"
                          >
                            {flag}
                          </span>
                        )
                      )}
                    </div>
                  </div>
                </div>
                <div className="w-full lg:w-auto lg:shrink-0">
                  <TerminalBlock
                    code="chmod +x install_owl_unified.sh && ./install_owl_unified.sh"
                    title="one-command install"
                  />
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Category filter */}
        <motion.div variants={fadeUpFast} className="flex items-center gap-2 mb-6 overflow-x-auto pb-2 scroll-snap-x">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-4 py-1.5 rounded-lg text-[12px] font-medium capitalize transition-all shrink-0 focus-ring ${
                activeCategory === cat
                  ? "bg-owl-lime/15 text-owl-lime border border-owl-lime/25"
                  : "bg-white/[0.03] text-muted-foreground border border-owl-border/40 hover:bg-white/[0.06] hover:text-foreground"
              }`}
            >
              {cat}
            </button>
          ))}
        </motion.div>

        {/* Bento grid of files */}
        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence mode="popLayout">
            {filteredFiles.map((file) => (
              <motion.div
                key={file.name}
                variants={scaleIn}
                layout
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.3 }}
              >
                <div className="relative group">
                  <div
                    className={`glass rounded-xl h-full transition-all duration-300 group-hover:scale-[1.02] ${file.glowClass}`}
                  >
                    <div className="p-5">
                      <div className="flex items-start justify-between mb-4">
                        <div
                          className="w-11 h-11 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
                          style={{ backgroundColor: `${file.color}12` }}
                        >
                          <file.icon className="w-5 h-5" style={{ color: file.color }} />
                        </div>
                        <Badge
                          className={`${file.badgeColor} text-[9px] border font-bold`}
                        >
                          {file.badge}
                        </Badge>
                      </div>
                      <h3 className="font-bold text-sm mb-1.5 font-mono tracking-tight">
                        {file.name}
                      </h3>
                      <p className="text-[12px] text-muted-foreground mb-4 leading-relaxed">
                        {file.desc}
                      </p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground/70 font-mono">
                          <span>{file.version}</span>
                          <span className="opacity-30">·</span>
                          <span>{file.size}</span>
                        </div>
                        <div
                          className="w-7 h-7 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all"
                          style={{ backgroundColor: `${file.color}15` }}
                        >
                          <ArrowUpRight
                            className="w-3.5 h-3.5"
                            style={{ color: file.color }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>

        {/* CLI Flags reference */}
        <motion.div variants={fadeUp} className="mt-8">
          <div className="glass rounded-xl p-5">
            <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
              <Settings className="w-4 h-4 text-owl-cyan" />
              CLI Flags Reference
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { flag: "--skip-kiro", desc: "Skip kiro-cli native binary download" },
                {
                  flag: "--skip-gateway",
                  desc: "Skip kiro-gateway setup (no port 8333)",
                },
                {
                  flag: "--enrich",
                  desc: "Enable proxy enrichment from auto-discovery sources",
                },
                {
                  flag: "--dry-run",
                  desc: "Validate without writing any files",
                },
              ].map((f) => (
                <div
                  key={f.flag}
                  className="flex gap-3 items-start p-3 rounded-lg bg-white/[0.02] border border-owl-border/30"
                >
                  <code className="font-mono text-owl-lime text-xs shrink-0 font-semibold">
                    {f.flag}
                  </code>
                  <span className="text-[12px] text-muted-foreground leading-relaxed">
                    {f.desc}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   ARCHITECTURE
   ═══════════════════════════════════════════════════════════ */

function ArchitectureSection() {
  const [hoveredLayer, setHoveredLayer] = useState<number | null>(null);

  return (
    <AnimatedSection id="architecture" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-15" />
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div variants={fadeUp} className="text-center mb-10 sm:mb-14">
          <SectionBadge color="#00F0FF">
            <Layers className="w-3 h-3 mr-1.5" />
            Architecture
          </SectionBadge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            How the <span className="text-gradient-cyan">Magic</span> Works
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base leading-relaxed">
            Six layers. One pipeline. Zero single points of failure.
          </p>
        </motion.div>

        {/* Architecture layers - Stacked */}
        <motion.div variants={stagger} className="space-y-3 max-w-4xl mx-auto">
          {ARCHITECTURE_LAYERS.map((layer, i) => (
            <motion.div
              key={layer.title}
              variants={fadeUp}
              onMouseEnter={() => setHoveredLayer(i)}
              onMouseLeave={() => setHoveredLayer(null)}
            >
              <div className="relative group">
                <div
                  className={`glass rounded-xl transition-all duration-300 ${
                    hoveredLayer === i ? "scale-[1.01]" : ""
                  }`}
                  style={
                    hoveredLayer === i
                      ? {
                          borderColor: `${layer.color}30`,
                          boxShadow: `0 0 30px ${layer.color}08`,
                        }
                      : undefined
                  }
                >
                  <div className="p-4 sm:p-5">
                    <div className="flex items-center gap-4">
                      {/* Layer icon */}
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-110"
                        style={{ backgroundColor: `${layer.color}12` }}
                      >
                        <layer.icon
                          className="w-6 h-6"
                          style={{ color: layer.color }}
                        />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span
                            className="text-[10px] font-mono font-bold tracking-wider"
                            style={{ color: layer.color }}
                          >
                            L{i + 1}
                          </span>
                          <h3 className="font-bold text-[15px] tracking-tight">
                            {layer.title}
                          </h3>
                          <span className="text-[12px] text-muted-foreground hidden sm:inline">
                            — {layer.subtitle}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {layer.items.map((item) => (
                            <span
                              key={item}
                              className="px-2 py-0.5 rounded-md text-[11px] font-medium border"
                              style={{
                                backgroundColor: `${layer.color}08`,
                                borderColor: `${layer.color}18`,
                                color: layer.color,
                              }}
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Connector dot */}
                      {i < ARCHITECTURE_LAYERS.length - 1 && (
                        <div className="hidden sm:flex flex-col items-center">
                          <motion.div
                            animate={{
                              y: hoveredLayer === i ? [0, 3, 0] : 0,
                            }}
                            transition={{ duration: 0.6, repeat: Infinity }}
                          >
                            <ChevronRight
                              className="w-4 h-4 rotate-90"
                              style={{ color: `${layer.color}40` }}
                            />
                          </motion.div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Request Flow Diagram */}
        <motion.div variants={fadeUp} className="mt-10">
          <div className="glass rounded-xl p-5 sm:p-6">
            <h3 className="text-sm font-bold flex items-center gap-2 mb-6">
              <Activity className="w-4 h-4 text-owl-green" />
              Request Flow
            </h3>
            {/* SVG Flow */}
            <div className="flex items-center justify-between gap-1 sm:gap-0 overflow-x-auto pb-2">
              {FLOW_NODES.map((node, i) => (
                <div key={node.label} className="flex items-center shrink-0">
                  <div className="flex flex-col items-center">
                    <motion.div
                      className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl flex items-center justify-center text-[10px] sm:text-[11px] font-bold font-mono"
                      style={{
                        backgroundColor: `${node.color}12`,
                        color: node.color,
                        border: `1px solid ${node.color}25`,
                      }}
                      whileHover={{ scale: 1.1 }}
                    >
                      {node.label}
                    </motion.div>
                  </div>
                  {i < FLOW_NODES.length - 1 && (
                    <motion.div
                      className="mx-1 sm:mx-2"
                      animate={{ x: [0, 4, 0] }}
                      transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                    >
                      <ArrowRight
                        className="w-3 h-3 sm:w-4 sm:h-4"
                        style={{ color: `${node.color}60` }}
                      />
                    </motion.div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* 3 Approaches */}
        <motion.div variants={fadeUp} className="mt-10">
          <h3 className="text-lg font-bold mb-5 text-center">
            Three Approaches, One Unified Stack
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                title: "Proxy Aggregation",
                desc: "Central router, decentralized proxies. Aggregates free-tier limits across providers for maximum throughput.",
                icon: Globe,
                color: "#BFFF00",
              },
              {
                title: "Skill Orchestration",
                desc: "Decentralized skills with own auth. Borrows free-tier access from specialized agents via find-skills.",
                icon: Layers,
                color: "#00F0FF",
              },
              {
                title: "Gateway Unification",
                desc: "Single gateway stitching credentials. Seamless experience mixing Kiro + Claude + OpenCode APIs.",
                icon: Server,
                color: "#A855F7",
              },
            ].map((approach) => (
              <div
                key={approach.title}
                className="glass rounded-xl p-5 text-center group hover:scale-[1.02] transition-all duration-300 cursor-default"
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-4 transition-transform group-hover:scale-110"
                  style={{ backgroundColor: `${approach.color}12` }}
                >
                  <approach.icon
                    className="w-5 h-5"
                    style={{ color: approach.color }}
                  />
                </div>
                <h4 className="font-bold text-sm mb-2">{approach.title}</h4>
                <p className="text-[12px] text-muted-foreground leading-relaxed">
                  {approach.desc}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   WALKTHROUGH
   ═══════════════════════════════════════════════════════════ */

function WalkthroughSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const INSTALL_STEPS = useMemo(
    () => [
      { text: "[1/8] Installing system dependencies...", pct: 12 },
      { text: "[2/8] Creating directory structure...", pct: 25 },
      { text: "[3/8] Setting up Python virtual environment...", pct: 37 },
      { text: "[4/8] Deploying core Python scripts...", pct: 50 },
      { text: "[5/8] Configuring Kiro ecosystem...", pct: 62 },
      { text: "[6/8] Installing systemd services...", pct: 75 },
      { text: "[7/8] Injecting OpenCode configuration...", pct: 87 },
      { text: "[8/8] Writing enrichment config...", pct: 100 },
    ],
    []
  );

  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setIsRunning(false);
          return 100;
        }
        return prev + 1.5;
      });
    }, 60);
    return () => clearInterval(interval);
  }, [isRunning]);

  const handleSimulate = () => {
    if (isRunning) {
      setIsRunning(false);
    } else {
      setProgress(0);
      setIsRunning(true);
    }
  };

  return (
    <AnimatedSection id="walkthrough" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div variants={fadeUp} className="text-center mb-10 sm:mb-14">
          <SectionBadge color="#A855F7">
            <Rocket className="w-3 h-3 mr-1.5" />
            Walkthrough
          </SectionBadge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Up in <span className="text-gradient-pink">4 Steps</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base leading-relaxed">
            From zero to unified AI gateway in under 5 minutes.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Steps Timeline */}
          <div className="lg:col-span-3">
            <motion.div variants={stagger} className="space-y-3">
              {WALKTHROUGH_STEPS.map((step, i) => (
                <motion.div key={step.step} variants={fadeUp}>
                  <div
                    className={`glass rounded-xl cursor-pointer transition-all duration-300 overflow-hidden ${
                      activeStep === i
                        ? "ring-1 scale-[1.005]"
                        : "hover:scale-[1.005]"
                    }`}
                    style={
                      activeStep === i
                        ? { borderColor: `${step.color}30`, boxShadow: `0 0 30px ${step.color}08` }
                        : undefined
                    }
                    onClick={() => setActiveStep(i)}
                  >
                    <div className="p-4 sm:p-5">
                      <div className="flex items-start gap-4">
                        {/* Step indicator */}
                        <div className="flex flex-col items-center gap-1.5">
                          <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 font-black text-sm transition-all"
                            style={{
                              backgroundColor:
                                activeStep === i
                                  ? `${step.color}18`
                                  : "rgba(255,255,255,0.04)",
                              color: activeStep === i ? step.color : "#6B6B85",
                            }}
                          >
                            {step.step}
                          </div>
                          {i < WALKTHROUGH_STEPS.length - 1 && (
                            <div
                              className="w-[2px] h-4 rounded-full"
                              style={{
                                backgroundColor:
                                  activeStep === i
                                    ? `${step.color}30`
                                    : "rgba(255,255,255,0.06)",
                              }}
                            />
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <step.icon
                              className="w-4 h-4"
                              style={{ color: step.color }}
                            />
                            <h3 className="font-bold text-[15px]">{step.title}</h3>
                          </div>
                          <p className="text-[13px] text-muted-foreground mb-3 leading-relaxed">
                            {step.desc}
                          </p>
                          <TerminalBlock code={step.command} title={`step-${step.step}`} />
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>

          {/* Installation Simulator */}
          <div className="lg:col-span-2">
            <motion.div variants={scaleIn} className="sticky top-20">
              <div className="glass rounded-xl overflow-hidden">
                {/* Terminal header */}
                <div className="px-4 py-3 border-b border-owl-border/40 bg-white/[0.02]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-[#FF5F57]/60" />
                        <span className="w-2.5 h-2.5 rounded-full bg-[#FEBC2E]/60" />
                        <span className="w-2.5 h-2.5 rounded-full bg-[#28C840]/60" />
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground/50 ml-1">
                        owl-install
                      </span>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[11px] text-muted-foreground hover:text-foreground px-2"
                      onClick={handleSimulate}
                    >
                      {isRunning ? (
                        <Pause className="w-3 h-3 mr-1" />
                      ) : (
                        <Play className="w-3 h-3 mr-1" />
                      )}
                      {isRunning ? "Pause" : progress === 100 ? "Reset" : "Run"}
                    </Button>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="px-4 pt-3">
                  <Progress
                    value={progress}
                    className="h-1.5 bg-white/[0.04]"
                  />
                </div>

                {/* Terminal output */}
                <div className="p-4 min-h-[280px] max-h-[340px] overflow-y-auto">
                  <div className="space-y-1.5 font-mono text-[12px]">
                    {INSTALL_STEPS.map((line, idx) => {
                      const isDone = progress >= line.pct;
                      const isCurrent =
                        progress >= line.pct - 12.5 && progress < line.pct;
                      return (
                        <motion.div
                          key={line.text}
                          initial={{ opacity: 0, x: -10 }}
                          animate={
                            isDone || isCurrent
                              ? { opacity: 1, x: 0 }
                              : { opacity: 0.2, x: 0 }
                          }
                          transition={{ duration: 0.2 }}
                          className="flex items-center gap-2"
                        >
                          {isDone ? (
                            <Check className="w-3 h-3 text-owl-green shrink-0" />
                          ) : isCurrent ? (
                            <motion.div
                              animate={{ opacity: [1, 0.3, 1] }}
                              transition={{ duration: 0.8, repeat: Infinity }}
                            >
                              <Clock className="w-3 h-3 text-owl-amber shrink-0" />
                            </motion.div>
                          ) : (
                            <Clock className="w-3 h-3 text-muted-foreground/30 shrink-0" />
                          )}
                          <span
                            className={
                              isDone
                                ? "text-owl-green/80"
                                : isCurrent
                                ? "text-owl-amber/80"
                                : "text-muted-foreground/30"
                            }
                          >
                            {line.text}
                          </span>
                        </motion.div>
                      );
                    })}

                    {/* Cursor */}
                    {isRunning && (
                      <span className="text-owl-lime cursor-blink">▊</span>
                    )}
                  </div>

                  {/* Completion message */}
                  {progress === 100 && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-4 p-3 rounded-lg bg-owl-green/[0.08] border border-owl-green/15"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-owl-green" />
                        <span className="text-[13px] font-bold text-owl-green">
                          Installation Complete!
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground mt-1 ml-6">
                        Forward Proxy :60000 · Kiro Gateway :8333 · MCP Active
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   KNOWLEDGE BASE
   ═══════════════════════════════════════════════════════════ */

function KnowledgeSection() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredFaq = useMemo(
    () =>
      FAQ_ITEMS.filter(
        (item) =>
          item.q.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.a.toLowerCase().includes(searchQuery.toLowerCase())
      ),
    [searchQuery]
  );

  return (
    <AnimatedSection id="knowledge" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-15" />
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div variants={fadeUp} className="text-center mb-10 sm:mb-14">
          <SectionBadge color="#FFB800">
            <BookOpen className="w-3 h-3 mr-1.5" />
            Knowledge Base
          </SectionBadge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Know Your <span className="text-gradient-lime">Stack</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-lg mx-auto text-sm sm:text-base leading-relaxed">
            Operating principles, skills, FAQ, and everything you need to master
            the ecosystem.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* Left column: Protocol + Skills */}
          <div className="lg:col-span-2 space-y-5">
            {/* Operating Protocol */}
            <motion.div variants={slideInLeft}>
              <div className="glass rounded-xl p-5">
                <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                  <Eye className="w-4 h-4 text-owl-lime" />
                  Operating Protocol
                </h3>
                <div className="space-y-2.5">
                  {[
                    {
                      name: "Silent Protocol",
                      desc: "Diagnose actual need before responding. Speed vs Depth routing.",
                      color: "#BFFF00",
                      icon: Eye,
                    },
                    {
                      name: "Depth-Seeking Mode",
                      desc: "Recursively drill to foundations. Why beneath what.",
                      color: "#00F0FF",
                      icon: Search,
                    },
                    {
                      name: "Compounding Editions",
                      desc: "Build on existing work. 1+1=3 through integration.",
                      color: "#A855F7",
                      icon: Layers,
                    },
                  ].map((protocol) => (
                    <div
                      key={protocol.name}
                      className="p-3 rounded-lg bg-white/[0.02] border border-owl-border/30 hover:border-owl-border/50 transition-colors group cursor-default"
                    >
                      <div className="flex items-center gap-2.5 mb-1">
                        <protocol.icon
                          className="w-3.5 h-3.5 transition-transform group-hover:scale-110"
                          style={{ color: protocol.color }}
                        />
                        <span className="font-bold text-[13px]">
                          {protocol.name}
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground pl-6 leading-relaxed">
                        {protocol.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Skills Grid */}
            <motion.div variants={slideInLeft}>
              <div className="glass rounded-xl p-5">
                <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                  <Command className="w-4 h-4 text-owl-cyan" />
                  Agent Skills
                </h3>
                <ScrollArea className="h-[300px]">
                  <div className="grid grid-cols-2 gap-2">
                    {SKILL_CARDS.map((skill) => (
                      <div
                        key={skill.name}
                        className="p-2.5 rounded-lg bg-white/[0.02] border border-owl-border/30 hover:border-owl-border/50 transition-all group cursor-default"
                      >
                        <skill.icon
                          className="w-4 h-4 mb-1.5 transition-transform group-hover:scale-110"
                          style={{ color: skill.color }}
                        />
                        <h4 className="font-bold text-[11px] mb-0.5 leading-tight">
                          {skill.name}
                        </h4>
                        <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2">
                          {skill.desc}
                        </p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </motion.div>
          </div>

          {/* Right column: FAQ + Ports + Commands */}
          <div className="lg:col-span-3 space-y-5">
            {/* FAQ */}
            <motion.div variants={slideInRight}>
              <div className="glass rounded-xl overflow-hidden">
                <div className="p-5 border-b border-owl-border/30">
                  <h3 className="text-sm font-bold flex items-center gap-2 mb-3">
                    <BookOpen className="w-4 h-4 text-owl-amber" />
                    Frequently Asked Questions
                  </h3>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/50" />
                    <input
                      type="text"
                      placeholder="Search questions..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full h-9 pl-9 pr-3 rounded-lg bg-white/[0.04] border border-owl-border/40 text-[13px] placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-owl-lime/25 transition-all"
                    />
                  </div>
                </div>
                <div className="p-2">
                  <Accordion type="single" collapsible className="w-full">
                    {filteredFaq.map((item, i) => (
                      <AccordionItem
                        key={i}
                        value={`faq-${i}`}
                        className="border-owl-border/30"
                      >
                        <AccordionTrigger className="text-[13px] font-medium text-left hover:text-owl-lime transition-colors px-3 py-2.5">
                          {item.q}
                        </AccordionTrigger>
                        <AccordionContent className="text-[13px] text-muted-foreground leading-relaxed px-3 pb-3">
                          {item.a}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                  {filteredFaq.length === 0 && (
                    <div className="text-center py-8">
                      <Search className="w-6 h-6 text-muted-foreground/30 mx-auto mb-2" />
                      <p className="text-[13px] text-muted-foreground">
                        No matching questions found.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>

            {/* Ports & Services */}
            <motion.div variants={slideInRight}>
              <div className="glass rounded-xl p-5">
                <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                  <Monitor className="w-4 h-4 text-owl-green" />
                  Ports & Services Reference
                </h3>
                <div className="space-y-2">
                  {[
                    {
                      port: 60000,
                      service: "OWL Forward Proxy",
                      status: "Systemd Active",
                      color: "#00FF88",
                    },
                    {
                      port: 8333,
                      service: "Kiro Gateway",
                      status: "Systemd Active",
                      color: "#BFFF00",
                    },
                    {
                      port: 7890,
                      service: "Upstream Proxy (Mihomo/Clash)",
                      status: "External",
                      color: "#00F0FF",
                    },
                  ].map((svc) => (
                    <div
                      key={svc.port}
                      className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-owl-border/30 group hover:border-owl-border/50 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="font-mono font-black text-lg tracking-tight"
                          style={{ color: svc.color }}
                        >
                          :{svc.port}
                        </span>
                        <div>
                          <p className="font-medium text-[13px]">{svc.service}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {svc.status}
                          </p>
                        </div>
                      </div>
                      <span className="relative flex h-2 w-2">
                        <span
                          className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-60"
                          style={{ backgroundColor: svc.color }}
                        />
                        <span
                          className="relative inline-flex rounded-full h-2 w-2"
                          style={{ backgroundColor: svc.color }}
                        />
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Quick Commands */}
            <motion.div variants={slideInRight}>
              <div className="glass rounded-xl p-5">
                <h3 className="text-sm font-bold flex items-center gap-2 mb-4">
                  <Terminal className="w-4 h-4 text-owl-lime" />
                  Quick Commands
                </h3>
                <div className="space-y-2">
                  {[
                    {
                      label: "Check proxy status",
                      cmd: "systemctl --user status owl-forward-proxy",
                    },
                    {
                      label: "Restart gateway",
                      cmd: "systemctl --user restart kiro-gateway",
                    },
                    {
                      label: "View proxy logs",
                      cmd: "tail -f ~/.owl-agent/logs/forward-proxy.log",
                    },
                    {
                      label: "Test MCP server",
                      cmd: 'echo \'{"jsonrpc":"2.0","id":1,"method":"initialize"}\' | python3 ~/.owl-agent/owl_resilient_mcp.py',
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="p-3 rounded-lg bg-white/[0.02] border border-owl-border/30 group hover:border-owl-border/50 transition-colors"
                    >
                      <p className="text-[11px] font-medium mb-1.5 text-muted-foreground">
                        {item.label}
                      </p>
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-[12px] font-mono text-owl-lime/75 truncate">
                          {item.cmd}
                        </code>
                        <CopyButton text={item.cmd} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   FOOTER
   ═══════════════════════════════════════════════════════════ */

function Footer() {
  return (
    <footer className="border-t border-owl-border/40 py-10 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">🦉</span>
            <span className="font-bold text-sm">OWL-AGENT</span>
            <span className="text-[11px] text-muted-foreground font-mono">
              v6.0
            </span>
          </div>
          <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
            <span>Silent Protocol</span>
            <span className="opacity-30">·</span>
            <span>Depth-Seeking Mode</span>
            <span className="opacity-30">·</span>
            <span>Compounding Editions</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ═══════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════ */

export default function OWLAgentPage() {
  const [activeSection, setActiveSection] = useState("hero");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.3 }
    );
    NAV_ITEMS.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar activeSection={activeSection} />
      <main className="flex-1">
        <HeroSection />
        <DownloadSection />
        <ArchitectureSection />
        <WalkthroughSection />
        <KnowledgeSection />
      </main>
      <Footer />
    </div>
  );
}
