import { Article } from "@/types/article";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, MessageSquare, TrendingUp } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface ArticleDetailProps {
  article: Article;
}

const getScoreColor = (score: number) => {
  if (score >= 4.0) return "text-score-high";
  if (score >= 2.5) return "text-score-medium";
  return "text-score-low";
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
  
  if (score >= 4.0) return "Highly Divisive";
  if (score >= 3.0) return "Controversial";
  if (score >= 2.0) return "Some Debate";
  if (score >= 1.0) return "Minor Disagreement";
  return "Consensus";
};

export const ArticleDetail = ({ article }: ArticleDetailProps) => {
  return (
    <div className="p-8 space-y-6 max-w-4xl mx-auto">
      <div className="space-y-4">
        <h1 className="text-3xl font-display font-bold leading-tight">
          {article.title}
        </h1>
        
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="font-medium">{article.domain}</span>
          <div className="flex items-center gap-1">
            <TrendingUp className="w-4 h-4" />
            <span>{article.hnScore} points</span>
          </div>
          <div className="flex items-center gap-1">
            <MessageSquare className="w-4 h-4" />
            <span>{article.hnComments} comments</span>
          </div>
        </div>

        <div className="flex gap-3">
          <Button asChild>
            <a href={article.articleUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="w-4 h-4 mr-2" />
              Read Article
            </a>
          </Button>
          <Button variant="outline" asChild>
            <a href={article.hnUrl} target="_blank" rel="noopener noreferrer">
              View on HN
            </a>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span>Scores</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Relevance</div>
              <div className={`text-3xl font-bold ${getScoreColor(article.relevanceScore)}`}>
                {article.relevanceScore.toFixed(1)}
              </div>
              <Badge variant="outline" className="text-xs">
                {getScoreLabel(article.relevanceScore, "relevance")}
              </Badge>
            </div>
            
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Trustworthiness</div>
              <div className={`text-3xl font-bold ${getScoreColor(article.trustworthinessScore)}`}>
                {article.trustworthinessScore.toFixed(1)}
              </div>
              <Badge variant="outline" className="text-xs">
                {getScoreLabel(article.trustworthinessScore, "trust")}
              </Badge>
            </div>
            
            <div className="space-y-1">
              <div className="text-sm text-muted-foreground">Controversy</div>
              <div className={`text-3xl font-bold ${getScoreColor(5.0 - article.controversyScore)}`}>
                {article.controversyScore.toFixed(1)}
              </div>
              <Badge variant="outline" className="text-xs">
                {getScoreLabel(article.controversyScore, "controversy")}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Article Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose prose-sm max-w-none prose-headings:font-display prose-a:text-primary">
            <ReactMarkdown>{article.summary}</ReactMarkdown>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Comments Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="prose prose-sm max-w-none prose-headings:font-display prose-a:text-primary">
            <ReactMarkdown>{article.commentsSummary}</ReactMarkdown>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
