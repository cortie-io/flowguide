import nodeIconData from "@/lib/data/node-icons.json";

type NodeIconEntry = {
  displayName: string;
  icon: string | null;
};

const NODE_ICON_BY_FULL_TYPE = nodeIconData as Record<string, NodeIconEntry>;

// 표시 이름(예: "HTTP Request")으로 아이콘을 찾기 위한 역방향 인덱스.
// 여러 노드가 같은 표시 이름을 가리킬 일은 없으므로 1:1로 매핑된다.
// 긴 이름이 짧은 이름의 부분 문자열인 경우(예: "Slack" ⊂ "Slack Trigger")를
// 먼저 매칭시키기 위해 이름 길이 내림차순으로 정렬해둔다.
const DISPLAY_NAME_ENTRIES: Array<{ name: string; icon: string }> = Object.values(
  NODE_ICON_BY_FULL_TYPE
)
  .filter((entry): entry is NodeIconEntry & { icon: string } => !!entry.icon)
  .map((entry) => ({ name: entry.displayName, icon: entry.icon }))
  .sort((a, b) => b.name.length - a.name.length);

/** n8n full type (예: "n8n-nodes-base.slack")로 아이콘 URL을 조회한다. */
export function getNodeIconByType(nodeType: string | undefined | null): string | null {
  if (!nodeType) return null;
  const normalized = nodeType.trim();
  return NODE_ICON_BY_FULL_TYPE[normalized]?.icon ?? null;
}

/**
 * 자유 텍스트(마크다운 헤더, 굵은 글씨 등) 안에서 알려진 n8n 노드 이름을
 * 찾아 아이콘 URL을 반환한다. 가장 먼저 매칭되는(=가장 긴) 이름을 사용한다.
 */
export function findNodeIconInText(text: string): { name: string; icon: string } | null {
  if (!text) return null;
  for (const entry of DISPLAY_NAME_ENTRIES) {
    if (text.includes(entry.name)) {
      return entry;
    }
  }
  return null;
}
