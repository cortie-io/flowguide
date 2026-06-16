# n8n 업무 자동화 일잘러 되기

> 메이허, 에디 유 지음 | 골든래빗 출판사

---

## 책 소개

매일 반복되는 번거로운 업무를 대신 처리할 존재가 있다면 얼마나 편할까요? n8n이 명쾌한 해답이 될 수 있습니다. n8n은 단 한 번의 클릭만으로, 혹은 별도의 조작 없이도 정해진 규칙에 따라 반복 업무를 자동으로 수행합니다. 이 책은 n8n을 나만의 비서로 다루는 법을 알려줍니다.

복잡할 수 있는 n8n의 노드, 서비스를 연결하기 위한 API 연결도 작은 워크플로부터 만들어가며 차근차근 익혀가면 금세 익숙해질 것입니다. 구글 워크스페이스, 유튜브, 슬랙, 노션, 디스코드, 심지어는 증권사까지—많은 서비스를 연결한 나만의 워크플로로 반복 작업과 작별하세요!

### 이 책의 3가지 포인트

**Point 1. n8n이 처음인 사람을 위한 꼼꼼한 가이드**

누구나 업무 자동화를 시작할 수 있도록, n8n의 기초부터 차근차근 안내하여 자동화의 장벽을 낮췄습니다. 이 책은 노드와 워크플로라는 직관적인 시각적 요소를 통해, 복잡한 코드 없이도 업무 프로세스를 흐름도로 그리듯 설계하는 방법을 상세히 설명합니다. 아주 기초적인 자동화부터 시작해 점차 복잡한 로직을 구현하다 보면, 어느새 자신만의 자동화 시스템을 자유자재로 다루는 모습을 발견하게 될 것입니다.

**Point 2. 매일 쓰는 서비스로 일상에 더 밀접한 워크플로 만들기**

구글, 슬랙, 노션 등 우리가 매일 사용하는 서비스는 물론, 전 세계의 다양한 API를 연결하여 업무의 확장성을 극대화합니다. 매일 아침 미팅 일정을 슬랙으로 알림받거나, 수신된 이메일을 중요도에 따라 자동 분류하는 등 실무에 즉시 적용할 수 있는 구체적인 예제를 직접 만들어봅니다. 흩어져 있던 도구를 하나의 유기적인 시스템으로 연결하는 강력한 경험을 제공합니다.

**Point 3. 알아서 검색하고 결정까지 내리는 AI 활용 워크플로 자동화**

단순한 반복 작업을 넘어, AI가 스스로 판단하고 업무를 처리하는 '진짜 자동화'를 경험할 차례입니다. 챗GPT가 도구를 사용하여 인터넷 정보를 검색하는 AI 에이전트부터, 사내 문서를 뒤져 정확한 답을 주는 RAG 챗봇까지 최신 기술을 직접 구현해봅니다.

---

## 이 책에서 다루는 API 14개

API는 서비스를 서로 이어주는 '연결 통로' 같은 역할을 합니다. 이를 통해 다양한 서비스를 연결해 하나의 자동화된 작업 흐름을 만들 수 있습니다.

| API | 설명 |
|-----|------|
| **API 01 지메일** | 이메일 수신 감지, 자동 답장 및 알림 메일 발송. 특정 조건의 이메일이 도착하면 트리거를 실행하거나 설문 응답자에게 맞춤형 자료를 자동 발송. |
| **API 02 구글 캘린더** | 개인이나 팀의 일정 데이터 관리 및 조회. 매일 아침 팀 캘린더에서 오늘의 미팅 일정을 가져와 리스트로 정리한 뒤 팀 메신저로 브리핑 메시지 발송. |
| **API 03 구글 스프레드시트** | 설문 응답, 주식 시세, 부동산 거래 내역 등 다양한 데이터를 저장·관리하는 데이터베이스로 활용. |
| **API 04 구글 드라이브** | 자동 발송할 첨부 파일 관리 또는 RAG를 위한 문서 저장소로 사용. |
| **API 05 슬랙** | 팀 내부의 업무 알림 및 시스템 모니터링 메시지 전송. 캘린더 일정 알림, 중요한 이메일 수신 알림 등을 채널에 자동 포스팅. |
| **API 06 노션** | 수집된 정보를 체계적으로 정리하고 중복을 방지하는 데이터베이스로 사용. |
| **API 07 디스코드 Webhook** | 주식 시장 모니터링과 같이 실시간성이 중요한 알림 전송. 특정 조건 충족 시 임베드 메시지 형태로 상세한 리포트를 채널에 전송. |
| **API 08 공공데이터포털(국토교통부)** | 부동산 시장의 실거래가 정보 확인 및 모니터링. HTTP Request 노드를 통해 특정 지역의 아파트 매매 상세 자료를 XML 형태로 수신 후 필터링. |
| **API 09 한국투자증권(KIS)** | 주식의 현재가 시세와 기간별 거래량 조회. 매일 장 마감 후 접근 토큰을 발급받아 특정 종목의 현재가와 20일 평균 거래량 조회. |
| **API 10 금융감독원 오픈DART** | 기업의 공시 정보 조회. 특정 종목의 거래량이 급증했을 때 해당 기업의 최근 공시 목록을 조회하여 주가 변동의 원인 파악. |
| **API 11 오픈AI** | 자연어 처리 능력을 통해 사용자 질문에 답하거나 텍스트를 벡터로 변환. 챗GPT를 통해 유튜브 자막을 요약하거나 검색 결과를 바탕으로 답변 생성. |
| **API 12 SerpAPI(Google Search)** | AI 에이전트가 실시간 인터넷 정보를 검색하여 최신 정보를 습득. AI가 스스로 판단하여 구글 검색이 필요할 때 도구로써 호출. |
| **API 13 Apify(YouTube Scraper)** | 유튜브 영상의 메타데이터와 자막을 텍스트로 추출. 특정 채널에 새 영상이 올라오면 해당 영상의 자막을 텍스트로 변환하여 가져오고, AI에게 전달하여 요약문 작성. |
| **API 14 Pinecone** | 대량의 문서 데이터를 벡터 형태로 저장하고 유사도를 검색하는 벡터 데이터베이스. 임베딩된 PDF 문서 조각들을 저장해두었다가 사용자의 질문이 들어오면 가장 관련성이 높은 문서를 검색하여 RAG 챗봇에 제공. |

---

## 목차

### 레벨 1. 설치와 환경 구성하기

- 01장 n8n 준비하기
- 02장 인터페이스와 구조 이해하기
- 03장 데이터 가공 및 조건 설정하기

### 레벨 2. 실무 자동화 프로젝트 만들기

- 04장 커뮤니케이션 자동화하기
- 05장 자동으로 정보 수집하고 활용하기

### 레벨 3. AI 에이전트 프로젝트 만들기

- 06장 검색 기능을 가진 에이전트 설계하기
- 07장 유튜브 영상 요약 에이전트 설계하기
- 08장 PDF만 넣으면 완성되는 우리 회사 챗봇 만들기

---

---

# 레벨 1. 설치와 환경 구성하기

> **학습 목표**
> n8n의 핵심 개념인 노드와 워크플로를 이해하고, 클라우드와 로컬 설치 방식의 장단점을 비교하여 자신에게 맞는 최적의 자동화 환경을 구축합니다. 더불어 주요 인터페이스의 조작법을 익히고, 트리거·로직·액션 노드의 역할과 JSON 데이터가 흐르는 구조를 파악하여 나만의 자동화 시스템을 설계하기 위한 탄탄한 기초를 다집니다.

---

## 01장. n8n 준비하기

> **학습 목표**
> n8n의 기본 개념인 노드와 워크플로를 통해 서비스 연동 자동화의 원리를 이해하고, 무료 사용 및 높은 자유도라는 n8n만의 차별화된 강점을 학습합니다. 내 컴퓨터에 직접 n8n 환경을 조성하고 관리자 계정을 생성함으로써 외부 비용 부담 없이 실무 자동화 실습을 시작할 수 있는 기반을 완성합니다.

---

### 1.1 n8n 알아보기

#### n8n이란?

n8n은 노드를 기반으로 한 워크플로 자동화 도구입니다. **워크플로**는 단계적으로 진행되는 업무의 절차나 흐름을 뜻하고, **노드**는 워크플로를 구성하는 각 단계나 작업을 의미합니다. 요컨대 n8n은 반복적인 업무의 개별 작업 단계를 사람 대신 자동으로 처리하는 도구라고 생각하면 됩니다.

예를 들어 매일 아침 이메일을 확인하고, 중요한 내용이 있으면 팀 채팅방에 알려주고, 관련 문서를 정리하는 일을 반복한다고 가정해봅시다. 이런 작업을 n8n으로 설정해두면 매일 아침 모니터 앞에 앉아 직접 마우스를 클릭할 필요 없이, 카페에서 커피 한 잔을 마시는 동안 모든 일이 자동으로 처리됩니다.

n8n은 특히 서로 다른 앱이나 서비스를 연결하는 데 강합니다. 이메일은 아웃룩으로 확인하고, 줌으로 미팅하며, 데이터는 구글 시트에 정리하는 것처럼—이렇게 서로 연동되지 않은 서비스들을 묶어서 자동으로 모든 과정을 처리할 수 있습니다.

---

#### n8n을 사용해야 하는 이유

**첫 번째 장점: 무료**

n8n의 가장 큰 장점은 무료라는 점입니다. n8n은 소스 코드가 공개된 '페어코드(Faircode)' 기반의 자동화 도구로, 누구나 자신의 컴퓨터(로컬)에 설치해서 무료로 자유롭게 사용할 수 있습니다. 클라우드 버전을 사용하거나 상업적으로 외부에 자동화 서비스를 제공하면 라이선스 비용이 발생할 수 있지만, 그렇지 않다면 로컬에 설치해서 별도 비용 없이 모든 기능을 제한 없이 사용할 수 있습니다.

> **페어코드란?** 소스 코드를 공개하여 누구나 열람할 수 있지만, 이용 범위나 상업적 목적에 따라 사용 권한을 일부 제한하는 방식입니다. 개인이나 내부 용도로는 자유롭게 써도 되지만 외부에 파는 건 안 된다는 조건이 붙은 오픈 소스라고 보면 됩니다.

**두 번째 장점: 높은 자유도**

대부분의 자동화 도구는 미리 만든 템플릿이나 정해진 방식으로만 워크플로를 구성할 수 있습니다. 하지만 n8n은 블록을 조립하듯 원하는 방식으로 워크플로를 만들 수 있어서 복잡한 업무 로직도 구현할 수 있습니다.

**세 번째 장점: 풍부한 연동 가능성**

n8n은 400개 이상의 서비스와 연동할 수 있습니다. 지메일, 슬랙, 노션, 구글 시트는 물론이고 국내에서 자주 사용하는 네이버 메일, 카카오톡 비즈니스 메시지, 잔디 같은 서비스와도 연동할 수 있습니다. API를 지원하는 다양한 업무 도구와 연결해서 나만의 기능을 추가할 수도 있습니다.

**네 번째 장점: 시각적 워크플로 구성**

