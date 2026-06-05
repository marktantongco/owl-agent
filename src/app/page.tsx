"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence, useScroll, useTransform, useInView } from "framer-motion";
import {
  Shield, Zap, Globe, Download, ChevronRight, Terminal, ArrowRight,
  Server, Lock, Activity, Layers, Cpu, Wifi, Copy, Check,
  ChevronDown, ExternalLink, FileCode, GitBranch, Settings,
  Monitor, Smartphone, Play, Pause, Box, Eye, BookOpen,
  Command, Database, Network, Rocket, Sparkles, AlertTriangle,
  CheckCircle2, Clock, RefreshCw, Search
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";

/* ═══════════════════════════════════════════════════════════
   DATA
   ═══════════════════════════════════════════════════════════ */

const NAV_ITEMS = [
  { id: "hero", label: "Home" },
  { id: "download", label: "Download" },
  { id: "architecture", label: "Architecture" },
  { id: "walkthrough", label: "Walkthrough" },
  { id: "knowledge", label: "Knowledge Base" },
];

const INSTALLER_FILES = [
  {
    name: "install_owl_unified.sh",
    desc: "Complete unified installer — all components",
    version: "v6.0",
    size: "~45KB",
    icon: Terminal,
    color: "text-owl-lime",
    glowClass: "glow-lime",
    badge: "MAIN",
    badgeColor: "bg-owl-lime/20 text-owl-lime",
  },
  {
    name: "validate_owl.sh",
    desc: "Post-install validation & mock test suite",
    version: "v1.0",
    size: "~12KB",
    icon: CheckCircle2,
    color: "text-owl-cyan",
    glowClass: "glow-cyan",
    badge: "QA",
    badgeColor: "bg-owl-cyan/20 text-owl-cyan",
  },
  {
    name: "forward_proxy.py",
    desc: "HTTP/HTTPS forward proxy with bypass logic",
    version: "v2.0",
    size: "~8KB",
    icon: Network,
    color: "text-owl-violet",
    glowClass: "glow-violet",
    badge: "CORE",
    badgeColor: "bg-owl-violet/20 text-owl-violet",
  },
  {
    name: "proxy_defense_fixed_v3.py",
    desc: "Resilient client with circuit breaker & proxy rotation",
    version: "v3.3",
    size: "~18KB",
    icon: Shield,
    color: "text-owl-pink",
    glowClass: "glow-pink",
    badge: "DEFENSE",
    badgeColor: "bg-owl-pink/20 text-owl-pink",
  },
  {
    name: "owl_resilient_mcp.py",
    desc: "MCP server exposing resilient HTTP tools for AI agents",
    version: "v1.1",
    size: "~22KB",
    icon: Cpu,
    color: "text-owl-amber",
    glowClass: "",
    badge: "MCP",
    badgeColor: "bg-owl-amber/20 text-owl-amber",
  },
  {
    name: "proxy_sources.json",
    desc: "Auto-discovery enrichment proxy source config",
    version: "v1.0",
    size: "~1KB",
    icon: Globe,
    color: "text-owl-green",
    glowClass: "",
    badge: "CONFIG",
    badgeColor: "bg-owl-green/20 text-owl-green",
  },
];

const ARCHITECTURE_LAYERS = [
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

const WALKTHROUGH_STEPS = [
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
    command: 'curl http://localhost:8333/v1/chat/completions \\\n  -H "Authorization: Bearer kiro-gateway-8333" \\\n  -H "Content-Type: application/json" \\\n  -d \'{"model":"auto","messages":[{"role":"user","content":"Hello"}]}\'',
    icon: Sparkles,
    color: "#FF3E9A",
  },
];

const FAQ_ITEMS = [
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

const SKILL_CARDS = [
  { name: "Silent Protocol", desc: "Pre-response diagnostic layer that routes speed vs depth before answering", icon: Eye, color: "#BFFF00" },
  { name: "Depth-Seeking Mode", desc: "Recursive first-principles analysis for complex problems", icon: Search, color: "#00F0FF" },
  { name: "Compounding Editions", desc: "Build upon existing work. Integration over reinvention.", icon: Layers, color: "#A855F7" },
  { name: "Proxy Defense Stack", desc: "5-tier escalation: weighted rotation, circuit breaker, dedup, caching, rate limiting", icon: Shield, color: "#FF3E9A" },
  { name: "MCP Resilient HTTP", desc: "AI agent middleware with cache, circuit breaker, offline queue, validation", icon: Cpu, color: "#FFB800" },
  { name: "find-skills", desc: "Discover and install agent skills from the ecosystem", icon: Command, color: "#00FF88" },
  { name: "7-Agent MASTER Pipeline", desc: "Decision → Simulator → Implementation → Auditor → Profiler → Optimizer → Maintenance", icon: RefreshCw, color: "#BFFF00" },
  { name: "Credential Stitcher", desc: "Pool management and rotation for free-tier credentials across providers", icon: Lock, color: "#00F0FF" },
];

/* ═══════════════════════════════════════════════════════════
   ANIMATION VARIANTS
   ═══════════════════════════════════════════════════════════ */

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 1, 0.36, 1] } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.08 } },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.9 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
};

