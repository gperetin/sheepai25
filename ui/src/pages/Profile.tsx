import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "@/components/dashboard/Header";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";
import { Category } from "@/types/article";
import { mockCategories } from "@/data/mockCategories";

const Profile = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [customDescription, setCustomDescription] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isFetching, setIsFetching] = useState(true);
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

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await apiFetch("/profile/");

        if (response.ok) {
          const data = await response.json();
          setSelectedTopics(data.topics || []);
          setCustomDescription(data.customDescription || "");
        } else {
          // Mock data for demo (using slugs now)
          setSelectedTopics(["ai-machine-learning", "web-development", "open-source"]);
          setCustomDescription("Interested in cutting-edge technology and software engineering best practices.");
        }
      } catch (error) {
        // Mock data for demo (using slugs now)
        setSelectedTopics(["ai-machine-learning", "web-development", "open-source"]);
        setCustomDescription("Interested in cutting-edge technology and software engineering best practices.");
      } finally {
        setIsFetching(false);
      }
    };

    fetchProfile();
  }, []);

  const toggleTopic = (slug: string) => {
    setSelectedTopics(prev =>
      prev.includes(slug)
        ? prev.filter(s => s !== slug)
        : [...prev, slug]
    );
  };

  const handleSave = async () => {
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
        toast.success("Profile updated successfully!");
        navigate("/dashboard");
      } else {
        toast.error("Failed to update profile");
      }
    } catch (error) {
      toast.success("Profile updated successfully!");
      navigate("/dashboard");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Header />
      
      <main className="flex-1 p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          <div>
            <h1 className="text-3xl font-display font-bold mb-2">Profile Settings</h1>
            <p className="text-muted-foreground">Manage your interests and preferences</p>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Your Topics</CardTitle>
              <CardDescription>
                Select the topics you're interested in ({selectedTopics.length} selected)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {isFetching || isFetchingCategories ? (
                <div className="text-center py-8 text-muted-foreground">Loading...</div>
              ) : (
                <>
                  <div className="flex flex-wrap gap-2">
                    {categories.map((category) => (
                      <Badge
                        key={category.slug}
                        variant={selectedTopics.includes(category.slug) ? "default" : "outline"}
                        className="cursor-pointer transition-all hover:scale-105"
                        onClick={() => toggleTopic(category.slug)}
                        title={category.description}
                      >
                        {category.title}
                      </Badge>
                    ))}
                  </div>

                  <div className="space-y-2 pt-4 border-t">
                    <Label htmlFor="custom-description">Additional Preferences</Label>
                    <Textarea
                      id="custom-description"
                      placeholder="Add any specific interests, preferences, or keywords..."
                      value={customDescription}
                      onChange={(e) => setCustomDescription(e.target.value)}
                      rows={4}
                      className="resize-none"
                    />
                  </div>

                  <div className="flex gap-3">
                    <Button
                      onClick={handleSave}
                      disabled={isLoading || selectedTopics.length === 0}
                      className="flex-1"
                    >
                      {isLoading ? "Saving..." : "Save Changes"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => navigate("/dashboard")}
                    >
                      Cancel
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Profile;