n8n은 프로그래밍을 모르는 사람도 직관적으로 워크플로를 만들 수 있도록 블록처럼 생긴 노드를 연결하는 방식으로 설계되어 있습니다. 복잡한 코드를 작성할 필요 없이 마우스 클릭만으로도 자동화를 할 수 있어 비전공자들에게도 쉬운 자동화 툴입니다.

---

### 1.2 n8n을 설치하는 두 가지 방법

n8n은 설치하지 않고도 바로 사용할 수 있는 **클라우드 버전**과 내 컴퓨터나 서버에 직접 설치하는 **로컬 버전**을 모두 제공합니다.

#### 클라우드 방식

- **장점:** 사이트에 가입하고 브라우저에서 바로 사용할 수 있어 빠르게 시작할 수 있습니다. 모바일에서도 바로 접속해 워크플로를 확인할 수 있어 접근성이 뛰어납니다.
- **단점:** 무료 체험판은 기간이 14일로 정해져 있습니다. 14일이 지난 이후 유료 요금제로 전환하지 않으면 워크스페이스가 삭제됩니다. 또한 데이터가 외부 서버에 저장되기 때문에 민감한 데이터를 다룰 때는 권장하지 않습니다.

#### 로컬 방식

- **장점:** 설치가 한 번 필요하지만 모든 기능을 제한 없이 사용할 수 있습니다. 아무리 많은 워크플로를 만들고 실행해도 추가 비용이 들지 않습니다. 데이터가 내 컴퓨터에 저장되어 민감한 정보도 안전하게 다룰 수 있습니다.
- **단점:** 설치와 관리를 사용자가 직접 해야 합니다. 해당 컴퓨터에서만 사용할 수 있다는 점, 컴퓨터를 끄면 워크플로도 함께 멈춘다는 점이 있습니다.

> 이 책에서는 **로컬 방식**으로 설치한 상황을 가정하고 설명을 이어갑니다.

---

### 1.3 클라우드 방식으로 시작하기

**n8n 홈페이지:** `www.n8n.io`

1. 웹 브라우저에서 n8n 사이트에 접속합니다.
2. 메인 화면의 [Get started for free] 버튼을 눌러 가입을 시작합니다.
3. 가입 화면에서 필요한 정보를 입력합니다. **Account name**에 입력하는 내용이 서버명이 되며, 한 번 확정하면 수정할 수 없으니 유의합니다.

클라우드 버전은 14일의 체험판 사용 후 유료 요금제로 전환해야 계속 사용할 수 있습니다. 요금제는 Starter, Pro, Enterprise가 있으며, Starter 요금제만으로도 충분히 원하는 워크플로를 만들고 운영할 수 있습니다.

---

### 1.4 로컬 방식으로 설치하기

이 책에서는 **도커(Docker)**를 사용하여 환경을 구성하는 방식을 설명합니다.

#### 설치를 위해 필요한 준비물

**도커(Docker)**

도커는 프로그램을 '컨테이너'라는 독립적인 환경에서 실행하는 기술입니다. 쉽게 말해 컴퓨터 안에 작은 가상 컴퓨터를 하나 만들고 그 안에서 프로그램을 실행하는 것과 비슷합니다. 복잡한 설치 과정을 생략하고 단 한 줄의 명령어만으로 n8n을 실행할 수 있다는 점이 도커의 가장 큰 장점입니다.

**스타터 키트(Self-hosted Starter Kit)**

n8n에서 제공하는 스타터 키트는 n8n을 로컬에서 안정적으로 실행할 수 있도록 필요한 모든 설정을 미리 구성해둔 템플릿입니다. 스타터 키트는 단순히 n8n만 설치하는 것이 아니라 Ollama, Qdrant, PostgreSQL 같이 AI 기능에 필요한 여러 도구를 함께 설치하고 연결합니다. 스타터 키트는 깃허브를 통해 제공되기 때문에 **깃(Git)**이 설치되어 있어야 합니다.

---

#### 깃 설치하기

1. 깃 공식 홈페이지(`git-scm.com`)에 접속합니다.
2. [Download for Windows] 버튼을 클릭합니다.
3. 내려받은 파일을 실행하여 설치합니다. 선택 옵션은 모두 기본값으로 두고 [Next]를 클릭합니다.
4. 설치 완료 후 명령 프롬프트(cmd)를 실행하여 `git`을 입력했을 때 도움말이 출력되면 설치 성공입니다.

---

#### CPU 가상화 옵션 활성화하기

도커를 설치하기 전에 CPU 가상화 기능이 켜져 있는지 확인해야 합니다.

1. **Windows 기능 켜기/끄기**를 검색하여 실행합니다.
2. 다음 세 가지 옵션을 모두 체크합니다:
   - Hyper-V
   - Linux용 Windows 하위 시스템
   - Windows 하이퍼바이저 플랫폼
3. [확인]을 클릭하고, 설치가 완료되면 [다시 시작]을 클릭합니다.

> **Hyper-V가 보이지 않는 경우:** Windows Home 등 일부 에디션은 목록에 Hyper-V가 나타나지 않을 수 있습니다. 이 경우 메모장에 다음 코드를 입력하고 `.bat` 확장자로 저장한 다음 관리자 권한으로 실행합니다.
> ```
> pushd "%~dp0"
> dir /b %SystemRoot%\servicing\Packages\*Hyper-V*.mum >hyper-v.txt
> for /f %%i in ('findstr /i . hyper-v.txt 2^>nul') do dism /online /norestart /add-package:"%SystemRoot%\servicing\Packages\%%i"
> del hyper-v.txt
> Dism /online /enable-feature /featurename:Microsoft-Hyper-V-All /LimitAccess /ALL
> pause
> ```

---

#### 도커 설치하기

1. 도커 홈페이지(`docker.com`)에 접속합니다.
2. [Download Docker Desktop] 버튼에 마우스를 올려 운영 체제에 맞는 파일을 내려받습니다.
3. 내려받은 파일을 실행합니다. Configuration 화면에서 **[Use WSL 2 instead of Hyper-V]** 옵션을 반드시 체크합니다.
4. 설치가 완료되면 컴퓨터를 재부팅합니다.
5. 도커 실행 후 로그인 화면이 뜨면 [Skip]을 눌러 넘어갑니다.

---

#### 스타터 키트 설치하기

스타터 키트 깃허브: `github.com/n8n-io/self-hosted-ai-starter-kit`

1. `N8N`이라는 폴더를 만들고, 해당 폴더의 주소창에 `cmd`를 입력하여 명령 프롬프트를 실행합니다.

2. 다음 명령어를 한 줄씩 차례대로 실행합니다:

```bash
git clone https://github.com/n8n-io/self-hosted-ai-starter-kit.git
cd self-hosted-ai-starter-kit
copy .env.example .env
```

3. 내려받은 폴더 안의 `docker-compose.yml` 파일을 메모장으로 열고, `environment:` 항목 아래에 다음 내용을 추가합니다 (들여쓰기 주의):

```yaml
environment:
  - TZ=Asia/Seoul
  - GENERIC_TIMEZONE=Asia/Seoul
  - N8N_SECURE_COOKIE=false
  - DB_TYPE=postgresdb
  - DB_POSTGRESDB_HOST=postgres
```

> `N8N_SECURE_COOKIE=false`는 로컬 HTTP 환경에서 로그인 오류를 방지하기 위한 설정입니다.
> `TZ`와 `GENERIC_TIMEZONE`은 n8n의 시간대를 한국 표준시로 설정합니다.

4. 환경에 맞는 명령어로 스타터 키트를 실행합니다:

```bash
# 일반 CPU 사용자
docker compose --profile cpu up

# NVIDIA GPU 사용자
docker compose --profile gpu-nvidia up
```

5. 설치가 완료되면 도커 Desktop에서 `self-hosted-ai-starter-kit` 컨테이너가 생성된 것을 확인합니다.

6. 컨테이너 목록에서 **n8n**을 찾아 실행 버튼(▶)을 클릭합니다. **postgres-1** 컨테이너도 반드시 함께 실행해야 합니다.

7. n8n 노드의 Port `5678:5678`을 클릭하면 브라우저에서 n8n에 접속됩니다.

8. 최초 접속 시 관리자 계정을 만드는 **Set up owner account** 페이지가 열립니다. 이름, 이메일, 비밀번호를 입력하여 계정을 만듭니다.

> ⚠️ 이 계정은 내 컴퓨터에서만 사용하는 정보이므로 비밀번호를 잊어버리면 찾기 어렵습니다.

---

## 02장. 인터페이스와 구조 이해하기

> **학습 목표**
> 워크플로 캔버스, 노드 패널, 설정 패널 등 n8n의 주요 인터페이스를 조작하는 방법을 익혀 자동화 작업의 기초를 다집니다. 트리거 노드, 로직 노드, 액션 노드 등 노드의 역할별 분류를 이해하고, 노드 간의 연결을 통해 데이터가 흐르는 구조를 파악합니다. JSON 형식으로 처리되는 데이터의 구조를 이해하고, 실행하여 워크플로의 성공 여부와 오류를 확인하는 방법을 배웁니다.

---

### 2.1 인터페이스와 친해지기

메인 화면의 오른쪽 위에 있는 [Create Workflow] 버튼을 클릭하거나 왼쪽 메뉴 바 위쪽에 있는 [+] 버튼을 눌러 새로운 워크플로를 만듭니다.

n8n의 기본 화면은 크게 3개의 영역으로 구성되어 있습니다.

#### 워크플로 캔버스 (Workflow Canvas)

화면 중앙의 넓은 흰색 영역입니다. n8n의 핵심 작업 공간으로, 여기서 노드를 배치하고 연결하여 자동화 워크플로를 구성합니다. 드래그 앤 드롭 방식으로 노드를 자유롭게 이동할 수 있습니다.

- 마우스 휠 또는 [줌 인/아웃] 버튼으로 캔버스 배율 조절
- 캔버스 이동: 스페이스바 + 드래그 또는 마우스 오른쪽 버튼 + 드래그

#### 노드 패널

캔버스 중앙의 [+] 버튼이나 오른쪽 위의 [+] 버튼을 클릭하면 나타납니다. 사용할 수 있는 노드들이 카테고리별로 정리되어 있으며, 검색창에서 특정 노드를 검색할 수 있습니다.

첫 번째 노드를 추가할 때는 워크플로의 시작을 결정하는 **트리거 노드** 목록이 표시됩니다.

#### 노드 설정 패널

노드를 클릭하면 선택한 노드의 설정을 변경할 수 있는 패널이 나타납니다.

- **Input:** 앞선 노드로부터 받은 데이터
- **Output:** 현재 노드의 실행 결과
- **Execute step:** 해당 노드만 단독으로 실행
- **Docs:** 해당 노드의 공식 문서 페이지

**Parameters 탭 주요 설정:**

| 옵션 | 설명 |
|------|------|
| **Always Output Data** | 노드가 실패하거나 실행되지 않더라도 이전 노드의 데이터를 그대로 다음 노드로 전달 |
| **Execute Once** | 입력 데이터가 여러 개여도 노드를 한 번만 실행 |
| **Retry On Fail** | 노드 실행이 실패했을 때 자동으로 재시도 |
| **On Error** | 오류 발생 시 처리 방법 설정 (Stop / Continue / Continue using error output) |

