import { Article } from "@/types/article";
import { cn } from "@/lib/utils";
import { MessageSquare, TrendingUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface ArticleListProps {
  articles: Article[];
  selectedArticle: Article | null;
  onSelectArticle: (article: Article) => void;
  isLoading: boolean;
}

const getScoreColor = (score: number) => {
  if (score >= 4.0) return "text-score-high";
  if (score >= 2.5) return "text-score-medium";
  return "text-score-low";
};

const getScoreBg = (score: number) => {
  if (score >= 4.0) return "bg-score-high";
  if (score >= 2.5) return "bg-score-medium";
  return "bg-score-low";
};

const getScoreLabel = (score: number, type: "relevance" | "trust" | "controversy") => {
  if (type === "relevance") {
    if (score >= 4.5) return "Must See";
    if (score >= 3.5) return "Highly Relevant";
    if (score >= 2.5) return "Relevant";
    if (score >= 1.5) return "Somewhat Relevant";
    return "Low Relevance";
  }
  
  if (type === "trust") {
    if (score >= 4.5) return "Highly Trusted";
    if (score >= 3.5) return "Trusted";
    if (score >= 2.5) return "Moderate";
    if (score >= 1.5) return "Questionable";
    return "Unreliable";
  }
  
  // controversy
  if (score >= 4.0) return "Highly Divisive";
  if (score >= 3.0) return "Controversial";
  if (score >= 2.0) return "Some Debate";
  if (score >= 1.0) return "Minor Disagreement";
  return "Consensus";
};

export const ArticleList = ({ articles, selectedArticle, onSelectArticle, isLoading }: ArticleListProps) => {
  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-3 w-24" />
            <div className="flex gap-2">
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-16" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="divide-y divide-border">
      {articles.map((article) => (
        <button
          key={article.id}
          onClick={() => onSelectArticle(article)}
          className={cn(
            "w-full text-left p-4 hover:bg-muted/50 transition-colors",
            selectedArticle?.id === article.id && "bg-muted"
          )}
        >
          <h3 className="font-semibold text-sm leading-snug mb-2 line-clamp-3">
            {article.title}
          </h3>
          
          <div className="text-xs text-muted-foreground mb-3">
            {article.domain}
          </div>

          <div className="flex items-center gap-3 mb-3 text-xs">
            <div className="flex items-center gap-1 text-muted-foreground">
              <TrendingUp className="w-3 h-3" />
              <span className="font-medium">{article.hnScore}</span>
            </div>
            <div className="flex items-center gap-1 text-muted-foreground">
              <MessageSquare className="w-3 h-3" />
              <span className="font-medium">{article.hnComments}</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Relevance</span>
              <div className="flex items-center gap-2">
                <span className={cn("font-semibold", getScoreColor(article.relevanceScore))}>
                  {article.relevanceScore.toFixed(1)}
                </span>
                <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium", getScoreBg(article.relevanceScore))}>
                  {getScoreLabel(article.relevanceScore, "relevance")}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Trust</span>
              <div className="flex items-center gap-2">
                <span className={cn("font-semibold", getScoreColor(article.trustworthinessScore))}>
                  {article.trustworthinessScore.toFixed(1)}
                </span>
                <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium", getScoreBg(article.trustworthinessScore))}>
                  {getScoreLabel(article.trustworthinessScore, "trust")}
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Controversy</span>
              <div className="flex items-center gap-2">
                <span className={cn("font-semibold", getScoreColor(5.0 - article.controversyScore))}>
                  {article.controversyScore.toFixed(1)}
                </span>
                <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-medium", getScoreBg(5.0 - article.controversyScore))}>
                  {getScoreLabel(article.controversyScore, "controversy")}
                </span>
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
};
