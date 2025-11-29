import { Category } from "@/types/article";
import { Card } from "@/components/ui/card";
import { Check, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface CategorySelectorProps {
  categories: Category[];
  selectedSlugs: string[];
  onToggle: (slug: string) => void;
  isLoading?: boolean;
}

export const CategorySelector = ({
  categories,
  selectedSlugs,
  onToggle,
  isLoading = false,
}: CategorySelectorProps) => {
  if (isLoading) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Loading categories...
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {categories.map((category) => {
        const isSelected = selectedSlugs.includes(category.slug);

        return (
          <Card
            key={category.slug}
            className={cn(
              "relative cursor-pointer transition-all hover:shadow-md",
              "border-2 hover:border-primary/50",
              isSelected && "border-primary bg-primary/5"
            )}
            onClick={() => onToggle(category.slug)}
          >
            <div className="p-4 space-y-3">
              {/* Icon and selection indicator */}
              <div className="flex items-start justify-between">
                <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                  <Sparkles className="w-5 h-5 text-muted-foreground" />
                </div>
                {isSelected && (
                  <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                    <Check className="w-4 h-4 text-primary-foreground" />
                  </div>
                )}
              </div>

              {/* Category title */}
              <div>
                <h3 className="font-semibold text-base leading-tight">
                  {category.title}
                </h3>
              </div>

              {/* Category description */}
              <p className="text-sm text-muted-foreground line-clamp-2">
                {category.description}
              </p>
            </div>
          </Card>
        );
      })}
    </div>
  );
};
