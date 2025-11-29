import { useState, useEffect } from "react";
import { Header } from "@/components/dashboard/Header";
import { ArticleList } from "@/components/dashboard/ArticleList";
import { ArticleDetail } from "@/components/dashboard/ArticleDetail";
import { ChatPanel } from "@/components/dashboard/ChatPanel";
import { Article } from "@/types/article";
import { mockArticles } from "@/data/mockArticles";
import { apiFetch } from "@/lib/api";

const Dashboard = () => {
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchArticles = async () => {
      try {
        const response = await apiFetch("/articles/");

        if (response.ok) {
          const data = await response.json();
          setArticles(data);
        } else {
          // Use mock data for demo
          setArticles(mockArticles);
        }
      } catch (error) {
        // Use mock data for demo
        setArticles(mockArticles);
      } finally {
        setIsLoading(false);
      }
    };

    fetchArticles();

    // Auto-select first article
    if (mockArticles.length > 0 && !selectedArticle) {
      setSelectedArticle(mockArticles[0]);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 flex overflow-hidden">
        {/* Article List - Left Pane */}
        <div className="w-80 border-r border-border bg-card overflow-y-auto">
          <ArticleList
            articles={articles}
            selectedArticle={selectedArticle}
            onSelectArticle={setSelectedArticle}
            isLoading={isLoading}
          />
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
