import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "@/components/dashboard/Header";
import { ArticleList } from "@/components/dashboard/ArticleList";
import { ArticleDetail } from "@/components/dashboard/ArticleDetail";
import { ChatPanel } from "@/components/dashboard/ChatPanel";
import { Article } from "@/types/article";
import { apiFetch } from "@/lib/api";
import { handleAPIResponse, getErrorMessage, APIError } from "@/lib/apiErrors";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/hooks/use-toast";

const Dashboard = () => {
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchArticles = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await apiFetch("/articles/");
        const data = await handleAPIResponse(response);

        setArticles(data);

        // Auto-select first article if available
        if (data.length > 0 && !selectedArticle) {
          setSelectedArticle(data[0]);
        }
      } catch (err) {
        const errorMessage = getErrorMessage(err);
        setError(errorMessage);

        // Show toast for auth errors, redirect to login
        if (err instanceof APIError && err.statusCode === 401) {
          toast({
            title: "Session Expired",
            description: "Please log in again.",
            variant: "destructive",
          });
          setTimeout(() => navigate('/auth'), 2000);
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchArticles();
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 flex overflow-hidden">
        {/* Article List - Left Pane */}
        <div className="w-80 border-r border-border bg-card overflow-y-auto">
          {error ? (
            <ErrorState
              title="Failed to load articles"
              message={error}
              onRetry={() => window.location.reload()}
            />
          ) : articles.length === 0 && !isLoading ? (
            <EmptyState
              title="No articles yet"
              message="Check back later for curated articles based on your interests. You can update your preferences in your profile."
              actionLabel="Update Preferences"
              onAction={() => navigate('/profile')}
            />
          ) : (
            <ArticleList
              articles={articles}
              selectedArticle={selectedArticle}
              onSelectArticle={setSelectedArticle}
              isLoading={isLoading}
            />
          )}
        </div>

        {/* Article Detail - Middle Pane */}
        <div className="flex-1 overflow-y-auto bg-background">
          {selectedArticle ? (
            <ArticleDetail article={selectedArticle} />
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground">
              Select an article to view details
            </div>
          )}
        </div>

        {/* Chat Panel - Right Pane */}
        <div className="w-96 border-l border-border bg-card">
          {selectedArticle ? (
            <ChatPanel articleId={selectedArticle.id} />
          ) : (
            <div className="h-full flex items-center justify-center text-muted-foreground p-4 text-center">
              Select an article to chat about it
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