---

### 2.2 기본 구조 이해하기

#### 워크플로란?

워크플로는 n8n에서 자동화 프로세스를 구성하는 기본 단위입니다. 하나의 워크플로는 여러 개의 작업 단계를 순차적으로 연결하여 하나의 자동화 흐름을 만드는 것으로, 각 단계는 하나의 노드로 표현합니다.

워크플로는 보통 **트리거 노드**부터 시작됩니다. 트리거로 시작된 워크플로는 이후 데이터를 가져오거나 외부 서비스를 호출하는 노드로 이어지고, 마지막에는 메시지 전송, 파일 저장, 결과 기록 등의 마무리 작업을 수행하며 종료됩니다.

> **💡 워크플로 템플릿 활용하기**
> n8n 공식 템플릿 페이지에서는 4,000개가 넘는 검증된 워크플로 템플릿을 제공합니다. 버튼 한 번으로 자신의 n8n 환경에 그대로 복사해올 수 있습니다.

---

#### 노드와 연결 방법

워크플로의 각 단계는 노드라고 불리는 단위 작업으로 구성됩니다. 노드는 역할에 따라 크게 3가지로 나뉩니다.

- **트리거 노드:** 워크플로를 시작하는 조건이나 신호
- **로직 노드:** 흐름을 제어하거나 데이터를 가공 (IF, Switch, Wait, Loop 등)
- **액션 노드:** 실제 작업을 수행

**노드 연결 방법:**

- 노드 출력 포트 옆의 [+] 버튼을 클릭하여 다음 노드를 추가합니다.
- 노드 간 연결선 위에 마우스를 올리면 [+]와 [휴지통] 아이콘이 나타납니다.
- 떨어진 노드를 연결하려면 출력 포트를 클릭한 채로 다음 노드로 드래그합니다.

---

#### 워크플로 구조 이해하기

기본적으로 노드들은 연결된 순서대로 하나씩 실행됩니다. 실행 순서는 **왼쪽에서 오른쪽**, **위에서 아래** 순입니다.

중간에 IF 노드나 Switch 노드를 사용하면 조건에 따라 두 갈래로 나뉘는 흐름을 만들 수도 있습니다.

---

#### 워크플로 실행 및 결과 확인하기

- **[Inactive] 버튼:** 클릭하여 워크플로를 활성화하면 설정된 조건에 따라 전체 워크플로가 동작합니다.
- **[Execute workflow] 버튼:** 테스트용으로 현재 시점에서 워크플로를 즉시 실행합니다.
- **[Execute step] 버튼:** 개별 노드만 단독으로 실행합니다.
- **[Executions] 탭:** 지금까지 실행된 모든 기록을 시간순으로 확인할 수 있습니다.

n8n의 모든 데이터는 기본적으로 **JSON 형식**으로 처리됩니다. 데이터 보기 옵션은 다음과 같습니다.

| 보기 옵션 | 설명 |
|-----------|------|
| **Schema** | 필드명과 값이 시각적으로 구분된 읽기 쉬운 형태 |
| **Table** | 스프레드시트와 비슷한 표 형태 |
| **JSON** | 원본 JSON 데이터 구조 그대로 표시 |

---

## 03장. 데이터 가공 및 조건 설정하기

> **학습 목표**
> 가장 간단한 형태의 워크플로를 만들어 n8n의 기본 동작 방식을 익힙니다. 매뉴얼 트리거를 사용해 버튼을 누르면 바로 실행되는 간단한 워크플로를 만들고, 이어서 수집한 시간 데이터를 가공하고 분류하는 작업을 통해 노드를 발전시킵니다.

---

### 3.1 첫 워크플로 만들기

여기서는 사용자가 워크플로를 실행하면 현재 시간을 확인해서 시간대에 따라 다른 내용으로 이메일을 보내는 워크플로를 만듭니다.

**워크플로 흐름:**
```
워크플로 시작(트리거) → 현재 시간 가져오기 → 오전/오후 구분(IF) → 시간대별 메시지 설정 → 이메일 발송
```

**매뉴얼 트리거 워크플로 만들기:**

1. n8n 메인 화면에서 [Create workflow]를 눌러 새 워크플로를 추가합니다.
2. 가운데의 [+ Add first step] 버튼을 클릭합니다.
3. 트리거 유형 리스트에서 [Trigger Manually]를 선택합니다.

> 매뉴얼 트리거는 사용자가 수동으로 직접 실행 버튼을 눌러야 워크플로가 시작됩니다. 테스트나 개발 단계에서 매우 유용합니다.

4. 두 번째 노드로 Date & Time 노드를 추가합니다. 노드 검색창에 `Date`를 입력하고 [Date & Time] → [Get Current Date]를 선택합니다.

**Date & Time 노드 주요 설정:**

- **Include Current Time:** 시간 정보 포함 여부 (기본값: true)
- **Output Field Name:** 가져온 날짜 정보를 저장할 필드명 (기본값: `currentDate`)

---

### 3.2 표현식으로 시간 데이터 가공하기

현재 Date & Time 노드에서 받은 시간 데이터는 `2025-08-03T08:59:55.787-04:00`과 같은 ISO 형식입니다. 표현식(Expression)을 사용해 이 데이터에서 시간 부분만 추출하고, 오전/오후를 구분합니다.

**Edit Fields(Set) 노드 추가:**

Edit Fields 노드는 워크플로에서 데이터를 생성하거나 수정할 수 있는 기본 노드입니다. 모드는 **Manual Mapping**과 **JSON** 중 선택할 수 있습니다.

**필드 추가 예시:**

| 필드명 | 자료형 | 표현식 | 설명 |
|--------|--------|--------|------|
| `currentDate` | String | `{{ $json.currentDate }}` | 이전 노드의 날짜 데이터 그대로 가져오기 |
| `currentHour` | String | `{{ new Date($node["Date & Time"].json.currentDate).getHours() }}` | 시간(0~23) 추출 |
| `timeOfDay` | String | `{{ new Date($node["Date & Time"].json.currentDate).getHours() < 12 ? "오전" : "오후" }}` | 오전/오후 구분 |

---

### 3.3 표현식 문법 이해하기

표현식은 자바스크립트 기반으로 동작하며, 중괄호를 중첩하여 사용합니다: `{{ ... }}`

**기본 문법:**

```javascript
// 이전 노드에서 전달받은 데이터 접근
{{ $json.fieldName }}

// 특정 노드의 데이터 접근
{{ $(노드명).item.json.fieldName }}
{{ $node[노드명].json.fieldName }}
```

**자주 사용하는 내장 함수:**

```javascript
{{ $json.text.trim() }}                   // 공백 제거
{{ $json.text.toLowerCase() }}            // 소문자 변환
{{ $json.text.split(",") }}               // 문자열 분리
{{ $json.value || "기본값" }}              // 빈 값일 때 기본값 설정
{{ $json.text.includes("키워드") }}        // 문자열 포함 여부 확인
```

**조건식 (삼항 연산자):**

n8n의 표현식에서는 if/else 문장 대신 삼항 연산자를 사용합니다.

```javascript
// 기본 형식: 조건 ? 참일 때 값 : 거짓일 때 값
{{ $json.hour < 12 ? "오전" : "오후" }}

// 문자열 포함 여부로 조건
{{ $json.title.includes("에너지") ? "에너지 관련" : "기타" }}

// 중첩 조건
{{ $json.age < 13 ? "어린이" : ($json.age < 20 ? "청소년" : "성인") }}
```

---

### 3.4 계정 연결하여 지메일로 메일 발송하기

구글 등 외부 서비스와 연동하려면 **인증 정보(Credential)** 설정이 필요합니다.

#### 구글 클라우드 콘솔 설정

1. 구글 클라우드 플랫폼(`cloud.google.com`)에 접속하여 로그인합니다.
2. 새 프로젝트를 생성합니다.
3. [API 및 서비스 → 라이브러리]에서 **Gmail API**를 검색하여 활성화합니다.

#### OAuth 동의 화면 구성하기

1. [사용자 인증 정보] → [+ 사용자 인증 정보 만들기] → [OAuth 클라이언트 ID]를 선택합니다.
2. [동의 화면 구성] 버튼을 클릭합니다.
3. 앱 이름(`n8n Gmail Integration`), 사용자 지원 이메일, 연락처 이메일을 입력합니다.
4. **대상**은 일반 계정의 경우 [외부]를 선택합니다.
5. Google API 서비스 사용자 데이터 정책에 동의합니다.

#### OAuth 클라이언트 ID 만들기

1. 애플리케이션 유형을 [웹 애플리케이션]으로 선택합니다.
2. n8n의 Gmail Credential 화면에서 **OAuth Redirect URL**을 복사합니다. (예: `http://localhost:5678/rest/oauth2-credential/callback`)
3. 구글 클라우드 콘솔의 [승인된 리디렉션 URI]에 해당 주소를 붙여넣습니다.
4. [만들기]를 클릭합니다.
5. 생성된 **클라이언트 ID**와 **클라이언트 보안 비밀번호**를 복사하여 안전하게 보관합니다.

> ⚠️ 클라이언트 보안 비밀번호는 최초 생성 시에만 확인할 수 있습니다. 반드시 저장해 두세요.

#### n8n에서 지메일 연동하기

1. n8n에서 [Create Credential] → `gmail` 검색 → [Gmail OAuth2 API] 선택.
2. Client ID와 Client Secret에 복사한 값을 붙여넣습니다.
3. [Sign in with Google]을 클릭하여 구글 계정으로 로그인합니다.

> **테스트 사용자 등록:** 구글 클라우드 콘솔에서 [API 및 서비스 → OAuth 동의 화면 → 대상]으로 이동하여 [+ Add users]를 클릭하고 자신의 이메일을 추가합니다.

#### 지메일 노드로 이메일 보내기

이메일 발송 노드(Gmail - Send a message) 주요 설정:

| 설정 | 값 |
|------|----|
| **Credential** | 연동한 Gmail 계정 |
| **Resource** | Message |
| **Operation** | Send |
| **To** | 수신 이메일 주소 |
| **Subject** | 이메일 제목 |
| **Email Type** | HTML 또는 Text |
| **Message** | 이메일 본문 |

> **n8n 출처 문구 제거:** [Add Option → Append n8n Attribution]을 추가하고 비활성화하면 본문 하단의 "This email was sent automatically with n8n" 문구가 사라집니다.

---

### 3.5 트리거 노드 알아보기

트리거 노드는 워크플로의 시작 버튼과 같은 역할을 합니다. 아무리 완벽한 워크플로도 트리거 노드가 없으면 실행되지 않습니다.

#### 주요 트리거 노드 유형

**On app event**

특정 앱에서 새로운 이벤트가 발생했을 때 워크플로를 시작하는 트리거입니다. 지메일에서 새 이메일을 수신하거나 구글 스프레드시트에 행이 추가될 때 등을 감지합니다.

**On a schedule**

정해진 주기로 워크플로를 자동 실행하는 트리거입니다. 반복적인 업무를 주기적으로 실행하는 워크플로에 많이 사용합니다.

