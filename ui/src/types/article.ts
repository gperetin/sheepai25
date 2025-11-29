export interface Article {
  id: string;
  title: string;
  domain: string;
  hnScore: number;
  hnComments: number;
  relevanceScore: number;
  trustworthinessScore: number;
  controversyScore: number;
  summary: string;
  commentsSummary: string;
  articleUrl: string;
  hnUrl: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export interface Category {
  slug: string;
  title: string;
  description: string;
}
