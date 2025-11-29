import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { Zap } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Category } from "@/types/article";
import { mockCategories } from "@/data/mockCategories";
import { CategorySelector } from "@/components/CategorySelector";

const Onboarding = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [customDescription, setCustomDescription] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingCategories, setIsFetchingCategories] = useState(true);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const response = await apiFetch("/categories/");
        if (response.ok) {
          const data = await response.json();
          setCategories(data);
        } else {
          setCategories(mockCategories);
        }
      } catch (error) {
        setCategories(mockCategories);
      } finally {
        setIsFetchingCategories(false);
      }
    };
    fetchCategories();
  }, []);

  const toggleTopic = (slug: string) => {
    setSelectedTopics(prev =>
      prev.includes(slug)
        ? prev.filter(s => s !== slug)
        : [...prev, slug]
    );
  };

  const handleComplete = async () => {
    if (selectedTopics.length === 0) {
      toast.error("Please select at least one topic");
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiFetch("/profile/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topics: selectedTopics,
          customDescription
        }),
      });

      if (response.ok) {
        toast.success("Profile set up successfully!");
        navigate("/dashboard");
      } else {
        toast.error("Failed to save preferences");
      }
    } catch (error) {
      // Mock success for UI demo
      toast.success("Profile set up successfully!");
      navigate("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="w-6 h-6 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-display font-bold text-foreground">FTL News</h1>
          </div>
          <h2 className="text-2xl font-display font-bold">Choose Your Interests</h2>
          <p className="text-muted-foreground">Select topics you want to follow and we'll personalize your feed</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Select Topics</CardTitle>
            <CardDescription>Choose the areas you're most interested in ({selectedTopics.length} selected)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <CategorySelector
              categories={categories}
              selectedSlugs={selectedTopics}
              onToggle={toggleTopic}
              isLoading={isFetchingCategories}
            />

            <div className="space-y-2 pt-4 border-t">
              <Label htmlFor="custom-description">Tell us more (optional)</Label>
              <Textarea
                id="custom-description"
                placeholder="Add any specific interests, preferences, or keywords that will help us find the most relevant articles for you..."
                value={customDescription}
                onChange={(e) => setCustomDescription(e.target.value)}
                rows={4}
                className="resize-none"
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button
              onClick={handleComplete}
              disabled={isLoading || selectedTopics.length === 0}
              className="w-full"
            >
              {isLoading ? "Saving preferences..." : "Complete Setup"}
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
};

export default Onboarding;