주요 설정:
- **Trigger Interval:** 실행 주기 단위 (Seconds, Minutes, Hours, Days, Weeks, Months)
- **Trigger at Hour / Minute:** 실행 시각
- **Add Rule:** 여러 시간대나 요일에 실행 규칙 추가

**On webhook call**

외부 시스템이나 사용자가 HTTP 요청을 보냈을 때 워크플로가 자동으로 실행되는 방식입니다. 특정 이벤트가 발생했을 때 즉시 알려주는 '초인종' 역할을 합니다.

> **On app event vs On webhook call 차이:**
> - On app event: n8n이 앱의 API를 통해 이벤트를 감지 (폴링 방식)
> - On webhook call: 외부 시스템이 n8n으로 HTTP 요청을 직접 전송 (더 실시간)

**On form submission**

n8n에서 직접 제공하는 폼을 사용자가 제출했을 때 워크플로가 자동 실행됩니다.

**When executed by another workflow**

다른 워크플로에서 이 워크플로를 하위 워크플로로 호출할 때 시작됩니다. 워크플로를 목적별로 분리하여 재사용성을 높일 수 있습니다.

**On chat message**

채팅 앱에서 메시지를 입력했을 때 워크플로를 자동 실행합니다. AI 어시스턴트나 챗봇을 구현할 때 주로 사용합니다.

---

---

# 레벨 2. 실무 자동화 프로젝트 만들기

> **학습 목표**
> 구글 캘린더, 슬랙, 지메일을 연동하여 일정 알림 봇을 만들고 이메일을 자동 분류하는 등 반복적인 커뮤니케이션 업무를 자동화하는 시스템을 구축합니다. HTTP Request 노드를 활용해 웹 스크래핑과 공공 데이터 및 증권사 API를 호출하고, 수집된 데이터를 정제하여 노션이나 구글 시트에 저장하는 정보 수집 자동화를 구현합니다.

---

## 04장. 커뮤니케이션 자동화하기

> **학습 목표**
> 구글 캘린더와 슬랙을 연동하여 매일 아침 팀의 미팅 일정을 확인하고, 일정 유무에 따라 맞춤 알림을 보내는 봇을 구현합니다. 수신된 이메일의 내용을 분석하여 중요도에 따라 슬랙으로 즉시 알림을 보내거나 라벨을 붙여 자동 분류하는 시스템을 구축합니다.

---

### 4.1 오늘의 미팅 일정 알림

구글 캘린더와 슬랙을 연동하여 아침마다 슬랙 팀 채널에 미팅 일정을 알려주는 시스템을 만듭니다.

**워크플로 흐름:**
```
Schedule Trigger → (평일 여부 확인) IF → 구글 캘린더에서 일정 가져오기 → (일정 유무) IF → 메시지 정리 → 슬랙 발송
```

#### 슬랙 워크스페이스 생성하기

1. 슬랙 홈페이지(`slack.com`)에 접속하여 계정을 생성합니다.
2. [새 워크스페이스로 계속 진행]을 눌러 워크스페이스를 생성합니다.
3. 채팅 채널을 추가합니다: [채널 추가 → 생성 → 채널 생성]
   - 채널 이름: `my_team`
   - 가시성: 공개

#### 슬랙 API 사용하기

1. 슬랙 API 사이트(`api.slack.com/apps`)에 로그인합니다.
2. [Create an App → From scratch]를 선택합니다.
3. 앱 이름(`n8n Bot`)과 워크스페이스를 지정합니다.
4. [OAuth & Permissions]에서 다음 권한(Scopes)을 추가합니다:
   - `chat:write` — 메시지 보내기
   - `chat:write.public` — 공개 채널에 메시지 보내기
   - `channels:read` — 채널 목록 조회
   - `groups:read` — 프라이빗 채널 목록 조회
5. [Install App → Install to 워크스페이스]를 클릭하여 설치합니다.
6. 생성된 **Bot User OAuth Token**(`xoxb-`로 시작)을 복사하여 보관합니다.

#### 슬랙 Credential 설정하기

n8n에서 [Create Credential → Slack API] 선택 후, **Access Token** 항목에 Bot User OAuth Token을 붙여넣고 저장합니다.

#### 구글 캘린더 API 사용하기

1. 구글 클라우드 콘솔에서 **Google Calendar API**를 활성화합니다.
2. [API 및 서비스 → OAuth 동의 화면 → 데이터 액세스]에서 캘린더 범위를 추가합니다.
   - `.../auth/calendar` (읽기/쓰기 권한)

#### 구글 캘린더 Credential 설정하기

n8n에서 [Create Credential → Google Calendar OAuth2 API] 선택 후, Client ID와 Client Secret을 입력하고 [Sign in with Google]로 계정을 연결합니다.

실습용 캘린더(Team Calendar)를 생성하고 테스트 일정을 추가해 둡니다.

---

#### 워크플로 구성

**1단계: Schedule Trigger 설정**

- Trigger Interval: Days
- Days Between Triggers: 1
- Trigger at Hour: 9am

**2단계: 평일/주말 구분 (IF 노드)**

```javascript
// Conditions 첫 번째 값에 입력
{{ ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].includes($json['Day of week']) }}
```

비교 연산자: `Boolean → is equal to`, 비교값: `true`

**3단계: 구글 캘린더에서 일정 가져오기**

- 노드: [Google Calendar → Get many events]
- Calendar: Team Calendar
- After: `{{ $now }}`
- Before: `{{ $now.set({ hour: 18, minute: 0, second: 0, millisecond: 0 }).toISO() }}`
- Settings → Always Output Data: 활성화

**4단계: 일정 유무 분기 (IF 노드)**

```javascript
{{ Boolean($input.first().json.summary) }}
```
비교: `Boolean → is true`

**5단계: 일정 정리 (Edit Fields 노드)**

일정이 있을 때 다음 필드를 생성합니다:

```javascript
// todayEvents (Array 타입)
{{
  $input.all()
    .map(i => i.json)
    .filter(e => e.start?.dateTime)
    .sort((a,b) => new Date(a.start.dateTime) - new Date(b.start.dateTime))
    .map(e => {
      const start = new Date(e.start.dateTime);
      const end = new Date(e.end.dateTime);
      return {
        title: e.summary ?? '',
        startTime: start.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
        endTime: end.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
        location: e.location ?? '',
        attendees: (e.attendees ?? []).map(a => a.email).join(',')
      }
    })
}}

// eventCount (String 타입)
{{
  $input.all()
    .map(i => i.json)
    .filter(e => e.start?.dateTime)
    .length
}}

// todayDate (String 타입)
{{ new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }) }}
```

Settings → **Execute Once** 활성화 (일정이 여러 개여도 노드를 한 번만 실행)

**6단계: 슬랙 메시지 구성 (Edit Fields 노드)**

```javascript
// message (String 타입)
{{
  `*${$json.todayDate} 팀 일정*\n오늘 우리 팀에게는 ${$json.eventCount}개의 일정이 있습니다.\n` +
  $json.todayEvents.map(event => {
    const lines = [
      `*${event.startTime} - ${event.endTime}* ${event.title}`,
      event.location ? `📍 ${event.location}` : '',
      event.attendees ? `${event.attendees}` : ''
    ].filter(Boolean);
    return lines.join('\n');
  }).join('\n\n') + '\n\n모두 좋은 하루 보내세요! 🌟'
}}
```

일정이 없는 경우:
```javascript
{{ `*${$json.todayDate} 팀 일정*\n오늘은 예정된 팀 일정이 없습니다. 개별 업무에 집중하는 하루가 될 것 같네요!` }}
```

**7단계: 슬랙 메시지 발송**

- Credential: Slack account
- Send Message To: Channel
- Channel: my_team
- Message Type: Simple Text Message
- Message Text: `{{ $json.message }}`
- Options → **Include Link to Workflow:** 비활성화 (출처 문구 제거)

---

### 4.2 이메일 자동 분류 처리

수신된 이메일을 자동으로 분류하고 처리하는 워크플로를 만듭니다. 중요한 이메일은 슬랙으로 즉시 알림을 받고, 일반적인 이메일은 자동으로 라벨을 붙여 정리합니다.

**사전 준비:** 지메일에서 다음 라벨을 미리 생성합니다.
- 회의, 프로젝트, 알림, 일반, 자동분류

**워크플로 흐름:**
```
Gmail Trigger → 데이터 가공(Edit Fields) → 중요도 확인(IF) → 중요: 슬랙 DM 발송
                                                              → 일반: Switch(카테고리별) → 라벨 붙이기
```

#### 지메일 트리거 설정하기

- 노드: [Gmail Trigger → On message received]
- Credential: Gmail 계정
- Poll Times: Every Minute
- Event: Message Received
- Simplify: 활성화

#### 이메일 내용 분석하기

Edit Fields 노드에서 다음 4개 필드를 생성합니다:

```javascript
// senderEmail (String): 발신자 이메일 추출
{{ ($json["From"] ?? "").match(/<([^>]+)>/)?.[1] ?? ($json["From"] ?? "").trim() }}

// subject (String): 이메일 제목
{{ $json["Subject"] ?? "" }}

// isImportant (String): 중요도 판단
{{
  ($json["Subject"] ?? "").toLowerCase().includes("긴급") ||
  ($json["Subject"] ?? "").toLowerCase().includes("urgent") ||
  ($json["From"] ?? "").toLowerCase().includes("boss@company.com")
}}

// category (String): 카테고리 분류
{{
  /noreply/i.test($json["From"] ?? "") ? "notification" :
  /회의|미팅|meeting/i.test($json["Subject"] ?? "") ? "meeting" :
  /프로젝트|project/i.test($json["Subject"] ?? "") ? "project" :
  "general"
}}
```

Include Other Input Fields: 활성화 (메일 id 등 원본 데이터 유지)

#### 중요 이메일 즉시 알림 보내기

IF 조건: `{{ $json.isImportant }}` → `String → is equal to` → `true`

슬랙 DM 설정:
- Send Message To: **User**
- User ID: 슬랙 프로필에서 [멤버 ID 복사]

메시지:
```
*중요한 이메일이 도착했습니다!*
*발신자:* {{$json.senderEmail}}
*제목:* {{$json.subject}}
*시간:* {{ new Date().toLocaleString('ko-KR') }}
Gmail에서 확인해주세요!
```

#### 일반 이메일 자동 라벨링하기

Switch 노드 설정:
- Mode: Rules
- 3개의 조건 생성:
  - `{{ $json.category }}` → `String → is equal to` → `meeting`
  - `{{ $json.category }}` → `String → is equal to` → `project`
  - `{{ $json.category }}` → `String → is equal to` → `notification`
- Options → Fallback Output: Extra Output

각 분기에 Gmail → Add label to message 노드 연결:
- Message ID: `{{ $json.id }}`
- Label Names: 해당 카테고리 라벨 + 자동분류

#### 읽음 상태 자동 관리하기

알림 카테고리 중 특정 발신자(깃허브, 지라, 컨플루언스) 메일을 자동으로 읽음 처리합니다.

