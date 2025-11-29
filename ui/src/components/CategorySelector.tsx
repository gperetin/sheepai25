import { Category } from "@/types/article";
import { Card } from "@/components/ui/card";
import {
  Check,
  Sparkles,
  Bot,
  Code,
  GitBranch,
  Globe,
  Users,
  Monitor,
  ShieldAlert,
  Bug,
  Lock,
  Building2,
  Briefcase,
  Rocket,
  Copyright,
  Cpu,
  Smartphone,
  Orbit,
  Atom,
  HeartPulse,
  Sigma,
  Scale,
  Earth,
  Train,
  Leaf,
  Flower2,
  Gamepad2,
  Palette,
  History,
  Hammer,
  MessageCircleQuestion,
  LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

const categoryIcons: Record<string, LucideIcon> = {
  "generative-ai-models": Sparkles,
  "ai-tools-applications": Bot,
  "programming-languages": Code,
  "software-engineering-devops": GitBranch,
  "web-development-browsers": Globe,
  "open-source-community": Users,
  "operating-systems": Monitor,
  "cybersecurity-incidents": ShieldAlert,
  "hacking-security-research": Bug,
  "privacy-encryption": Lock,
  "big-tech-corporate-news": Building2,
  "work-career-management": Briefcase,
  "startups-venture-capital": Rocket,
  "media-copyright-content": Copyright,
  "semiconductors-chips": Cpu,
  "consumer-electronics": Smartphone,
  "space-exploration": Orbit,
  "physics-materials": Atom,
  "health-biotech-medicine": HeartPulse,
  "mathematics-theory": Sigma,
  "law-policy-regulation": Scale,
  "geopolitics-global-affairs": Earth,
  "transportation-infrastructure": Train,
  "environment-energy": Leaf,
  "obituaries": Flower2,
  "gaming-game-dev": Gamepad2,
  "graphics-design-ui-ux": Palette,
  "retro-computing-history": History,
  "show-hn-projects": Hammer,
  "ask-hn-community-meta": MessageCircleQuestion,
};

const getCategoryIcon = (slug: string): LucideIcon => {
  return categoryIcons[slug] || Sparkles;
};

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
        const Icon = getCategoryIcon(category.slug);

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
                  <Icon className="w-5 h-5 text-muted-foreground" />
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
