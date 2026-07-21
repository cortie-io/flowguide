import { generateDummyPassword } from "./db/utils";

export const isProductionEnvironment = process.env.NODE_ENV === "production";
export const isDevelopmentEnvironment = process.env.NODE_ENV === "development";
export const isTestEnvironment = Boolean(
  process.env.PLAYWRIGHT_TEST_BASE_URL ||
    process.env.PLAYWRIGHT ||
    process.env.CI_PLAYWRIGHT
);

export const DUMMY_PASSWORD = generateDummyPassword();

export const suggestions = [
  "n8n 입문 커리큘럼 로드맵을 만들어줘",
  "HTTP Request 노드로 외부 API를 호출하는 방법 알려줘",
  "Webhook 트리거와 Schedule 트리거의 차이점은 뭐야?",
  "이 에러 메시지를 분석하고 해결 방법을 알려줘",
];