```javascript
{{
  $json.category === 'notification' &&
  (
    $json.senderEmail.includes('github') ||
    $json.senderEmail.includes('jira') ||
    $json.senderEmail.includes('confluence')
  )
}}
```

조건 판별식: `Boolean → is true`

true 분기에 [Gmail → Mark a message as read] 노드 연결:
- Message ID: `{{ $json.id }}`

---

### 4.3 설문 응답 데이터 자동 분석

설문 응답 데이터를 받으면 자동으로 응답자에게 자료를 발송하고, 응답 데이터를 누적 분석하여 대시보드까지 만드는 워크플로를 만듭니다.

**워크플로 흐름:**
```
Google Sheet Trigger → 데이터 정규화 → 구글 드라이브에서 파일 다운로드 → 이메일 발송(첨부 포함)
                    ↓
                점수 계산 → 점수 합계 → 추가 분석 → 구글 시트 저장
```

#### 구글폼 및 시트 세팅하기

1. 구글폼(`docs.google.com/forms`)에서 설문을 생성합니다.
2. [응답 → Sheets에 연결]로 구글 시트와 연동합니다.

#### 구글 시트와 구글 드라이브 연동하기

구글 클라우드 콘솔에서 추가로 활성화할 API:
- **Google Sheets API**
- **Google Drive API**

OAuth 동의 화면의 데이터 액세스에 다음 범위 추가:
- `.../auth/spreadsheets` — 스프레드시트 읽기/쓰기
- `.../auth/drive.file` — 앱에서 사용하는 특정 파일 접근

n8n에서 다음 Credential을 모두 생성합니다:
- Google Sheets Trigger OAuth2 API
- Google Sheets OAuth2 API
- Google Drive OAuth2 API

#### 응답 데이터 실시간으로 확인하고 자료 발송하기

**트리거:** Google Sheets Trigger → On row added
- Document: 설문 응답 스프레드시트
- Sheet: 응답 시트
- Poll Times: Every Minute

**데이터 정규화 (Edit Fields, JSON 모드):**

```json
{
  "리드이름": "{{$json['이름']}}",
  "이메일": "{{$json['이메일 주소']}}",
  "연락처": "{{$json['연락처'] || '미제공'}}",
  "회사명": "{{$json['회사명']}}",
  "직책": "{{$json['직책'] || '미제공'}}",
  "회사규모": "{{$json['회사 규모']}}",
  "현재도구": "{{$json['현재 사용 중인 자동화 도구']}}",
  "비효율문제": "{{$json['현재 겪고 있는 가장 큰 업무 비효율']}}",
  "예산범위": "{{$json['월 자동화 솔루션 예산']}}",
  "의사결정권": "{{$json['자동화 도구 도입 의사결정권']}}",
  "도입시급성": "{{$json['자동화 솔루션 도입 시급성']}}",
  "유입경로": "{{$json['이 페이지를 알게 된 경로']}}",
  "설문제출시간": "{{$json['타임스탬프']}}"
}
```

Include Other Input Fields: 비활성화

**파일 다운로드:**

구글 드라이브에 자료 파일을 미리 업로드한 후:
- 노드: [Google Drive → Download file]
- 파일 목록에서 해당 PDF 파일 선택

**이메일 발송:**

- To: `{{$json["이메일"]}}`
- Subject: `요청하신 자동화 꿀팁 자료를 보내드립니다!`
- Message: 응답자 정보를 활용한 맞춤형 HTML 본문
- Options → Attachments 추가, Attachment Field Name: `data`

#### 응답 데이터 분석하기

**점수 계산 (Edit Fields, Manual Mapping):**

```javascript
// 회사규모점수 (Number)
{{ $json["회사규모"]==="11-50명 (중소기업)" ? 25 : $json["회사규모"]==="51-200명(중견기업)" ? 20 : $json["회사규모"]==="1-10명 (스타트업/소기업)" ? 15 : $json["회사규모"]==="개인/프리랜서" ? 12 : 10 }}

// 예산점수 (Number)
{{ $json["예산범위"]==="50-100만원" ? 30 : $json["예산범위"]==="100만원 이상" ? 25 : $json["예산범위"]==="10-50만원" ? 20 : $json["예산범위"]==="아직 정해지지 않음" ? 10 : 5 }}

// 의사결정권점수 (Number)
{{ $json["의사결정권"]==="본인이 최종 결정권자" ? 20 : $json["의사결정권"]==="의사결정에 큰 영향력을 가짐" ? 15 : $json["의사결정권"]==="제안할 수 있지만 최종 결정권은 없음" ? 8 : 3 }}

// 도입시급성점수 (Number)
{{ $json["도입시급성"]==="즉시 도입 필요" ? 15 : $json["도입시급성"]==="3개월 내 도입 희망" ? 12 : $json["도입시급성"]==="6개월 내 검토 예정" ? 8 : 3 }}
```

**최종점수 계산 (Edit Fields):**

```javascript
{{ $json["회사규모점수"] + $json["예산점수"] + $json["의사결정권점수"] + $json["도입시급성점수"] + $json["현재도구점수"] }}
```

> 같은 노드 내에서는 방금 만든 필드를 참조할 수 없으므로 별개의 노드를 추가합니다.

**추가 분석 (Edit Fields):**

```javascript
// 우선순위 (String)
{{ $json["최종점수"] >= 80 ? "A" : $json["최종점수"] >= 60 ? "B" : "C" }}

// 접근전략 (String)
{{ $json["도입시급성"]==="즉시 도입 필요" ? "즉시 전화 연락+무료 컨설팅 제안" : ($json["의사결정권"]==="본인이 최종 결정권자" && $json["최종점수"] >= 70 ? "개인화된 데모 세션 제안" : "단계별 이메일 마케팅 시퀀스") }}
```

#### 구글 시트로 저장하기

구글 시트에 [통합분석결과] 시트를 추가한 다음:
- 노드: [Google Sheets → Append row in sheet]
- Mapping Column Mode: Map Automatically

#### 대시보드로 시각화하기

Looker Studio(`lookerstudio.google.com`)에서:
1. [+ 새 보고서 작성] 클릭
2. 데이터 소스로 [Google Sheets] 선택
3. 통합분석결과 시트 연결
4. 원형 차트, 막대 차트 등 원하는 시각화 추가

---

## 05장. 자동으로 정보 수집하고 활용하기

> **학습 목표**
> HTTP Request 노드를 활용해 온라인 서점, 공공 데이터 포털, 증권사 API 등 다양한 외부 소스에서 데이터를 수집하는 방법을 배웁니다. 수집한 원본 데이터에서 필요한 정보만 추출하고 정제하여 노션이나 구글 시트에 저장하는 파이프라인을 만듭니다.

---

### 5.1 웹 스크래핑을 통한 도서 정보 수집하기

온라인 서점에서 도서 정보를 자동으로 수집하여 노션에 정리하는 시스템을 만듭니다. 실습 사이트: Books to Scrape (`books.toscrape.com`)

**워크플로 흐름:**
```
Schedule Trigger → HTTP Request(HTML 수집) → HTML 정제(1차) → HTML 정제(2차) → Edit Fields(URL 정리) → Notion(기존 데이터 조회) → Merge(중복 제거) → Notion(신규 저장)
```

#### 노션에 데이터베이스 세팅하기

1. 노션(`notion.com`) 가입 후, [빈 데이터베이스] 페이지를 생성합니다.
2. 데이터베이스 이름: `도서DB`
3. 열(속성) 구성:

| 열 이름 | 유형 |
|---------|------|
| Title | 텍스트 (기본) |
| Price | 텍스트 |
| Image | URL |
| Product_URL | URL |
| Date | 날짜 |

4. [설정 → 연결 → API 연결 개발 또는 관리]에서 새 API 통합을 만들고 도서DB에 접근 권한을 부여합니다.
5. 생성된 **프라이빗 API 통합 시크릿**을 복사하여 보관합니다.
6. n8n에서 [Create Credential → Notion API] 선택 후, Internal Integration Secret에 시크릿을 붙여넣고 저장합니다.

#### HTTP Request 노드로 데이터 수집하기

- Method: GET
- URL: `https://books.toscrape.com/catalogue/category/books/food-and-drink_33/index.html`
- Send Headers: 활성화
  - Name: `User-Agent`
  - Value: 자신의 브라우저 User-Agent 값

#### HTML 정제하기

**1차 추출 (Extract HTML Content 노드):**

- Source Data: JSON
- JSON Property: `data`
- Key: `List`
- CSS Selector: `li[class="col-xs-6 col-sm-4 col-md-3 col-lg-3"]`
- Return Value: **HTML**
- Return Array: 활성화

**2차 추출 (Extract HTML Content 노드):**

- JSON Property: `List`
- 4개 필드 추가:

| Key | CSS Selector | Return Value | Attribute |
|-----|--------------|--------------|-----------|
| Title | `h3>a` | Attribute | `title` |
| Price | `p.price_color` | Text | - |
| Image | `.image_container img` | Attribute | `src` |
| Product_URL | `h3>a` | Attribute | `href` |

**URL 전체 경로로 변환 (Edit Fields 노드):**

```javascript
// Image
{{ 'https://books.toscrape.com/' + $json.Image.replace('../../../../', '') }}

// Product_URL
{{ 'https://books.toscrape.com/catalogue/' + $json.Product_URL.replace('../../../', '') }}

// Date
{{ new Date().toLocaleDateString('ko-KR') }}
```

Include Other Input Fields: 활성화

#### 중복 데이터 제거하기

1. **Notion - Get many database pages 노드:**
   - Database: 도서DB
   - Return All: 활성화
   - Simplify: 활성화
   - Filter → Build Manually → Property: Title → Equals → `{{ $json.Title }}`

2. **Merge 노드:**
   - Mode: Combine
   - Combine By: Matching Fields
   - Fields To Match Have Different Names: 활성화
   - Input 1 Field: `property_title`
   - Input 2 Field: `Title`
   - Output Type: Keep Non-Matches
   - Output Data From: Input 2

#### 노션 데이터베이스 업데이트하기

- 노드: [Notion → Create a database page]
- Database: 도서DB
- Properties에 Title, Price, Image, Product_URL, Date 매핑
- Image의 Ignore If Empty: 활성화
- Date의 Include Time: 비활성화

#### 스크래핑 오류 알림 추가하기

HTTP Request 노드의 Settings에서 On Error를 **Continue (using error output)**으로 설정합니다. Error 분기에 슬랙 알림 노드를 연결합니다:

```
⚠️ 도서 수집 오류 발생
시간: {{ new Date().toLocaleString('ko-KR') }}
오류: 웹사이트 접속 불가 또는 구조 변경
```

---

### 5.2 공공 API로 부동산 실거래가 모니터링하기

국토교통부 API를 이용해 특정 지역의 아파트 실거래가를 자동으로 모니터링하는 워크플로를 만듭니다.

**워크플로 흐름:**
```
Schedule Trigger → HTTP Request(부동산 정보) → Split Out → Edit Fields(데이터 정제) → Edit Fields(uniqueKey) → Google Sheets(기존 데이터 조회) → Merge(중복 제거) → Google Sheets(저장) → IF(조건 필터링) → IF(이전 거래 여부) → 슬랙 알림
```

