import { Article } from "@/types/article";

export const mockArticles: Article[] = [
  {
    id: "1",
    title: "New Breakthrough in Quantum Computing Could Revolutionize Cryptography",
    domain: "quantumtech.com",
    hnScore: 842,
    hnComments: 234,
    relevanceScore: 4.8,
    trustworthinessScore: 4.5,
    controversyScore: 2.1,
    summary: "Researchers at MIT have achieved a significant breakthrough in quantum computing that could fundamentally change how we approach cryptographic security. The team developed a novel quantum error correction technique that maintains coherence for unprecedented durations, bringing practical quantum computers closer to reality.\n\nThe new approach combines **topological quantum computing** with dynamic error correction, achieving error rates below the threshold needed for fault-tolerant quantum computation. This advancement addresses one of the primary obstacles preventing quantum computers from solving real-world problems at scale.",
    commentsSummary: "The HN community is cautiously optimistic about this development. Several commenters with quantum computing backgrounds note that while the results are impressive, **significant engineering challenges remain**. \n\nKey concerns raised:\n- Scalability to larger qubit systems\n- Temperature requirements and practical deployment\n- Timeline to commercial applications\n\nSome skeptics point out similar announcements in the past that didn't materialize, while supporters argue this research represents genuine incremental progress rather than hype.",
    articleUrl: "https://quantumtech.com/breakthrough-2024",
    hnUrl: "https://news.ycombinator.com/item?id=39876543"
  },
  {
    id: "2",
    title: "Show HN: I Built a Privacy-First Analytics Platform in Rust",
    domain: "github.com",
    hnScore: 1243,
    hnComments: 412,
    relevanceScore: 4.5,
    trustworthinessScore: 4.9,
    controversyScore: 1.2,
    summary: "A solo developer has released **PrivyMetrics**, an open-source web analytics platform built entirely in Rust. The project aims to provide website owners with detailed insights while respecting user privacy and complying with GDPR without requiring cookie consent banners.\n\nKey features include:\n- Zero personal data collection\n- Real-time analytics with sub-second latency\n- Self-hosted deployment in under 5 minutes\n- Built-in data retention controls\n- Lightweight JavaScript snippet (<2KB)\n\nThe developer reports serving 50M+ page views monthly on a single modest VPS, highlighting Rust's performance benefits for this use case.",
    commentsSummary: "Strong positive reception from the HN community. Many users express interest in migrating from Google Analytics.\n\n**Common themes:**\n- Appreciation for the privacy-first approach\n- Interest in the technical architecture and performance characteristics\n- Questions about integration with existing infrastructure\n- Requests for additional features (A/B testing, funnel analysis)\n\nA few commenters raise questions about sustainability and long-term maintenance for a solo-developed project, though the developer has committed to keeping it open source regardless of commercial success.",
    articleUrl: "https://github.com/example/privymetrics",
    hnUrl: "https://news.ycombinator.com/item?id=39876544"
  },
  {
    id: "3",
    title: "The Death of the Third-Party Cookie: What Developers Need to Know",
    domain: "techcrunch.com",
    hnScore: 567,
    hnComments: 178,
    relevanceScore: 3.9,
    trustworthinessScore: 4.2,
    controversyScore: 3.8,
    summary: "With Google's latest announcement pushing third-party cookie deprecation to 2025, developers and businesses are scrambling to adapt their tracking and advertising strategies. This comprehensive guide explores the alternatives and their implications.\n\n**Key alternatives discussed:**\n1. First-party data strategies\n2. Google's Privacy Sandbox APIs\n3. Server-side tracking solutions\n4. Contextual advertising renaissance\n\nThe article notes that while the delay provides more preparation time, companies that haven't started planning are already behind. Privacy regulations continue to evolve globally, making future-proof solutions critical.",
    commentsSummary: "**Highly divisive discussion** with strong opinions on all sides.\n\nPrivacy advocates celebrate the change as long overdue, citing surveillance capitalism concerns. Some call for even more aggressive privacy protections.\n\nAd tech professionals express frustration with:\n- Lack of viable alternatives that maintain revenue\n- Google's dominant position in defining replacements\n- Inconsistent browser support for new standards\n\nSmall publishers worry about revenue impacts, with several sharing declining ad income data. There's skepticism about whether Privacy Sandbox truly protects privacy or simply consolidates Google's control over digital advertising.",
    articleUrl: "https://techcrunch.com/cookie-death-guide",
    hnUrl: "https://news.ycombinator.com/item?id=39876545"
  }
];