/* ═══════════════════════════════════════════════════════════
   COMPONENTS
   ═══════════════════════════════════════════════════════════ */

function AnimatedSection({ children, className = "", id = "" }: { children: React.ReactNode; className?: string; id?: string }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
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
    <button onClick={handleCopy} className="p-1.5 rounded-md hover:bg-white/10 transition-colors">
      {copied ? <Check className="w-3.5 h-3.5 text-owl-green" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
    </button>
  );
}

function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  return (
    <div className="relative group rounded-xl bg-black/50 border border-owl-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-owl-border">
        <span className="text-xs font-mono text-muted-foreground">{language}</span>
        <CopyButton text={code} />
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono leading-relaxed">
        <code className="text-owl-lime/90">{code}</code>
      </pre>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   NAV
   ═══════════════════════════════════════════════════════════ */

function Navbar({ activeSection }: { activeSection: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50 glass-strong"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14 sm:h-16">
          <div className="flex items-center gap-2">
            <span className="text-xl sm:text-2xl">🦉</span>
            <span className="font-bold text-base sm:text-lg tracking-tight">OWL-AGENT</span>
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-owl-lime/30 text-owl-lime hidden sm:inline-flex">
              v6.0
            </Badge>
          </div>
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                  activeSection === item.id
                    ? "text-owl-lime bg-owl-lime/10"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                }`}
              >
                {item.label}
              </a>
            ))}
          </div>
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg hover:bg-white/5 transition-colors"
          >
            {mobileOpen ? <ChevronDown className="w-5 h-5" /> : <Command className="w-5 h-5" />}
          </button>
        </div>
      </div>
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-t border-owl-border overflow-hidden"
          >
            <div className="px-4 py-3 space-y-1">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  onClick={() => setMobileOpen(false)}
                  className={`block px-3 py-2 rounded-lg text-sm transition-all ${
                    activeSection === item.id ? "text-owl-lime bg-owl-lime/10" : "text-muted-foreground"
                  }`}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}

/* ═══════════════════════════════════════════════════════════
   HERO
   ═══════════════════════════════════════════════════════════ */

function HeroSection() {
  const [statusDots, setStatusDots] = useState<number[]>([]);
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({ target: containerRef, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], [0, -100]);
  const opacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  useEffect(() => {
    const interval = setInterval(() => {
      setStatusDots(Array.from({ length: 6 }, () => Math.random()));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section ref={containerRef} id="hero" className="relative min-h-screen flex items-center overflow-hidden noise">
      {/* Background effects */}
      <div className="absolute inset-0 dot-grid opacity-40" />
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-owl-lime/5 rounded-full blur-[120px]" />
      <div className="absolute bottom-1/4 -right-32 w-96 h-96 bg-owl-violet/5 rounded-full blur-[120px]" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-owl-cyan/3 rounded-full blur-[200px]" />

      <motion.div style={{ y, opacity }} className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        <div className="flex flex-col items-center text-center">
          {/* Status badge */}
          <motion.div variants={fadeUp} className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-owl-green opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-owl-green" />
            </span>
            <span className="text-xs font-mono text-muted-foreground">v6.0 — ALL SYSTEMS OPERATIONAL</span>
            {statusDots.map((v, i) => (
              <span key={i} className="w-1 h-1 rounded-full bg-owl-lime/50" style={{ opacity: v }} />
            ))}
          </motion.div>

          {/* Main headline */}
          <motion.h1 variants={fadeUp} className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl font-black tracking-tighter leading-[0.9]">
            <span className="block">ONE GATEWAY</span>
            <span className="block text-gradient-lime">ALL AI MODELS</span>
            <span className="block text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold text-muted-foreground mt-2">
              ZERO COST
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p variants={fadeUp} className="mt-6 sm:mt-8 max-w-2xl text-base sm:text-lg text-muted-foreground leading-relaxed px-4">
            The unified free-tier proxy stack for <span className="text-owl-cyan font-medium">Hermes</span>,{" "}
            <span className="text-owl-violet font-medium">Claude</span>,{" "}
            <span className="text-owl-pink font-medium">OpenCode</span> &{" "}
            <span className="text-owl-amber font-medium">Kiro</span>.
            One API endpoint. Intelligent routing. Credential stitching. Resilient by default.
          </motion.p>

          {/* CTA buttons */}
          <motion.div variants={fadeUp} className="flex flex-col sm:flex-row items-center gap-3 mt-8 sm:mt-10">
            <a href="#download">
              <Button
                size="lg"
                className="bg-owl-lime text-owl-dark hover:bg-owl-lime/90 font-bold text-base px-8 h-12 rounded-xl glow-lime transition-all hover:scale-105"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Installer
              </Button>
            </a>
            <a href="#architecture">
              <Button
                size="lg"
                variant="outline"
                className="border-owl-border text-foreground hover:bg-white/5 font-medium text-base px-8 h-12 rounded-xl"
              >
                <Eye className="w-4 h-4 mr-2" />
                View Architecture
              </Button>
            </a>
          </motion.div>

          {/* Quick stats */}
          <motion.div variants={fadeUp} className="grid grid-cols-3 gap-4 sm:gap-8 mt-12 sm:mt-16 w-full max-w-lg">
            {[
              { value: "6", label: "Core Files", color: "text-owl-lime" },
              { value: "5", label: "Arch Layers", color: "text-owl-cyan" },
              { value: "4", label: "AI Providers", color: "text-owl-violet" },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className={`text-2xl sm:text-3xl font-black ${stat.color}`}>{stat.value}</div>
                <div className="text-xs sm:text-sm text-muted-foreground mt-1">{stat.label}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        animate={{ y: [0, 8, 0] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2"
      >
        <ChevronDown className="w-5 h-5 text-muted-foreground/50" />
      </motion.div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════
   DOWNLOAD HUB
   ═══════════════════════════════════════════════════════════ */

function DownloadSection() {
  return (
    <AnimatedSection id="download" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div variants={fadeUp} className="text-center mb-12 sm:mb-16">
          <Badge variant="outline" className="border-owl-lime/30 text-owl-lime mb-4">DOWNLOAD CENTER</Badge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Grab the <span className="text-gradient-lime">Stack</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-sm sm:text-base">
            Every file you need. One command to install. Full validation included.
          </p>
        </motion.div>

        {/* Main installer highlight */}
        <motion.div variants={scaleIn} className="mb-10">
          <Card className="glass glow-lime rounded-2xl overflow-hidden border-owl-lime/20">
            <CardContent className="p-6 sm:p-8">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-xl bg-owl-lime/10 flex items-center justify-center shrink-0">
                    <Terminal className="w-7 h-7 text-owl-lime" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-lg">install_owl_unified.sh</span>
                      <Badge className="bg-owl-lime/20 text-owl-lime text-[10px]">MAIN INSTALLER</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Complete stack: Forward Proxy + Proxy Defense + MCP Server + Kiro Gateway + Systemd + Wrappers
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 w-full sm:w-auto">
                  <CodeBlock code="chmod +x install_owl_unified.sh && ./install_owl_unified.sh" />
                </div>
              </div>
              {/* Feature pills */}
              <div className="flex flex-wrap gap-2 mt-5">
                {["--skip-kiro", "--skip-gateway", "--enrich", "--dry-run"].map((flag) => (
                  <span key={flag} className="px-2.5 py-1 rounded-lg bg-white/5 text-xs font-mono text-muted-foreground border border-owl-border">
                    {flag}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Bento grid of files */}
        <motion.div variants={stagger} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {INSTALLER_FILES.filter((_, i) => i > 0).map((file) => (
            <motion.div key={file.name} variants={scaleIn}>
              <Card className={`glass rounded-xl h-full hover:scale-[1.02] transition-transform duration-300 ${file.glowClass} group`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div className={`w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center ${file.color}`}>
                      <file.icon className="w-5 h-5" />
                    </div>
                    <Badge className={`${file.badgeColor} text-[10px]`}>{file.badge}</Badge>
                  </div>
                  <h3 className="font-bold text-sm mb-1 font-mono">{file.name}</h3>
                  <p className="text-xs text-muted-foreground mb-3">{file.desc}</p>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>{file.version}</span>
                    <span>·</span>
                    <span>{file.size}</span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Install flags guide */}
        <motion.div variants={fadeUp} className="mt-10">
          <Card className="glass rounded-xl">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Settings className="w-4 h-4 text-owl-cyan" />
                CLI Flags Reference
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {[
                  { flag: "--skip-kiro", desc: "Skip kiro-cli native binary download" },
                  { flag: "--skip-gateway", desc: "Skip kiro-gateway setup (no port 8333)" },
                  { flag: "--enrich", desc: "Enable proxy enrichment from auto-discovery sources" },
                  { flag: "--dry-run", desc: "Validate without writing any files" },
                ].map((f) => (
                  <div key={f.flag} className="flex gap-3 items-start">
                    <code className="font-mono text-owl-lime shrink-0">{f.flag}</code>
                    <span className="text-muted-foreground">{f.desc}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   ARCHITECTURE
   ═══════════════════════════════════════════════════════════ */

function ArchitectureSection() {
  return (
    <AnimatedSection id="architecture" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-20" />
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div variants={fadeUp} className="text-center mb-12 sm:mb-16">
          <Badge variant="outline" className="border-owl-cyan/30 text-owl-cyan mb-4">ARCHITECTURE</Badge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            How the <span className="text-gradient-cyan">Magic</span> Works
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-sm sm:text-base">
            Five layers. One pipeline. Zero single points of failure.
          </p>
        </motion.div>

        {/* Architecture layers */}
        <motion.div variants={stagger} className="space-y-4 sm:space-y-6">
          {ARCHITECTURE_LAYERS.map((layer, i) => (
            <motion.div key={layer.title} variants={fadeUp}>
              <Card className="glass rounded-xl overflow-hidden group hover:scale-[1.01] transition-transform duration-300">
                <CardContent className="p-5 sm:p-6">
                  <div className="flex flex-col sm:flex-row items-start gap-4">
                    {/* Layer number + icon */}
                    <div className="flex items-center gap-3">
                      <div
                        className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${layer.color}15` }}
                      >
                        <layer.icon className="w-6 h-6" style={{ color: layer.color }} />
                      </div>
                      <div className="sm:hidden">
                        <span className="text-[10px] font-mono" style={{ color: layer.color }}>
                          LAYER {i + 1}
                        </span>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="hidden sm:inline text-[10px] font-mono" style={{ color: layer.color }}>
                          LAYER {i + 1}
                        </span>
                        <h3 className="font-bold text-base">{layer.title}</h3>
                        <span className="text-xs text-muted-foreground">— {layer.subtitle}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {layer.items.map((item) => (
                          <span
                            key={item}
                            className="px-2.5 py-1 rounded-lg text-xs font-medium border"
                            style={{
                              backgroundColor: `${layer.color}08`,
                              borderColor: `${layer.color}20`,
                              color: layer.color,
                            }}
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Arrow connector (except last) */}
                    {i < ARCHITECTURE_LAYERS.length - 1 && (
                      <div className="hidden sm:flex items-center">
                        <ChevronRight className="w-5 h-5 text-muted-foreground/30" />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Flow diagram */}
        <motion.div variants={fadeUp} className="mt-10">
          <Card className="glass rounded-xl overflow-hidden">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-bold flex items-center gap-2">
                <Activity className="w-4 h-4 text-owl-green" />
                Request Flow
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 text-xs sm:text-sm">
                {[
                  { label: "Client", color: "#F0F0F5" },
                  { label: "→", color: "#8888A0" },
                  { label: "Gateway :8333", color: "#BFFF00" },
                  { label: "→", color: "#8888A0" },
                  { label: "Router", color: "#00F0FF" },
                  { label: "→", color: "#8888A0" },
                  { label: "Creds", color: "#A855F7" },
                  { label: "→", color: "#8888A0" },
                  { label: "Proxy :60000", color: "#00FF88" },
                  { label: "→", color: "#8888A0" },
                  { label: "APIs", color: "#FF3E9A" },
                ].map((item, i) => (
                  <span key={i} className="font-mono font-medium" style={{ color: item.color }}>
                    {item.label}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* 3 Approaches comparison */}
        <motion.div variants={fadeUp} className="mt-10">
          <h3 className="text-lg font-bold mb-4 text-center">Three Approaches, One Unified Stack</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              {
                title: "Proxy Aggregation",
                desc: "Central router, decentralized proxies. Aggregates free-tier limits across providers.",
                icon: Globe,
                color: "#BFFF00",
              },
              {
                title: "Skill Orchestration",
                desc: "Decentralized skills with own auth. Borrows free-tier access from specialized agents.",
                icon: Layers,
                color: "#00F0FF",
              },
              {
                title: "Gateway Unification",
                desc: "Single gateway stitching credentials. Seamless experience mixing Kiro + Claude + OpenCode.",
                icon: Server,
                color: "#A855F7",
              },
            ].map((approach) => (
              <Card key={approach.title} className="glass rounded-xl text-center group hover:scale-[1.02] transition-transform duration-300">
                <CardContent className="p-5">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3"
                    style={{ backgroundColor: `${approach.color}15` }}
                  >
                    <approach.icon className="w-5 h-5" style={{ color: approach.color }} />
                  </div>
                  <h4 className="font-bold text-sm mb-2">{approach.title}</h4>
                  <p className="text-xs text-muted-foreground leading-relaxed">{approach.desc}</p>
                </CardContent>
              </Card>
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

  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          setIsRunning(false);
          return 100;
        }
        return prev + 2;
      });
    }, 80);
    return () => clearInterval(interval);
  }, [isRunning]);

  return (
    <AnimatedSection id="walkthrough" className="py-20 sm:py-28 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div variants={fadeUp} className="text-center mb-12 sm:mb-16">
          <Badge variant="outline" className="border-owl-violet/30 text-owl-violet mb-4">WALKTHROUGH</Badge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Up in <span className="text-gradient-pink">4 Steps</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-sm sm:text-base">
            From zero to unified AI gateway in under 5 minutes.
          </p>
        </motion.div>

        {/* Step timeline */}
        <motion.div variants={stagger} className="space-y-4 sm:space-y-6 max-w-3xl mx-auto">
          {WALKTHROUGH_STEPS.map((step, i) => (
            <motion.div key={step.step} variants={fadeUp}>
              <Card
                className={`glass rounded-xl cursor-pointer transition-all duration-300 ${
                  activeStep === i ? "ring-1 scale-[1.01]" : "hover:scale-[1.005]"
                }`}
                style={{ ringColor: activeStep === i ? step.color : undefined }}
                onClick={() => setActiveStep(i)}
              >
                <CardContent className="p-5 sm:p-6">
                  <div className="flex items-start gap-4">
                    {/* Step number */}
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 font-black text-sm"
                      style={{
                        backgroundColor: activeStep === i ? `${step.color}20` : "rgba(255,255,255,0.05)",
                        color: activeStep === i ? step.color : "#8888A0",
                      }}
                    >
                      {step.step}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <step.icon className="w-4 h-4" style={{ color: step.color }} />
                        <h3 className="font-bold text-base">{step.title}</h3>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{step.desc}</p>
                      <CodeBlock code={step.command} language={i === 3 ? "bash" : "bash"} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>

        {/* Simulation */}
        <motion.div variants={fadeUp} className="mt-10 max-w-3xl mx-auto">
          <Card className="glass rounded-xl">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-4">
                <h4 className="font-bold text-sm flex items-center gap-2">
                  <Play className="w-4 h-4 text-owl-lime" />
                  Installation Simulator
                </h4>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs border-owl-border"
                  onClick={() => {
                    setIsRunning(!isRunning);
                    if (!isRunning) setProgress(0);
                  }}
                >
                  {isRunning ? <Pause className="w-3 h-3 mr-1" /> : <Play className="w-3 h-3 mr-1" />}
                  {isRunning ? "Pause" : "Simulate Install"}
                </Button>
              </div>
              <Progress value={progress} className="h-2 mb-3" />
              <div className="space-y-1 font-mono text-xs text-muted-foreground">
                {[
                  { text: "[1/8] System dependencies", pct: 12 },
                  { text: "[2/8] Directory structure", pct: 25 },
                  { text: "[3/8] Python virtual environment", pct: 37 },
                  { text: "[4/8] Core Python scripts", pct: 50 },
                  { text: "[5/8] Kiro ecosystem", pct: 62 },
                  { text: "[6/8] Systemd services", pct: 75 },
                  { text: "[7/8] OpenCode configuration", pct: 87 },
                  { text: "[8/8] Enrichment config", pct: 100 },
                ].map((line) => (
                  <div key={line.text} className={`flex items-center gap-2 transition-opacity ${progress >= line.pct ? "opacity-100" : "opacity-20"}`}>
                    {progress >= line.pct ? (
                      <Check className="w-3 h-3 text-owl-green shrink-0" />
                    ) : (
                      <Clock className="w-3 h-3 shrink-0" />
                    )}
                    <span>{line.text}</span>
                  </div>
                ))}
              </div>
              {progress === 100 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-3 rounded-lg bg-owl-green/10 border border-owl-green/20"
                >
                  <span className="text-sm font-bold text-owl-green">🦉 Installation Complete!</span>
                  <span className="text-xs text-muted-foreground ml-2">Forward Proxy :60000 · Kiro Gateway :8333 · MCP Active</span>
                </motion.div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AnimatedSection>
  );
}

/* ═══════════════════════════════════════════════════════════
   KNOWLEDGE BASE
   ═══════════════════════════════════════════════════════════ */

function KnowledgeSection() {
  const [searchQuery, setSearchQuery] = useState("");
  const filteredFaq = FAQ_ITEMS.filter(
    (item) =>
      item.q.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.a.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <AnimatedSection id="knowledge" className="py-20 sm:py-28 relative">
      <div className="absolute inset-0 dot-grid opacity-20" />
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div variants={fadeUp} className="text-center mb-12 sm:mb-16">
          <Badge variant="outline" className="border-owl-amber/30 text-owl-amber mb-4">KNOWLEDGE BASE</Badge>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight">
            Know Your <span className="text-gradient-lime">Stack</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-xl mx-auto text-sm sm:text-base">
            Operating principles, skills, FAQ, and everything you need to master the ecosystem.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Left: Skills + Protocol */}
          <div className="lg:col-span-2 space-y-6">
            {/* Operating Protocol */}
            <motion.div variants={fadeUp}>
              <Card className="glass rounded-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Eye className="w-4 h-4 text-owl-lime" />
                    Operating Protocol
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { name: "Silent Protocol", desc: "Diagnose actual need before responding. Speed vs Depth routing.", color: "#BFFF00" },
                    { name: "Depth-Seeking Mode", desc: "Recursively drill to foundations. Why beneath what.", color: "#00F0FF" },
                    { name: "Compounding Editions", desc: "Build on existing work. 1+1=3 through integration.", color: "#A855F7" },
                  ].map((protocol) => (
                    <div key={protocol.name} className="p-3 rounded-lg bg-white/3 border border-owl-border">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: protocol.color }} />
                        <span className="font-bold text-sm">{protocol.name}</span>
                      </div>
                      <p className="text-xs text-muted-foreground pl-4">{protocol.desc}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </motion.div>

            {/* Skills Grid */}
            <motion.div variants={fadeUp}>
              <Card className="glass rounded-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Command className="w-4 h-4 text-owl-cyan" />
                    Agent Skills
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[320px]">
                    <div className="grid grid-cols-2 gap-2">
                      {SKILL_CARDS.map((skill) => (
                        <div
                          key={skill.name}
                          className="p-2.5 rounded-lg bg-white/3 border border-owl-border hover:border-white/10 transition-colors group cursor-default"
                        >
                          <skill.icon
                            className="w-4 h-4 mb-1.5 group-hover:scale-110 transition-transform"
                            style={{ color: skill.color }}
                          />
                          <h4 className="font-bold text-[11px] mb-0.5 leading-tight">{skill.name}</h4>
                          <p className="text-[10px] text-muted-foreground leading-relaxed line-clamp-2">{skill.desc}</p>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Right: FAQ + Ports Reference */}
          <div className="lg:col-span-3 space-y-6">
            {/* FAQ */}
            <motion.div variants={fadeUp}>
              <Card className="glass rounded-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-owl-amber" />
                    Frequently Asked Questions
                  </CardTitle>
                  <div className="relative mt-2">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                      type="text"
                      placeholder="Search questions..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full h-9 pl-9 pr-3 rounded-lg bg-white/5 border border-owl-border text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-owl-lime/30"
                    />
                  </div>
                </CardHeader>
                <CardContent>
                  <Accordion type="single" collapsible className="w-full">
                    {filteredFaq.map((item, i) => (
                      <AccordionItem key={i} value={`faq-${i}`} className="border-owl-border">
                        <AccordionTrigger className="text-sm font-medium text-left hover:text-owl-lime transition-colors">
                          {item.q}
                        </AccordionTrigger>
                        <AccordionContent className="text-sm text-muted-foreground leading-relaxed">
                          {item.a}
                        </AccordionContent>
                      </AccordionItem>
                    ))}
                  </Accordion>
                  {filteredFaq.length === 0 && (
                    <p className="text-center text-sm text-muted-foreground py-6">No matching questions found.</p>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Ports & Services Reference */}
            <motion.div variants={fadeUp}>
              <Card className="glass rounded-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Monitor className="w-4 h-4 text-owl-green" />
                    Ports & Services Reference
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {[
                      { port: 60000, service: "OWL Forward Proxy", status: "Systemd Active", color: "#00FF88" },
                      { port: 8333, service: "Kiro Gateway", status: "Systemd Active", color: "#BFFF00" },
                      { port: 7890, service: "Upstream Proxy (Mihomo/Clash)", status: "External", color: "#00F0FF" },
                    ].map((svc) => (
                      <div key={svc.port} className="flex items-center justify-between p-3 rounded-lg bg-white/3 border border-owl-border">
                        <div className="flex items-center gap-3">
                          <span className="font-mono font-black text-lg" style={{ color: svc.color }}>
                            :{svc.port}
                          </span>
                          <div>
                            <p className="font-medium text-sm">{svc.service}</p>
                            <p className="text-[10px] text-muted-foreground">{svc.status}</p>
                          </div>
                        </div>
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75" style={{ backgroundColor: svc.color }} />
                          <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: svc.color }} />
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Quick Commands */}
            <motion.div variants={fadeUp}>
              <Card className="glass rounded-xl">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-bold flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-owl-lime" />
                    Quick Commands
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { label: "Check proxy status", cmd: "systemctl --user status owl-forward-proxy" },
                    { label: "Restart gateway", cmd: "systemctl --user restart kiro-gateway" },
                    { label: "View proxy logs", cmd: "tail -f ~/.owl-agent/logs/forward-proxy.log" },
                    { label: "Test MCP server", cmd: 'echo \'{"jsonrpc":"2.0","id":1,"method":"initialize"}\' | python3 ~/.owl-agent/owl_resilient_mcp.py' },
                  ].map((item) => (
                    <div key={item.label} className="p-3 rounded-lg bg-white/3 border border-owl-border">
                      <p className="text-xs font-medium mb-1.5 text-muted-foreground">{item.label}</p>
                      <div className="flex items-center justify-between gap-2">
                        <code className="text-xs font-mono text-owl-lime/80 truncate">{item.cmd}</code>
                        <CopyButton text={item.cmd} />
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
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
    <footer className="border-t border-owl-border py-10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🦉</span>
            <span className="font-bold">OWL-AGENT</span>
            <span className="text-xs text-muted-foreground">Unified Synergy Gateway v6.0</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>Built with Silent Protocol + Depth-Seeking Mode</span>
            <span>·</span>
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
    <div className="min-h-screen flex flex-col">
      <Navbar activeSection={activeSection} />
      <main className="flex-1">
        <HeroSection />
        <Separator className="bg-owl-border/50 max-w-7xl mx-auto" />
        <DownloadSection />
        <Separator className="bg-owl-border/50 max-w-7xl mx-auto" />
        <ArchitectureSection />
        <Separator className="bg-owl-border/50 max-w-7xl mx-auto" />
        <WalkthroughSection />
        <Separator className="bg-owl-border/50 max-w-7xl mx-auto" />
        <KnowledgeSection />
      </main>
      <Footer />
    </div>
  );
}