#### 공공데이터포털에서 Open API 신청하기

1. 공공데이터포털(`data.go.kr`)에 로그인합니다.
2. 검색창에 `부동산 실거래가 정보`를 검색합니다.
3. [오픈API] 탭에서 **국토교통부 아파트 매매 실거래가 상세 자료**의 [활용신청] 버튼을 클릭합니다.
4. 신청 완료 후 **일반 인증키**를 복사하여 보관합니다.

> **콜백 URL:** `https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`

#### 구글 스프레드시트 준비하기

새 구글 스프레드시트를 생성하고, 첫 행에 다음 열 이름을 입력합니다:
`거래일자 | 아파트명 | 위치 | 가격(만원) | 면적(평) | 층 | 준공년도 | 평당가 | 수집일 | 구분값`

시트명을 `거래내역`으로 변경합니다.

#### 공공 API 호출하여 부동산 실거래 내역 가져오기

HTTP Request 노드 설정:
- Method: GET
- URL: `https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`
- Query Parameters:
  - `serviceKey`: 발급받은 인증키
  - `LAWD_CD`: `11680` (강남구)
  - `DEAL_YMD`: `{{ new Date().getFullYear() }}{{ String(new Date().getMonth() + 1).padStart(2, '0') }}`
  - `pageNo`: `1`
  - `numOfRows`: `100`
- Options → Response Format: **JSON**

#### 데이터 정리 및 중복 제거

**Split Out 노드:**
- Fields To Split Out: `response.body.items.item`
- Include: No Other Fields

**Edit Fields 노드 (데이터 정제):**

```javascript
// apartmentName (String)
{{ $json["aptNm"] }}

// price (Number)
{{ Number($json["dealAmount"].replace(/,/g, "").trim()) }}

// area (Number)
{{ ($json["excluUseAr"] / 3.3).toFixed(1) }}

// floor (Number)
{{ $json["floor"] }}

// buildYear (Number)
{{ $json["buildYear"] }}

// location (String)
{{ `${$json["aptDong"] ?? ""} ${$json["bonbun"] ?? ""}-${$json["bubun"] ?? ""}`.trim() }}

// dealDate (String)
{{ (() => {
  const y = $json["dealYear"];
  const m = String($json["dealMonth"]).padStart(2, "0");
  const d = String($json["dealDay"]).padStart(2, "0");
  return `${y}-${m}-${d}`;
})() }}

// pricePerPyeong (Number)
{{ (() => {
  const price = Number($json["dealAmount"].replace(/,/g, "").trim());
  const sqm = Number($json["excluUseAr"]);
  const pyeong = sqm / 3.3;
  return Math.round(price / pyeong);
})() }}
```

**중복 식별자 생성 (Edit Fields 노드):**

```javascript
// uniqueKey (String)
{{ $json.apartmentName + '|' + $json.area + '|' + $json.floor + '|' + $json.dealDate }}
```

Include Other Input Fields: 활성화

#### 데이터 저장 및 조건부 알림

1. **Google Sheets - Get row(s) in sheet:** 기존 거래 내역 불러오기 (Settings → Execute Once 활성화)

2. **Merge 노드:**
   - Mode: Combine → Matching Fields
   - Fields To Match Have Different Names 활성화
   - Input 1 Field: `구분값`, Input 2 Field: `uniqueKey`
   - Output Type: Keep Non-Matches
   - Output Data From: Input 2

3. **Google Sheets - Append row in sheet:** 새 거래 내역 저장

#### 특정 조건 필터링 및 거래 추이 확인

**IF 노드 (관심 매물 필터링):**

```javascript
{{
  Number($('Merge').item.json.price) >= 80000 &&
  Number($('Merge').item.json.price) <= 200000 &&
  Number($('Merge').item.json.area) >= 18 &&
  Number($('Merge').item.json.area) < 35 &&
  Number($('Merge').item.json.floor) > 3 &&
  Number($('Merge').item.json.floor) < 20 &&
  (new Date().getFullYear() - Number($('Merge').item.json.buildYear)) <= 15
}}
```

**Code in JavaScript 노드 (이전 거래 비교):**

```javascript
let rows = [];
let targetApt = null;
let targetArea = null;
let targetDealDate = null;

try {
  // 구글 시트 데이터 읽기
  rows = $items("Get row(s) in sheet");

  // 오늘 수집된 매물 정보
  targetApt = String($json.apartmentName || "").trim();
  targetArea = Number(String($json.area || "").replace(/[^0-9.]/g, ""));
  targetDealDate = String($json.dealDate || "").replace(/[^0-9-]/g, "");

  const todayPrice = Number($json.price);

  // 동일 아파트 + 동일 평형 + 오늘 거래 제외
  const filtered = rows
    .map(i => i.json)
    .filter(r => {
      const apt = String(r["아파트명"] || "").trim();
      const area = Number(String(r["면적(평)"] || "").replace(/[^0-9.]/g, ""));
      const dealDate = String(r["거래일자"]).trim();
      const aptMatch = apt === targetApt;
      const areaMatch = Math.abs(area - targetArea) <= 0.2;
      const isToday = dealDate === targetDealDate;
      return aptMatch && areaMatch && !isToday;
    })
    .sort((a, b) => new Date(a["거래일자"]) - new Date(b["거래일자"]));

  if (filtered.length === 0) {
    return [{ json: { status: "이전 거래 없음", filteredCount: 0, todayPrice } }];
  }

  const lastPastPrice = Number(filtered[filtered.length - 1]["가격(만원)"]);
  const rate = ((todayPrice - lastPastPrice) / lastPastPrice * 100).toFixed(2);

  return [{ json: { status: "이전 거래 있음", filteredCount: filtered.length, todayPrice, lastPastPrice, rate } }];

} catch (error) {
  return [{ json: { status: "error", message: error.message } }];
}
```

슬랙 알림 메시지 (이전 거래 있는 경우):
```
*신규 아파트 거래 알림* 🏠
*{{$('If').item.json.apartmentName}}* {{$('If').item.json.area}}평 | {{$('If').item.json.dealDate}}

💰 오늘 거래가: *{{$json.todayPrice}}만원*
📊 이전 거래가: *{{$json.lastPastPrice}}만원*
📈 변동률: *{{$json.rate}}%*
```

---

### 5.3 증권사 API를 활용한 주식 모니터링 시스템 만들기

한국투자증권 API를 이용하여 원하는 종목의 가격과 거래량을 모니터링하고, 특정 조건에서 디스코드로 알림을 보내는 워크플로를 만듭니다.

**워크플로 흐름:**
```
Schedule Trigger → 토큰 발급 → 주식 현재가 조회 → Edit Fields → 기간별 시세 조회 → Code(평균 거래량 계산) → Edit Fields(거래량 비율) → IF → 공시 조회 → 데이터 정제 → Discord 알림 → Google Sheets 저장
```

#### 디스코드 연동하기

1. 디스코드에서 서버를 생성합니다.
2. [채널 설정 → 연동 → 웹후크 만들기]를 클릭합니다.
3. [웹후크 URL 복사]를 눌러 URL을 보관합니다.
4. n8n에서 [Create Credential → Discord Webhook] 선택 후 Webhook URL을 붙여넣고 저장합니다.

#### 구글 시트 생성하기

새 구글 스프레드시트 생성 후, 첫 행에 입력:
`종목명 | 종목코드 | 현재가 | 오늘거래량 | 거래량비율 | 등락률 | 날짜`

#### 한국투자증권 API 신청하기

1. 한국투자증권 홈페이지에서 [트레이딩 → Open API → KIS Developers → 서비스 신청/조회]로 이동합니다.
2. 계좌를 선택하고 신청을 완료합니다.
3. 생성된 **APP Key**와 **APP Secret**을 복사하여 보관합니다.

> **토큰 발급 방식:** 한국투자증권 API는 OAuth 2.0 Client Credentials 방식을 사용합니다. 토큰 유효기간은 24시간이므로 매일 새로 발급받아야 합니다.

#### 주식 현재가 시세 정보 가져오기

**토큰 발급 (HTTP Request 노드):**

- Method: POST
- URL: `https://openapi.koreainvestment.com:9443/oauth2/tokenP`
- Send Body: JSON
- Body:
  ```json
  {
    "grant_type": "client_credentials",
    "appkey": "YOUR_APP_KEY",
    "appsecret": "YOUR_APP_SECRET"
  }
  ```

**현재가 조회 (HTTP Request 노드):**

- Method: GET
- URL: `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-price`
- Query Parameters:
  - `FID_COND_MRKT_DIV_CODE`: `J`
  - `FID_INPUT_ISCD`: `005930` (삼성전자)
- Headers:
  - `content-type`: `application/json; charset=utf-8`
  - `authorization`: `Bearer {{ $json.access_token }}`
  - `appkey`: YOUR_APP_KEY
  - `appsecret`: YOUR_APP_SECRET
  - `tr_id`: `FHKST01010100`
  - `custtype`: `P`

**데이터 정제 (Edit Fields 노드):**

```javascript
// 종목코드 (String)
{{ $json.output.stck_shrn_iscd }}

// 현재가 (Number)
{{ $json.output.stck_prpr }}

// 등락률 (Number)
{{ $json.output.prdy_ctrt }}

// 오늘거래량 (Number)
{{ $json.output.acml_vol }}

// 날짜 (String)
{{ new Date().toISOString().slice(0, 10) }}
```

#### 최근 20일 평균 시세 확인하기

**기간별 시세 조회 (HTTP Request 노드):**

- URL: `https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice`
- Query Parameters:
  - `FID_COND_MRKT_DIV_CODE`: `J`
  - `FID_INPUT_ISCD`: `005930`
  - `FID_INPUT_DATE_1`: `{{ (() => { const d = new Date(); d.setDate(d.getDate() - 35); return d.toISOString().slice(0,10).replaceAll('-', ''); })() }}`
  - `FID_INPUT_DATE_2`: `{{ new Date().toISOString().slice(0,10).replaceAll('-','') }}`
  - `FID_PERIOD_DIV_CODE`: `D`
  - `FID_ORG_ADJ_PRC`: `0`
- Headers: (토큰 발급과 동일, tr_id는 `FHKST03010100`)

**평균 거래량 계산 (Code in JavaScript 노드):**

```javascript
const rows = Object.values($json.output2 || {});

if (rows.length === 0) {
  return { ...$json, 평균거래량: null };
}

const last20 = rows.slice(0, 20);
const avgVolume = last20.reduce((sum, item) => sum + Number(item.acml_vol), 0) / last20.length;

return { ...$json, 평균거래량: Math.round(avgVolume) };
```

**거래량 비율 계산 (Edit Fields 노드):**

```javascript
// 거래량비율 (Number)
{{ $('Edit Fields').item.json['오늘거래량'] / Number($json['평균거래량']) }}
```

**IF 조건:** `거래량비율 >= 1.5` → `Number → is greater than → 1.5`

#### 전자공시시스템 API 신청하기

