import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Zap, Target, Bell, MessageSquare, ArrowRight } from "lucide-react";

const Index = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect if already logged in
    const token = localStorage.getItem("authToken");
    if (token) {
      navigate("/dashboard");
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-surface to-muted">
      <header className="border-b border-border/50 bg-card/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-display font-bold">FTL News</span>
          </div>
          <Button onClick={() => navigate("/auth")}>
            Get Started
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl md:text-6xl font-display font-bold leading-tight">
              Never Miss a Story
              <br />
              <span className="text-primary">That Matters to You</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Track Hacker News with intelligent filtering. Get personalized recommendations
              based on your interests, powered by AI analysis.
            </p>
          </div>

          <div className="flex gap-4 justify-center">
            <Button size="lg" onClick={() => navigate("/auth")} className="gap-2">
              Start Tracking
              <ArrowRight className="w-4 h-4" />
            </Button>
            <Button size="lg" variant="outline" onClick={() => navigate("/auth")}>
              Learn More
            </Button>
          </div>

          <div className="grid md:grid-cols-3 gap-8 pt-16">
            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mx-auto">
                <Target className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-display font-bold text-lg">Smart Filtering</h3>
              <p className="text-muted-foreground text-sm">
                Choose your topics and let our AI find the most relevant articles for you
              </p>
            </div>

            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mx-auto">
                <Bell className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-display font-bold text-lg">Relevance Scores</h3>
              <p className="text-muted-foreground text-sm">
                See trustworthiness, controversy, and relevance scores for every article
              </p>
            </div>

            <div className="space-y-3">
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mx-auto">
                <MessageSquare className="w-6 h-6 text-primary" />
              </div>
              <h3 className="font-display font-bold text-lg">AI Chat</h3>
              <p className="text-muted-foreground text-sm">
                Ask questions about any article and get instant, intelligent answers
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Index;
