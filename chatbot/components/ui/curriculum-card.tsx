"use client";

import { memo } from "react";
import { Badge } from "@/components/ui/badge";

interface CurriculumCard {
  week: number | string;
  level: "beginner" | "intermediate" | "advanced";
  title: string;
  description: string;
  duration: string;
  canvas_code_id?: string;
  workflow_json?: unknown;
}

interface CurriculumProps {
  cards: CurriculumCard[];
  description?: string;
}

const levelColors: Record<string, { bg: string; text: string; label: string }> = {
  beginner: { bg: "bg-green-50", text: "text-green-700", label: "초급" },
  intermediate: { bg: "bg-blue-50", text: "text-blue-700", label: "중급" },
  advanced: { bg: "bg-purple-50", text: "text-purple-700", label: "고급" },
};

export const CurriculumRenderer = memo(({ cards, description }: CurriculumProps) => {
  if (!Array.isArray(cards) || cards.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 my-4">
      {description && (
        <p className="text-sm text-muted-foreground mb-6">{description}</p>
      )}

      <div className="grid gap-3">
        {cards.map((card, idx) => {
          const colors =
            levelColors[card.level] || levelColors.beginner;

          return (
            <div
              key={idx}
              className={`${colors.bg} border border-gray-200 rounded-lg p-4 transition-all hover:shadow-sm`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-semibold text-sm">{card.title}</h3>
                    <Badge
                      variant="secondary"
                      className={`text-xs ${colors.text} bg-transparent border-current`}
                    >
                      {card.level === "beginner"
                        ? "입문"
                        : card.level === "intermediate"
                          ? "중급"
                          : "고급"}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed mb-3">
                    {card.description}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <span>📅 {card.week}주차</span>
                    <span>⏱️ {card.duration}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

CurriculumRenderer.displayName = "CurriculumRenderer";