1. OpenDART(`dart.fss.or.kr`)에 접속합니다.
2. [인증키 신청/관리 → 인증키 신청]에서 이메일과 비밀번호를 입력하고 신청합니다.
3. [오픈API 이용현황]에서 **API Key**를 복사합니다.

**공시 조회 (HTTP Request 노드):**

- URL: `https://opendart.fss.or.kr/api/list.json`
- Query Parameters:
  - `crtfc_key`: OpenDART API 인증키
  - `corp_code`: `00126380` (삼성전자 고유번호)
  - `bgn_de`: `{{ $now.minus({days: 7}).toFormat('yyyyMMdd') }}`
  - `end_de`: `{{ $now.toFormat('yyyyMMdd') }}`
  - `page_count`: `10`

**데이터 정제:**

1. Split Out 노드: `list` 배열 분리
2. Edit Fields: `{{ $json.report_nm }}({{ $json.rcept_dt }})` 형태로 공시 정보 재구성
3. Aggregate 노드: `report_nm` 필드를 배열로 집계

#### 디스코드로 알림 보내기

Discord 노드 설정:
- Connection Type: **Webhook**
- Message: `**{{ $json['종목명'] }} 거래량 급증!**`

Embeds 설정:
- Title: `{{ $json['종목명'] }} ({{ $json['종목코드'] }})`
- Description:
  ```
  평소 대비 **{{$json['거래량비율'].toFixed(1)}}배** 거래량 급증 📈
  **현재가**: {{$json.현재가}}원
  **등락률**: {{$json.등락률}}%
  **오늘거래량**: {{$json.거래량}}
  **최근 공시**: {{$json.공시목록}}
  ```
- Color: `{{ $json.등락률 >= 0 ? 3066993 : 15158332 }}`
- Timestamp: `{{ $now.toISO() }}`

---

---

# 레벨 3. AI 에이전트 프로젝트 만들기

> **학습 목표**
> 오픈AI API를 연동하고 Memory 기능을 부여하여 문맥을 이해하는 대화형 에이전트를 설계합니다. SerpAPI와 Apify를 연결해 실시간 정보를 스스로 수집하고 판단하는 능동형 AI를 구현합니다. 외부 지식을 검색하여 답변하는 RAG 아키텍처의 원리와 텍스트를 벡터로 변환하는 임베딩 기술을 심층적으로 학습합니다.

---

## 06장. 검색 기능을 가진 에이전트 설계하기

> **학습 목표**
> 오픈AI 챗GPT API를 n8n에 연동하고, 메모리 기능을 추가하여 이전 대화의 맥락을 기억하는 AI 에이전트를 설계합니다. SerpAPI를 도구로 연결하여 AI가 실시간 인터넷 검색 결과를 바탕으로 최신 정보에 기반한 답변을 생성하도록 만듭니다.

---

### 6.1 챗GPT API 알아보기

오픈AI에서 제공하는 챗GPT API를 사용하면 n8n과 같이 외부 툴에서 챗GPT를 호출하여 자신만의 AI 프로그램을 만들 수 있습니다.

#### 사용할 수 있는 GPT 모델

| 모델 | 특징 |
|------|------|
| **GPT-4.1** | 복잡한 작업을 위한 가장 스마트한 모델 |
| **GPT-4.1 mini** | 속도와 인텔리전스의 균형을 맞춘 합리적인 모델 |
| **GPT-4.1 nano** | 지연 시간이 짧은 작업을 위한 가장 빠르고 비용효율적인 모델 |

#### 과금 구조 (GPT-4.1 카테고리)

| 모델 | 입력 (100만 토큰당) | 출력 (100만 토큰당) |
|------|---------------------|---------------------|
| GPT-4.1 | $2.00 | $8.00 |
| GPT-4.1 mini | $0.40 | $1.60 |
| GPT-4.1 nano | $0.10 | $0.40 |

- **context window:** 1,047,576 토큰 (약 100만 토큰)
- **max output tokens:** 32,768 토큰
- **knowledge cutoff:** 2024년 6월 1일

> **토큰이란?** 챗GPT가 인식하는 단어 단위입니다. 예를 들어 `I am a student.`는 5개의 토큰으로 인식됩니다.

---

### 6.2 챗GPT API Key 발급하기

1. 오픈AI 플랫폼(`platform.openai.com`)에 접속하여 회원가입 후 로그인합니다.
2. [API Keys → + Create new secret key]를 클릭합니다.
3. 키를 복사하여 안전한 곳에 보관합니다.

> ⚠️ API 키가 유출되면 다른 사람이 내 계정으로 API를 사용하여 과금이 발생할 수 있습니다.

4. [Billing → Add payment details]에서 결제 수단을 등록합니다.
5. [Add to credit balance]에서 선결제 금액을 충전합니다 (최소 $5 이상 권장).

---

### 6.3 GPT 연동 워크플로 만들기

#### GPT-4.1 mini 연동하기

1. 새 워크플로를 만들고 트리거 노드로 [On chat message]를 선택합니다.
2. [AI Agent] 노드를 추가합니다.
3. Chat Model의 [+] 버튼을 클릭하여 [OpenAI Chat Model]을 선택합니다.
4. [+ Create new credential]을 클릭하고 API Key를 입력한 후 저장합니다.
5. Model에서 `gpt-4.1-mini`를 선택합니다.
6. 트리거 노드의 [Open chat] 버튼을 클릭하여 대화를 시작합니다.

#### 에이전트에 기억력 부여하기

기본 상태에서는 이전 대화를 기억하지 못합니다. 메모리 기능을 추가합니다.

1. AI Agent의 Memory 라인 [+] 버튼을 클릭합니다.
2. [Simple Memory]를 선택합니다.
3. **Context Window Length** 설정: 기본값 5 (현재 시점 기준 이전 대화 5개 기억)

> Context Window Length를 크게 설정할수록 더 많은 이전 대화가 입력 토큰으로 계산되어 과금이 증가합니다. 5 이하의 값을 권장합니다.

---

### 6.4 검색 기능 추가하기

#### SerpAPI 회원가입 및 키 발급

1. SerpAPI(`serpapi.com`)에 접속하여 회원가입합니다.
2. 무료 플랜은 월 250회 검색이 가능합니다.
3. [Your Account → API Key]를 복사하여 보관합니다.

#### 에이전트와 검색기의 연동

1. AI Agent의 Tool 라인 [+] 버튼을 클릭합니다.
2. `serpapi`를 검색하여 [SerpAPI (Google Search)]를 선택합니다.
3. [+ Create new credential]을 클릭하고 API Key를 입력한 후 저장합니다.

완성된 에이전트 구조:
```
When chat message received
     ↓
  AI Agent
 ┌──┬──┬──┐
Model Memory Tool
 │         │
OpenAI    Simple   SerpAPI
Chat      Memory
Model
```

**동작 원리:**
- 사용자가 질문을 입력합니다.
- AI가 질문을 분석하여 검색이 필요한지 판단합니다.
- 필요하다면 SerpAPI를 통해 구글 검색을 수행합니다.
- 검색 결과를 바탕으로 최종 답변을 작성합니다.

> **참고:** SerpAPI 버그 발생 시 n8n 템플릿(`n8n.io/workflows/1954-ai-agent-chat/`)에서 워크플로를 복사하여 사용할 수 있습니다.

---

## 07장. 유튜브 영상 요약 에이전트 설계하기

> **학습 목표**
> RSS Feed Trigger를 사용하여 특정 유튜브 채널에 새로운 영상이 업로드되는 즉시 워크플로가 실행되도록 설정합니다. Apify를 활용해 영상의 자막을 텍스트로 추출하고, 이를 AI 모델에 전달하여 핵심 내용을 요약하게 만듭니다.

---

### 7.1 유튜브 영상 스크래핑하기

#### RSS란?

RSS(Really Simple Syndication)는 뉴스나 블로그 같은 웹사이트에서 콘텐츠를 배포하기 위해 사용하는 표준 형식입니다. 새 콘텐츠가 올라오면 RSS 피드 주소가 자동으로 업데이트됩니다.

**유튜브 채널의 RSS 피드 주소 형식:**
```
https://www.youtube.com/feeds/videos.xml?channel_id=채널ID
```

**채널 ID 확인 방법:**
1. 유튜브 채널 페이지에서 [...더보기]를 클릭합니다.
2. [채널 공유 → 채널 ID 복사]를 선택합니다.

#### RSS Feed Trigger 노드 설정하기

- 노드 선택: [RSS Feed Trigger]
- Feed URL: 유튜브 채널의 RSS 피드 주소 입력
- Poll Times: Every Minute

[Fetch Test Event] 버튼을 클릭하면 가장 최근 동영상 정보가 OUTPUT에 표시됩니다. `link` 키에 최근 동영상 URL이 저장되어 있습니다.

#### Apify 설정하기

1. Apify(`apify.com`)에 접속하여 회원가입합니다.
2. [Settings → API & Integrations]에서 **Default API token**을 복사합니다.
3. [Apify Store]에서 `YouTube Scraper`를 검색합니다.
4. [Input] 탭에서 다음을 설정합니다:
   - Download subtitles: **활성화**
   - Subtitle language: **Any**
   - Subtitle format: **plaintext**
5. [API → Run Actor synchronously and get dataset items]의 URL을 복사합니다:
   ```
   https://api.apify.com/v2/acts/streamers-youtube-scraper/run-sync-get-dataset-items?token=YOUR_API_KEY
   ```

#### HTTP 노드 설정하기

RSS Feed Trigger 다음에 HTTP Request 노드를 추가합니다.

- Method: POST
- URL: 위에서 복사한 Apify URL
- Send Body: 활성화
- Body Content Type: JSON
- Specify Body: Using JSON
- JSON 입력 (Expression 모드):

```json
{
  "downloadSubtitles": true,
  "paste": false,
  "startUrls": [{"url": "{{ $json.link }}"}],
  "subtitlesFormat": "plaintext",
  "subtitlesLanguage": "any"
}
```

---

### 7.2 영상 요약 에이전트 만들기

#### 에이전트 연결하기

HTTP Request 노드 다음에 AI Agent 노드를 추가합니다.

1. Chat Model에 [OpenAI Chat Model] 연결:
   - Model: `gpt-4.1-mini`

2. AI Agent 설정:
   - Source for Prompt: **Define below**
   - Prompt (Expression 모드):

```
Summarize the transcript below.

{{ $json.title }}

{{ $json.subtitles[0].plaintext }}
```

#### 지메일 노드로 이메일 보내기

AI Agent 다음에 [Gmail → Send a message] 노드를 추가합니다.

- To: 수신할 이메일 주소
- Subject: `오늘의 유튜브 요약`
- Message: `{{ $json.output }}`

---

## 08장. PDF만 넣으면 완성되는 우리 회사 챗봇 만들기

> **학습 목표**
> 구글 드라이브에 업로드된 PDF 문서를 n8n으로 불러와 텍스트로 읽어낸 뒤, 이를 적절한 크기로 잘라 AI가 학습하기 좋은 형태의 문서 데이터로 가공합니다. 벡터 데이터베이스인 Pinecone 환경을 구축하고 오픈AI의 임베딩 모델을 연동하여, 전처리된 문서 데이터를 벡터로 변환해 인덱스에 적재하는 자동화 워크플로를 구현합니다.

---

### 8.1 RAG 이해하기

#### RAG 챗봇이란?

RAG(Retrieval Augmented Generation, 검색 증강 생성)는 AI 챗봇의 한계를 해결하기 위해 만들어졌습니다.

- **일반 챗봇의 한계:** 학습 데이터 이후의 최신 정보나 회사 내부 자료에 대해 정확한 답변을 하기 어렵습니다.
- **RAG의 해결 방법:** 사용자가 질문하면 관련 자료에서 필요한 정보를 검색하고, 그 정보를 바탕으로 정확한 답변을 생성합니다.

**RAG의 장점:**
- **신뢰성:** 추측이 아닌 실제 문서를 바탕으로 답변
- **최신성:** 새로운 자료가 추가되면 최신 정보로 답변 가능

#### 임베딩과 유사도

**임베딩(Embedding)**은 텍스트를 벡터(숫자의 배열)로 변환하는 과정입니다.

```
'사과' → 단어 임베딩 → 벡터: [0.12, 0.34, 0.75, -0.12]
'안녕하세요' → 문장 임베딩 → 벡터: [0.57, 0.25, 0.85, 3.24]
```

임베딩된 벡터들 사이에서 **코사인 유사도**를 계산하면 텍스트 간의 의미적 유사도를 정량적으로 구할 수 있습니다. 값의 범위는 -1에서 1 사이이며, 1에 가까울수록 유사도가 높습니다.

**임베딩 기반 검색의 핵심 장점:**
- 단어가 직접적으로 겹치지 않아도 의미가 유사하면 연결해줍니다.
- 예: '꼬르륵 소리가 난다' → '배고픔'과 관련된 문서 검색

이처럼 텍스트 데이터를 임베딩하여 보관하고, 새로운 입력에 대해 유사도를 계산하는 전문 도구를 **벡터 데이터베이스(Vector DB)**라고 합니다.

---

### 8.2 벡터 검색을 활용한 RAG 시스템 만들기

#### 구글 드라이브 데이터 연동하기

1. 구글 드라이브에 `rag`라는 폴더를 생성하고 PDF 파일들을 업로드합니다.
2. n8n에서 새 워크플로를 만들고 [Trigger Manually] 노드를 추가합니다.
3. [Google Drive → Search files and folders] 노드를 추가합니다:
   - Resource: File/Folder
   - Operation: Search
   - Return All: 활성화
   - Filter → Folder: `rag`

4. [Google Drive → Download file] 노드를 추가합니다:
   - Resource: File
   - Operation: Download
   - File → By ID: `{{ $json.id }}`

#### Pinecone 환경 설정하기

**Pinecone 가입:**

1. Pinecone(`pinecone.io`)에 접속하여 회원가입합니다.
2. 가입 완료 후 생성된 **API Key**를 복사합니다.

**인덱스(Index) 생성:**

1. [Indexes → Create index]를 클릭합니다.
2. 설정:
   - Index 이름: `rag-index`
   - 임베딩 모델: `text-embedding-3-large` (OpenAI)
   - Dimension: `3072`
   - Capacity mode: Serverless
   - Cloud provider: AWS
   - Region: Virginia (us-east-1)
3. [Create index]를 클릭합니다.

#### PDF 데이터 전처리하기

n8n 워크플로에 다음 순서로 노드를 연결합니다:

```
Trigger Manually
→ Search files and folders (Google Drive)
→ Download file (Google Drive)
→ Loop Over Items
  → Pinecone Vector Store (Add documents)
     ├─ Embeddings OpenAI (text-embedding-3-large)
     └─ Default Data Loader
           └─ Recursive Character Text Splitter
```

**Loop Over Items 노드:**
- Batch Size: 1

**Pinecone Vector Store 노드:**
- Operation Mode: Insert Documents
- Pinecone Index: `rag-index`
- Options → Pinecone Namespace: `travel`

**Embeddings OpenAI 노드:**
- Model: `text-embedding-3-large`

**Default Data Loader 노드:**
- Type of Data: Binary
- Mode: Load All Input Data
- Data Format: Automatically Detect by MimeType
- Text Splitting: **Custom**

**Recursive Character Text Splitter 노드:**
- Chunk Size: `1000`

> **Chunk Size란?** PDF 파일의 전체 내용을 약 1,000자씩 나누어 여러 개의 작은 문서로 자르는 설정입니다. 너무 작으면 정보가 부족하고, 너무 크면 불필요한 정보가 섞입니다.

**Pinecone Vector Store 뒤에 Loop Over Items Input으로 연결**하여 반복 처리합니다.

[Execute workflow]를 실행하면 PDF 파일들이 전처리되어 벡터 데이터베이스에 적재됩니다.

#### RAG 챗봇 만들기

같은 캔버스에 새로운 노드 그룹을 추가합니다.

**1. 트리거 노드:** [On chat message]

**2. Question and Answer Chain 노드:**

```
When chat message received
     ↓
Question and Answer Chain
 ┌─────────────────────┐
Model              Retriever
 │                     │
OpenAI Chat        Vector Store Retriever
Model (gpt-4.1)         │
                  Pinecone Vector Store
                         │
                  Embeddings OpenAI
                  (text-embedding-3-large)
```

**설정 상세:**

- **OpenAI Chat Model:** Model = `gpt-4.1`

- **Pinecone Vector Store (Retriever용):**
  - Operation Mode: Retrieve Documents (As Vector Store for Chain/Tool)
  - Pinecone Index: `rag-index`
  - Options → Pinecone Namespace: `travel`

- **Embeddings OpenAI (Retriever용):**
  - Model: `text-embedding-3-large`

> ⚠️ 데이터 적재 시와 동일한 임베딩 모델을 사용해야 유사도를 정확히 계산할 수 있습니다.

**동작 원리:**

1. 사용자가 질문을 입력합니다.
2. 질문이 `text-embedding-3-large` 모델을 통해 벡터로 변환됩니다.
3. Pinecone에서 유사도 상위 4개의 문서를 검색합니다.
4. LLM에 다음과 같은 형태로 전달됩니다:
   ```
   System: 당신은 질문-답변 작업을 위한 어시스턴트입니다. 다음에 제공된 맥락을 사용하여 질문에 답하세요. 답을 모르면 모른다고 말하고, 답을 지어내지 마세요.

   Context: [검색된 4개 문서]

   Human: [사용자 질문]
   ```
5. LLM이 검색된 문서를 기반으로 답변을 생성합니다.

---

## 찾아보기

| 용어 | 설명 |
|------|------|
| **AI Agent** | 도구를 사용하여 스스로 판단하고 행동하는 AI 에이전트 노드 |
| **Always Output Data** | 노드 실패 시에도 이전 데이터를 다음 노드로 전달하는 옵션 |
| **Apify** | 웹 스크래핑 플랫폼 (YouTube Scraper 등 제공) |
| **Chunk Size** | 텍스트를 분할할 때의 최대 문자 수 |
| **Context Window Length** | Simple Memory에서 기억할 이전 대화의 개수 |
| **Edit Fields** | 데이터를 생성하거나 수정하는 기본 노드 |
| **Evaluations** | AI 워크플로의 성능을 평가하는 n8n 기능 |
| **Execute Once** | 입력이 여러 개여도 노드를 한 번만 실행하는 옵션 |
| **Execute step** | 특정 노드만 단독으로 실행하는 버튼 |
| **Execute workflow** | 전체 워크플로를 테스트 실행하는 버튼 |
| **Executions** | 워크플로 실행 기록을 확인하는 탭 |
| **HTTP Request** | 외부 웹사이트나 API와 통신하는 핵심 노드 |
| **If 노드** | 조건을 평가하여 true/false로 분기하는 노드 |
| **JSON** | n8n에서 모든 데이터를 처리하는 기본 데이터 형식 |
| **Loop over Items** | 여러 아이템을 순차적으로 처리하는 제어 노드 |
| **OAuth 동의 화면** | 구글 API 연동 시 필요한 앱 인증 화면 |
| **On Error** | 오류 발생 시 처리 방법을 선택하는 옵션 |
| **Parameters** | 노드의 동작을 설정하는 핵심 옵션들 |
| **Pinecone** | 벡터 데이터베이스 서비스 |
| **RAG** | Retrieval Augmented Generation, 검색 증강 생성 |
| **Recursive Character Text Splitter** | 텍스트를 일정 크기로 분할하는 노드 |
| **Retry On Fail** | 노드 실패 시 자동 재시도 옵션 |
| **RSS Feed Trigger** | RSS 피드에 새 항목이 추가될 때 실행되는 트리거 |
| **Schema** | 필드명과 값을 시각적으로 구분하여 보여주는 데이터 보기 옵션 |
| **SerpAPI** | 구글 검색 결과를 제공하는 API 서비스 |
| **Simple Memory** | n8n 내장 메모리로 이전 대화를 기억하는 노드 |
| **Switch 노드** | 여러 조건으로 분기할 때 사용하는 노드 |
| **Text Splitter** | 긴 텍스트를 작은 조각으로 분할하는 노드 |
| **User-Agent** | 웹 스크래핑 시 봇 차단을 방지하기 위해 전달하는 브라우저 식별 정보 |
| **Wait 노드** | 워크플로 실행을 일시정지하는 제어 노드 |
| **구글 클라우드 콘솔** | 구글 API 설정 및 관리 플랫폼 |
| **깃(Git)** | 스타터 키트 설치에 필요한 버전 관리 도구 |
| **네임스페이스** | 벡터 데이터베이스 내 논리적 격리 공간 |
| **노드** | 워크플로를 구성하는 각 단계나 작업 단위 |
| **도커(Docker)** | 프로그램을 독립적인 컨테이너에서 실행하는 기술 |
| **매뉴얼 트리거** | 사용자가 직접 클릭하면 실행되는 트리거 노드 |
| **벡터 데이터베이스** | 임베딩된 벡터를 저장하고 유사도 검색을 수행하는 DB |
| **스타터 키트** | n8n 로컬 설치에 필요한 설정이 사전 구성된 템플릿 |
| **오픈API** | 공공데이터포털에서 제공하는 공개 API |
| **워크플로** | n8n에서 자동화 프로세스를 구성하는 기본 단위 |
| **인덱스** | Pinecone에서 벡터 데이터를 저장하고 검색하는 단위 |
| **임베딩** | 텍스트를 벡터(숫자의 배열)로 변환하는 과정 |
| **입력 포트 / 출력 포트** | 노드 간 데이터가 전달되는 연결 지점 |
| **전자공시시스템(DART)** | 금융감독원에서 운영하는 기업 공시 정보 시스템 |
| **조건식** | n8n 표현식에서 조건 분기에 사용하는 삼항 연산자 |
| **트리거 노드** | 워크플로를 시작하는 조건이나 신호를 담당하는 노드 |
| **표현식** | 워크플로 실행 시 동적으로 계산되는 값을 작성하는 코드 (`{{ ... }}`) |
| **필드명** | JSON에서 값에 해당하는 키(이름) |
| **활성화** | 워크플로를 실제로 작동시키는 상태로 전환 |