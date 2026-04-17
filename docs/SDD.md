# Themis — Spec-Driven Development Document

**Project:** Themis — An Agentic RAG System for Data Protection Law (LGPD with GDPR extensibility)
**Type:** Portfolio Project (Tier 1 Big Tech — AI/ML Engineer)
**Author:** [Gabriel Morett]
**Version:** 1.0
**Target duration:** 5–7 semanas (part-time, ~15–20h/semana)

---

## Table of Contents

1. [Visão Geral e Objetivos](#1-visão-geral-e-objetivos)
2. [Requisitos Funcionais e Não-Funcionais](#2-requisitos-funcionais-e-não-funcionais)
3. [Arquitetura de Alto Nível](#3-arquitetura-de-alto-nível)
4. [Stack Tecnológica](#4-stack-tecnológica)
5. [Roadmap em Fases (Ordem de Implementação)](#5-roadmap-em-fases)
6. [Detalhamento por Fase](#6-detalhamento-por-fase)
7. [Estratégia de Avaliação](#7-estratégia-de-avaliação)
8. [Observabilidade e Monitoramento](#8-observabilidade-e-monitoramento)
9. [Segurança e Responsible AI](#9-segurança-e-responsible-ai)
10. [Custo Estimado](#10-custo-estimado)
11. [Entregáveis e Artefatos de Portfolio](#11-entregáveis-e-artefatos-de-portfolio)
12. [Riscos e Mitigações](#12-riscos-e-mitigações)
13. [Critérios de Conclusão](#13-critérios-de-conclusão)

---

## 1. Visão Geral e Objetivos

### 1.1 Problema

Profissionais de tecnologia, compliance e jurídico precisam navegar diariamente a LGPD (Lei Geral de Proteção de Dados, Lei 13.709/2018), regulamentações da ANPD, decisões administrativas e comparar com GDPR para operações multinacionais. Consultas diretas a LLMs genéricos produzem respostas sem citação, sujeitas a alucinação, e sem rastreabilidade — inaceitável em contexto regulatório.

### 1.2 Solução

**Themis** é um sistema agentic de RAG especializado em proteção de dados, que responde perguntas com:
- Citação obrigatória e verificável de fontes primárias
- Decomposição agentic de queries complexas (múltiplos agentes especializados)
- Grounding rigoroso (recusa graciosa quando não há base documental)
- Comparação cross-jurisdictional LGPD ↔ GDPR
- Audit trail completo e observabilidade de custo/latência

### 1.3 Objetivos do Projeto (como portfolio)

**Objetivo primário:** demonstrar competência end-to-end de AI/ML Engineer em nível tier 1, incluindo RAG avançado, agentes, avaliação rigorosa, deploy em nuvem, observabilidade e engenharia de software séria.

**Objetivo secundário:** servir como artefato técnico defensável em entrevistas, com documentação de decisões arquiteturais, trade-offs, e resultados mensuráveis.

**Não-objetivo:** ser um produto comercial pronto ou substituir aconselhamento jurídico profissional.

### 1.4 Personas

- **Developer/Engenheiro:** precisa entender requisitos técnicos de LGPD (ex: consent management, data retention)
- **DPO/Compliance Officer:** compara LGPD e GDPR, busca precedentes da ANPD
- **Founder/Produto:** entende obrigações básicas sem precisar ler a lei inteira

---

## 2. Requisitos Funcionais e Não-Funcionais

### 2.1 Requisitos Funcionais

**RF-01** — Ingestão e indexação do texto completo da LGPD, regulamentações da ANPD, decisões administrativas, e GDPR para comparação.

**RF-02** — Interface de chat com streaming de respostas (web UI + API REST).

**RF-03** — Toda resposta factual deve incluir citações verificáveis (artigo + lei + link para fonte).

**RF-04** — Sistema deve recusar responder quando não há base documental ("hallucination refusal").

**RF-05** — Decomposição agentic: queries complexas são divididas entre agentes especializados (retriever, comparator, calculator, synthesizer).

**RF-06** — Tools disponíveis aos agentes: busca vetorial na base, busca em jurisprudência/decisões ANPD, calculadora de prazos regulatórios, comparador LGPD-GDPR, verificador de requisitos para caso específico.

**RF-07** — Cache semântico para queries recorrentes.

**RF-08** — Rate limiting por usuário (IP/API key).

**RF-09** — Histórico de conversas persistente com opção de exclusão (right-to-be-forgotten — dogfooding).

**RF-10** — Dashboard de observabilidade (traces, custos, latência, qualidade).

### 2.2 Requisitos Não-Funcionais

**RNF-01 (Latência)** — P50 < 3s para queries simples (cached); P95 < 8s para queries agentic complexas.

**RNF-02 (Custo)** — Custo médio por query < $0.02 USD (usando roteamento inteligente de modelos).

**RNF-03 (Qualidade)** — Em dataset de eval interno (~100 queries):
- Citation accuracy ≥ 95% (citações verificáveis e corretas)
- Faithfulness ≥ 90% (resposta fiel ao contexto recuperado)
- Answer relevancy ≥ 85%
- Hallucination rate < 5%

**RNF-04 (Segurança)** — PII redaction em logs, prompt injection detection, guardrails de output.

**RNF-05 (Observabilidade)** — 100% das requisições tracked com tracing distribuído.

**RNF-06 (Disponibilidade)** — Sistema deployado e publicamente acessível (URL funcional).

**RNF-07 (Reprodutibilidade)** — Build determinístico via Docker; qualquer avaliador pode rodar localmente em < 15 min.

**RNF-08 (Extensibilidade GDPR)** — Arquitetura permite plugar corpus GDPR e responder queries cross-jurisdictional sem refactor.

---

## 3. Arquitetura de Alto Nível

### 3.1 Diagrama Conceitual (descrição textual)

```
[User] → [Web UI / API Gateway]
           ↓
     [Rate Limiter + Auth]
           ↓
     [Guardrails Input Layer]  ← detecta prompt injection, PII
           ↓
     [Query Router Agent]       ← classifica: simples / complexa / fora de escopo
           ↓
     ┌─────┴─────────────────────────┐
     ↓                               ↓
[Fast Path: Haiku + Cache]    [Agentic Orchestrator — LangGraph]
                                     ↓
                         ┌───────────┼───────────┬──────────┐
                         ↓           ↓           ↓          ↓
                  [Retriever   [Comparator  [Calculator  [Synthesizer
                   Agent]       Agent]       Agent]       Agent]
                         ↓           ↓           ↓          ↓
                  Vector DB     Cross-ref    Prazo ANPD   Final response
                  (Qdrant)      LGPD-GDPR    rules
                         ↓
                  [Reranker — Cross-Encoder]
                         ↓
                  [Citation Verifier]
                         ↓
     [Guardrails Output Layer]  ← verifica citation, refusal, PII leak
           ↓
     [Response Streaming] → User

Observability (cross-cutting):
 - Langfuse (LLM tracing, cost, latency)
 - CloudWatch (infra metrics)
 - Postgres (conversations, audit log)
```

### 3.2 Componentes Principais

- **API Layer:** FastAPI com streaming (SSE)
- **Orchestration:** LangGraph (state machine de agentes)
- **Retrieval:** Hybrid search (BM25 + dense) no Qdrant + reranking com cross-encoder
- **LLM Routing:** Bedrock (Claude Haiku para queries simples, Claude Sonnet para síntese complexa); Ollama local em dev
- **Embeddings:** `BAAI/bge-m3` (multilingual, suporta PT-BR e EN) ou Bedrock Titan Embeddings
- **Vector Store:** Qdrant (self-hosted em dev, Qdrant Cloud tier grátis em prod)
- **Metadata Store:** Postgres (RDS Free Tier)
- **Cache:** Redis (ElastiCache ou container)
- **Observability:** Langfuse (self-hosted) + CloudWatch
- **Deploy:** Docker Compose (dev) + AWS ECS Fargate (prod)

### 3.3 Fluxo de uma Query Complexa (Exemplo)

**User:** "Posso usar legítimo interesse para marketing direto de dados biométricos? Como isso muda entre LGPD e GDPR?"

1. Guardrails input: OK (sem injection, sem PII)
2. Router classifica: COMPLEXA (comparação cross-jurisdictional + categoria especial de dados)
3. Orchestrator aciona:
   - **Retriever Agent:** busca "legítimo interesse", "dados biométricos", "dados sensíveis" na base LGPD
   - **Retriever Agent (paralelo):** busca correspondentes no GDPR
   - **Comparator Agent:** identifica diferenças em bases legais e categorias especiais
   - **Synthesizer Agent:** monta resposta com citações e nota comparativa
4. Citation Verifier checa que cada citação aponta para documento real
5. Guardrails output: verifica que há citações, que não vazou PII do contexto
6. Stream da resposta pro usuário
7. Trace completo loggado no Langfuse com breakdown de custo

---

## 4. Stack Tecnológica

### 4.1 Linguagem e Frameworks
- **Python 3.11+** (produção)
- **FastAPI** (API REST + SSE streaming)
- **Pydantic v2** (validação e settings)
- **LangGraph** (agent orchestration)
- **LangChain** (componentes auxiliares, mas não como spine — LangGraph é o spine)

### 4.2 LLM e AI
- **Prod:** AWS Bedrock (Claude Haiku 3.5 + Claude Sonnet 4)
- **Dev:** Ollama (Llama 3.1 8B ou Qwen 2.5 7B localmente)
- **Embeddings:** BAAI/bge-m3 via HuggingFace (local) ou Bedrock Titan (prod)
- **Reranker:** BAAI/bge-reranker-v2-m3 (cross-encoder)

### 4.3 Armazenamento
- **Vector DB:** Qdrant
- **Relational:** PostgreSQL 16 (conversations, users, audit log, eval results)
- **Cache:** Redis 7
- **Object storage:** S3 (raw documents, eval datasets)

### 4.4 Avaliação
- **RAGAS** (faithfulness, answer relevancy, context precision/recall)
- **DeepEval** (custom metrics, G-Eval)
- **Dataset próprio:** ~100 queries anotadas manualmente

### 4.5 Observability
- **Langfuse** (LLM-specific tracing, cost, token usage, eval tracking)
- **Prometheus + Grafana** (métricas de infra, opcional)
- **AWS CloudWatch** (logs centralizados)
- **OpenTelemetry** (tracing distribuído)

### 4.6 DevOps / Infra
- **Docker + Docker Compose** (local dev)
- **AWS ECS Fargate** (deploy produção)
- **AWS RDS Postgres** (Free Tier)
- **AWS S3** (storage)
- **AWS Bedrock** (LLM em prod)
- **GitHub Actions** (CI/CD)
- **Terraform** (IaC — opcional mas recomendado)

### 4.7 Qualidade de Código
- **ruff** (linting + formatting)
- **mypy** (type checking)
- **pytest** (unit + integration tests)
- **pre-commit** hooks

### 4.8 Frontend (mínimo)
- **Next.js 14** (App Router) + **Tailwind** + **shadcn/ui**
- Apenas chat interface, histórico, e dashboard simples

---

## 5. Roadmap em Fases

Ordem estritamente sequencial. Cada fase tem critérios de "done" antes de avançar.

| Fase | Nome | Duração | Objetivo |
|------|------|---------|----------|
| 0 | Setup e Foundations | 3–4 dias | Repo, tooling, estrutura base |
| 1 | Data Ingestion Pipeline | 5–7 dias | Corpus LGPD+ANPD indexado e consultável |
| 2 | RAG Baseline (sem agentes) | 5–7 dias | Sistema end-to-end básico funcionando |
| 3 | Evaluation Framework | 4–6 dias | Dataset + métricas + CI-integrated evals |
| 4 | Agentic Orchestration | 7–10 dias | Multi-agent com LangGraph |
| 5 | Optimization (custo/latência) | 4–6 dias | Cache, routing, streaming, benchmarks |
| 6 | Guardrails e Security | 3–5 dias | Input/output guardrails, PII, injection |
| 7 | Observability | 3–4 dias | Langfuse + dashboards + alerts |
| 8 | Frontend Mínimo | 3–5 dias | Chat UI + history + dashboard |
| 9 | Deploy AWS | 4–6 dias | Produção com URL pública |
| 10 | GDPR Extension | 3–5 dias | Corpus GDPR + cross-jurisdictional |
| 11 | Documentation Polish | 2–3 dias | README, ARCHITECTURE, EVAL reports |

**Total estimado:** 5–7 semanas em ritmo part-time intenso.

---

## 6. Detalhamento por Fase

### FASE 0 — Setup e Foundations (3–4 dias)

#### Objetivos
Estabelecer fundação de engenharia antes de escrever lógica de negócio.

#### Tarefas
1. **Criar repositório GitHub** `themis` (público, com README chamativo mesmo que WIP)
2. **Estrutura de monorepo:**
   ```
   themis/
   ├── apps/
   │   ├── api/          # FastAPI backend
   │   └── web/          # Next.js frontend (Fase 8)
   ├── packages/
   │   ├── core/         # lógica de domínio
   │   ├── rag/          # retrieval + generation
   │   ├── agents/       # LangGraph agents
   │   ├── evals/        # eval framework
   │   └── ingestion/    # data pipeline
   ├── infra/            # Terraform, Docker
   ├── docs/             # ARCHITECTURE.md, DECISIONS.md, etc.
   ├── data/             # raw + processed (gitignored exceto samples)
   ├── tests/
   ├── docker-compose.yml
   ├── pyproject.toml
   └── README.md
   ```
3. **Tooling:**
   - `uv` como package manager (mais rápido que pip)
   - `ruff`, `mypy`, `pytest` configurados
   - `pre-commit` com hooks
   - `.env.example` template
4. **Docker Compose local:**
   - Postgres, Redis, Qdrant, Langfuse (self-hosted), Ollama
5. **GitHub Actions básico:**
   - Lint + typecheck + tests em PRs
6. **Architecture Decision Records (ADRs):**
   - Criar `docs/decisions/` com template
   - Primeiro ADR: "Why LangGraph over CrewAI/AutoGen"
   - Segundo ADR: "Why Qdrant over pgvector"
7. **README inicial com:**
   - Problem statement
   - Screenshot placeholder
   - Quick start
   - Status badges

#### Definition of Done
- [ ] `docker-compose up` sobe toda a stack local
- [ ] CI verde em PR de teste
- [ ] 2+ ADRs escritos
- [ ] README claro o suficiente para outro dev rodar localmente

---

### FASE 1 — Data Ingestion Pipeline (5–7 dias)

#### Objetivos
Construir pipeline robusto de ingestão, chunking, embedding e indexação do corpus.

#### Corpus a ingerir (ordem de prioridade)
1. **LGPD** — Lei 13.709/2018 (texto oficial do Planalto)
2. **Regulamentações ANPD** — resoluções, guias, pareceres (site anpd.gov.br)
3. **Decisões ANPD** — sanções aplicadas, casos públicos
4. **Guias complementares** — MPF, ENIDH, cartilhas oficiais
5. **(Fase 10) GDPR** — Regulation (EU) 2016/679 + EDPB guidelines

#### Tarefas
1. **Scrapers/loaders por fonte:**
   - Planalto (HTML → texto estruturado por artigo)
   - ANPD (HTML scraping respeitoso com rate limit)
   - PDFs das decisões (usar `pdfplumber` ou `pypdf`)
2. **Normalização:**
   - Um schema unificado: `{id, source, doc_type, title, article_num, text, date, jurisdiction, metadata}`
   - Preservar estrutura hierárquica (Capítulo → Seção → Artigo → Parágrafo → Inciso)
3. **Chunking strategy:**
   - **Nível 1:** chunk natural (1 artigo = 1 chunk, com metadata rica)
   - **Nível 2:** se artigo > 500 tokens, split em parágrafos mantendo contexto pai
   - Experimentar: semantic chunking vs fixed-size vs estrutural (logar no ADR)
4. **Embedding:**
   - Usar `bge-m3` (multilingual, 1024 dims)
   - Batch embedding com rate limit
   - Store: vector + metadata completa no Qdrant
5. **Indexação híbrida:**
   - Dense: Qdrant collection
   - Sparse: BM25 via Qdrant sparse vectors OU Postgres com tsvector PT-BR
6. **Validação do corpus:**
   - Script que valida: cada artigo da LGPD está indexado, counts batem
   - Dashboard simples: "corpus stats" (total chunks, avg chunk size, etc.)
7. **Versionamento:**
   - DVC ou simplesmente `data/processed/v1/` com hash
   - Permite reproduzir qualquer estado do corpus

#### Decisões a documentar (ADRs)
- Estratégia de chunking escolhida e por quê (com benchmark)
- Embedding model (por que bge-m3 e não Titan ou OpenAI)
- Hybrid vs dense-only (com evidência)

#### Definition of Done
- [ ] 100% dos artigos da LGPD indexados com metadata correta
- [ ] Regulamentações da ANPD indexadas (principais)
- [ ] Pipeline rodável via `make ingest` ou CLI
- [ ] Testes unitários para loaders e chunkers
- [ ] Script de validação passa

---

### FASE 2 — RAG Baseline (5–7 dias)

#### Objetivos
Sistema end-to-end mais simples possível funcionando. **Sem agentes ainda.**

#### Tarefas
1. **Retrieval básico:**
   - Função `retrieve(query, k=10)` retorna chunks relevantes
   - Hybrid search: dense + BM25 com reciprocal rank fusion
2. **Reranking:**
   - Cross-encoder `bge-reranker-v2-m3` re-ordena top-k para top-n (ex: 20→5)
3. **Prompt engineering inicial:**
   - System prompt estrito: "responda APENAS com base no contexto, cite sempre, recuse se não souber"
   - Template com slots: `{context}`, `{question}`, `{citation_format}`
4. **Generation:**
   - Chamada ao LLM (Ollama em dev, Bedrock em prod)
   - Streaming de tokens
5. **Citation formatting:**
   - Cada afirmação deve terminar com `[Art. X, LGPD]` ou similar
   - Pós-processamento verifica formato
6. **API endpoint:**
   - `POST /api/v1/query` com `{question, conversation_id?}`
   - SSE streaming response
7. **Testes:**
   - Unit: retrieval, reranking, prompt building
   - Integration: query end-to-end com mock LLM
8. **Manual smoke test:**
   - Lista de 10 queries reais, verificar qualidade visualmente

#### Definition of Done
- [ ] Query via API retorna resposta streaming com citações
- [ ] Latência baseline medida (P50, P95)
- [ ] Hallucination rate anedótico baixo (verificação manual em 10 queries)
- [ ] Logs estruturados de cada query

---

### FASE 3 — Evaluation Framework (4–6 dias)

#### Objetivos
**Esta é a fase que mais diferencia seu projeto.** Construir sistema rigoroso de avaliação.

#### Tarefas
1. **Criar eval dataset (`evals/dataset/v1/`):**
   - **~100 queries** categorizadas:
     - 30 factual simples (resposta direta na lei)
     - 25 procedural (prazos, requisitos)
     - 20 comparativas (entre artigos)
     - 15 edge cases (fora de escopo, ambíguas)
     - 10 adversariais (tentativa de extrair info errada)
   - Cada query tem:
     ```yaml
     id: q_001
     question: "Qual o prazo para a ANPD concluir investigação administrativa?"
     category: procedural
     difficulty: easy
     expected_articles: ["Art. 52, LGPD"]
     expected_answer_points:
       - "prazo de X dias"
       - "possibilidade de prorrogação"
     must_contain_citation: true
     should_refuse: false
     ```
2. **Métricas implementadas:**
   - **Retrieval metrics:** Recall@k, MRR, NDCG (usando `expected_articles`)
   - **Generation metrics (RAGAS):** Faithfulness, Answer Relevancy, Context Precision/Recall
   - **Custom metrics:**
     - Citation Accuracy: citação aponta para doc real E doc contém a afirmação
     - Refusal Accuracy: recusou quando devia, não recusou quando não devia
     - Hallucination Rate: afirmações não suportadas por contexto
3. **LLM-as-judge com safeguards:**
   - Usar Claude Sonnet como juiz
   - Rubrica explícita
   - Calibrar contra 20 exemplos anotados manualmente
4. **Harness de execução:**
   - `python -m evals run --version v1` executa todas
   - Salva resultados em Postgres com timestamp, git commit, model version
   - Gera report markdown em `evals/reports/`
5. **Integração com CI:**
   - PR trigger: roda subset rápido (20 queries) em mock
   - Main merge: roda full eval em staging
   - Regressão: se score cai > 5%, bloquea merge
6. **Eval dashboard:**
   - Página simples mostrando evolução das métricas ao longo do tempo
   - Permite comparar runs

#### Decisões a documentar
- ADR: "Why we built our own eval dataset instead of relying on public benchmarks"
- ADR: "LLM-as-judge calibration methodology"

#### Definition of Done
- [ ] 100 queries anotadas no dataset
- [ ] Todas as métricas implementadas e testadas
- [ ] Eval run completo em < 10 min
- [ ] Report gerado automaticamente em markdown
- [ ] Baseline scores documentados em `EVALUATION.md`

---

### FASE 4 — Agentic Orchestration (7–10 dias)

#### Objetivos
Upgrade do baseline para arquitetura multi-agent com LangGraph.

#### Tarefas
1. **Desenhar state graph:**
   ```
   [Router] → [Simple Path]
           → [Complex Path] → [Planner] → [Retriever Agent]
                                       → [Comparator Agent]
                                       → [Calculator Agent]
                                       → [Synthesizer Agent]
                                       → [Critic Agent]
   ```
2. **Implementar cada agent:**
   - **Router Agent:** classifica query (simple/complex/out-of-scope/adversarial)
   - **Planner Agent:** decompõe query complexa em sub-tasks
   - **Retriever Agent:** tool-using, escolhe entre busca em LGPD / ANPD decisões / GDPR
   - **Comparator Agent:** quando query exige comparação, alinha artigos correspondentes
   - **Calculator Agent:** para prazos, contagens regulatórias (ex: "quantos dias tenho para responder?")
   - **Synthesizer Agent:** consolida resultados em resposta coerente com citations
   - **Critic Agent:** revisa resposta antes de enviar (catch hallucination, missing citation)
3. **Tools disponíveis (via function calling):**
   - `search_lgpd(query, filters)`
   - `search_anpd_decisions(query, date_range)`
   - `search_gdpr(query)` (preparação para Fase 10)
   - `calculate_deadline(article, event_date)`
   - `compare_provisions(lgpd_article, gdpr_article)`
4. **State management:**
   - Shared state com histórico, contexto acumulado, rascunhos
   - Checkpoints para debug
5. **Fallback strategies:**
   - Timeout por agent
   - Graceful degradation: se agent X falha, tenta path simplificado
6. **Re-run evals:**
   - Comparar métricas v1 (baseline RAG) vs v2 (agentic)
   - Documentar melhoria (ou regressão!) em cada métrica
   - Honesto: se agentic piorou em algum aspecto, documentar

#### Decisões a documentar
- ADR: "Multi-agent topology: hierarchical vs flat"
- ADR: "Router: LLM-based vs rules-based classification"
- ADR: "When to use agents vs simple RAG (trade-off analysis)"

#### Definition of Done
- [ ] Todos os agents implementados e testados isoladamente
- [ ] Orchestrator end-to-end funciona
- [ ] Eval re-rodada, resultados documentados
- [ ] Traces no Langfuse mostram decomposição clara
- [ ] Fallback testado (simular falha de agent)

---

### FASE 5 — Optimization (custo/latência) (4–6 dias)

#### Objetivos
Transformar "funciona" em "funciona bem e barato".

#### Tarefas
1. **Semantic caching:**
   - Cache por embedding similarity (threshold ~0.97)
   - Redis + vector para chaves
   - TTL configurável
   - Métricas: hit rate, cache size
2. **Model routing:**
   - Queries simples (classificadas pelo Router) → Claude Haiku
   - Queries complexas → Claude Sonnet
   - Medir economia: % queries em Haiku, redução de custo
3. **Prompt optimization:**
   - Reduzir system prompt verbosity (mas sem perder qualidade — validar com eval)
   - Prompt caching da Anthropic (quando aplicável)
4. **Batch embedding:**
   - Para ingestion, batches de 64–128
5. **Streaming optimizado:**
   - First-token latency < 1s ideal
   - Usar SSE com chunks pequenos
6. **Parallel agent execution:**
   - Quando possível, rodar agents em paralelo (Retriever + Comparator juntos)
7. **Benchmarks documentados:**
   - Tabela em `PERFORMANCE.md`:
     - Baseline vs otimizado
     - P50, P95, P99 latency
     - Custo médio, p95 custo
     - Token usage breakdown
8. **Load testing básico:**
   - Locust ou k6 com 10 usuários concorrentes
   - Identificar bottlenecks

#### Definition of Done
- [ ] RNF-01 (latência) e RNF-02 (custo) atingidos
- [ ] Cache hit rate > 30% em queries repetidas
- [ ] `PERFORMANCE.md` com benchmarks antes/depois
- [ ] Load test passa sem degradação significativa

---

### FASE 6 — Guardrails e Security (3–5 dias)

#### Objetivos
Implementar camada de segurança que **demonstra responsible AI** — crucial para o tema.

#### Tarefas
1. **Input guardrails:**
   - Prompt injection detection (regex + classifier leve, ex: Llama Guard ou rules)
   - PII detection no input (CPF, email, telefone) — opção de redact ou reject
   - Topic filtering: recusar queries fora de escopo (com resposta graciosa)
2. **Output guardrails:**
   - Citation verifier: toda afirmação factual tem citação; senão, flag
   - Hallucination detector: cross-check afirmações com contexto recuperado
   - PII leak detection: garantir que PII do contexto não vaza
3. **Rate limiting:**
   - Por IP (anônimo)
   - Por API key (autenticado)
   - Sliding window no Redis
4. **Audit log:**
   - Toda query salva com: timestamp, user hash, query, response, citations, cost, latency
   - Retention policy configurável (dogfooding LGPD — art. 16)
5. **Right-to-be-forgotten (dogfooding!):**
   - Endpoint `DELETE /api/v1/users/me/history`
   - Remove de Postgres + Redis + Langfuse
   - Documentar em `PRIVACY.md`
6. **Data minimization nos logs:**
   - Hash de identificadores
   - PII redaction antes de persistir
7. **Secrets management:**
   - AWS Secrets Manager em prod
   - `.env` + `.env.example` em dev
   - Nunca commitar keys

#### Decisões a documentar
- ADR: "Guardrails architecture: middleware vs agent"
- `SECURITY.md` e `PRIVACY.md` escritos

#### Definition of Done
- [ ] Testes de red team: 10 tentativas de prompt injection bloqueadas
- [ ] PII detection funciona em 95%+ de casos de teste
- [ ] Rate limit testado
- [ ] Right-to-be-forgotten funcional end-to-end
- [ ] `SECURITY.md` e `PRIVACY.md` publicados

---

### FASE 7 — Observability (3–4 dias)

#### Objetivos
Tornar o sistema debuggável e auditável em produção.

#### Tarefas
1. **Langfuse integration:**
   - Todo LLM call tracked
   - Traces agregam chain completa de uma query (router → planner → agents → synth)
   - Custos por query, por user, por dia
   - Token breakdown
2. **Custom eval tracking:**
   - Resultados de eval runs no Langfuse
   - Comparação entre versões de prompt
3. **Structured logging:**
   - `structlog` com JSON output
   - Correlation IDs (trace ID de cada request)
4. **Metrics (Prometheus):**
   - Request rate, error rate, latency histogram
   - Queue depth, cache hit rate
5. **Dashboards:**
   - **Business dashboard:** queries/dia, users únicos, top queries, refusal rate
   - **Tech dashboard:** P50/P95/P99, error rate, cost/day, token usage
   - **Quality dashboard:** eval scores ao longo do tempo
6. **Alerts (básicos):**
   - Error rate > 5%
   - Latency P95 > 10s
   - Cost/day > $X
7. **Data drift monitoring (leve):**
   - Distribuição de tipos de queries ao longo do tempo
   - Se cache hit rate cair drasticamente → alertar

#### Definition of Done
- [ ] Cada query tem trace completo visualizável no Langfuse
- [ ] Dashboards acessíveis com dados reais
- [ ] Alert disparado em teste de falha
- [ ] `OBSERVABILITY.md` documenta o setup

---

### FASE 8 — Frontend Mínimo (3–5 dias)

#### Objetivos
Interface que demonstra o sistema sem distrair do foco técnico.

#### Tarefas
1. **Stack:** Next.js 14 App Router + Tailwind + shadcn/ui
2. **Telas:**
   - **Home/Chat:** input + mensagens streaming + citations clicáveis (abrem fonte)
   - **History:** lista de conversas anteriores, opção de deletar (dogfooding)
   - **Dashboard público (readonly):** métricas agregadas anônimas (queries/dia, taxa de refusal, etc.) — demonstra observability
   - **About:** explica o projeto, stack, limitações
3. **UX critical:**
   - Streaming suave
   - Loading states claros
   - Citations com hover preview
   - Disclaimer visível: "Themis não substitui aconselhamento jurídico profissional"
4. **Design:** simples, profissional, dark mode opcional
5. **Responsive:** funciona em mobile

#### Definition of Done
- [ ] Chat funcional com streaming
- [ ] Citations clicáveis abrem fonte correta
- [ ] Dashboard público exibe métricas
- [ ] Deploy no Vercel (ou ECS junto com backend)

---

### FASE 9 — Deploy AWS (4–6 dias)

#### Objetivos
Sistema publicamente acessível em URL própria — entregável crítico do portfolio.

#### Tarefas
1. **Infrastructure as Code (Terraform):**
   - VPC, subnets, security groups
   - ECS Fargate cluster
   - RDS Postgres (Free Tier)
   - ElastiCache Redis (ou Redis em container)
   - S3 buckets
   - ALB com HTTPS (ACM)
   - Route53 (se tiver domínio próprio)
2. **Docker images:**
   - Multi-stage builds
   - Imagens em ECR
3. **CI/CD pipeline (GitHub Actions):**
   - Test → Build → Push ECR → Deploy ECS
   - Staging env + Production env
   - Rollback automatizado em falha
4. **Bedrock setup:**
   - IAM role com permissões mínimas
   - Model access habilitado (Haiku + Sonnet)
   - VPC endpoint para Bedrock (segurança)
5. **Secrets:**
   - AWS Secrets Manager para credentials
6. **Domain e HTTPS:**
   - Ideal: domínio custom (`themis.seu-nome.com`)
   - ACM certificate
7. **Custom startup script:**
   - Warm up caches
   - Health checks corretos
8. **Cost guardrails:**
   - AWS Budget alert em $20/mês
   - Stop automático se passar threshold

#### Decisões a documentar
- ADR: "Why ECS Fargate over Lambda / EKS"
- ADR: "RDS vs Aurora Serverless"

#### Definition of Done
- [ ] URL pública funcionando com HTTPS
- [ ] Pipeline CI/CD verde, deploy em < 10 min
- [ ] Monitoring em produção ativo
- [ ] `DEPLOYMENT.md` explica como reproduzir

---

### FASE 10 — GDPR Extension (3–5 dias)

#### Objetivos
Provar extensibilidade arquitetural e elevar apelo internacional.

#### Tarefas
1. **Ingestão do GDPR:**
   - Regulation (EU) 2016/679 em inglês
   - Schema compatível com LGPD
   - Nova tag de jurisdiction: `eu`
2. **Mapping LGPD ↔ GDPR:**
   - Criar tabela de correspondência artigo-a-artigo (manual, ~30 mappings core)
   - Armazenar em `data/mappings/lgpd_gdpr.yaml`
3. **Comparator Agent upgrade:**
   - Usa o mapping para buscas cross-jurisdictional
   - Identifica diferenças semânticas quando há
4. **Novas queries no eval dataset:**
   - 20 queries comparativas LGPD-GDPR
   - Re-run evals
5. **UI update:**
   - Toggle de jurisdição (BR / EU / Both)
   - Citations distinguem fonte
6. **Documentação:**
   - Seção em README: "Extending to new jurisdictions"
   - Mostra o processo: adicionar corpus → mapping → re-eval

#### Definition of Done
- [ ] Queries comparativas retornam comparações precisas
- [ ] Eval dataset expandido, scores documentados
- [ ] UI mostra jurisdição na citação
- [ ] README internacional atualizado

---

### FASE 11 — Documentation Polish (2–3 dias)

#### Objetivos
**Esta fase é crítica para portfolio.** Documentação é o que recrutador lê antes de olhar código.

#### Tarefas
1. **README.md polish:**
   - Hero section com screenshot/GIF do sistema
   - Problem statement claro
   - Demo URL destacado
   - Quick start (3 comandos)
   - Architecture diagram inline
   - Link para cada documento secundário
   - Section "Why this project" explaining technical choices
   - Tech stack badges
   - Contact info
2. **Documentos secundários polidos:**
   - `ARCHITECTURE.md` — diagrama + explicação por camada
   - `EVALUATION.md` — dataset, métricas, resultados, análise
   - `PERFORMANCE.md` — benchmarks de custo/latência
   - `SECURITY.md` — threat model e mitigações
   - `PRIVACY.md` — data handling, dogfooding LGPD
   - `OBSERVABILITY.md` — o que medimos e por quê
   - `DEPLOYMENT.md` — como reproduzir
   - `DECISIONS.md` — índice dos ADRs
3. **Diagramas:**
   - Architecture overview (C4 context + container)
   - Agent flow (state machine)
   - Data flow (ingestion → retrieval)
   - Usar Excalidraw ou Mermaid
4. **Video demo (5 min):**
   - Loom ou similar
   - Mostra: query simples → query complexa → comparação LGPD/GDPR → dashboard
5. **Blog post (opcional mas altamente recomendado):**
   - "Building an Agentic RAG System for Legal Compliance: Lessons Learned"
   - Publicar em Medium/Dev.to/LinkedIn
   - Referenciar no README

#### Definition of Done
- [ ] README faz recrutador querer clicar em "Demo"
- [ ] Todos os documentos secundários existem e são polidos
- [ ] Diagramas existem e são claros
- [ ] Video demo publicado
- [ ] Blog post publicado (opcional)

---

## 7. Estratégia de Avaliação

### 7.1 Princípios
- **Eval-driven development:** nenhuma mudança de prompt/arquitetura sem re-rodar eval
- **Dataset próprio > benchmark público:** específico para o domínio
- **Múltiplas camadas:** retrieval quality, generation quality, end-to-end quality
- **LLM-as-judge com calibração:** não confia cegamente em outro LLM

### 7.2 Dataset (`evals/dataset/v1/`)

Total: ~100 queries, distribuídas em categorias balanceadas. Cada query é anotada com resposta esperada, artigos esperados, e critérios de aceitação.

Versionamento rigoroso: v1 (baseline), v2 (agentic), v3 (com GDPR), etc.

### 7.3 Métricas

**Retrieval:**
- Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)
- NDCG@10

**Generation:**
- Faithfulness (RAGAS)
- Answer Relevancy (RAGAS)
- Citation Accuracy (custom)
- Refusal Accuracy (custom)

**End-to-end:**
- Task Success Rate (human-annotated subset)
- Hallucination Rate

### 7.4 Cadência
- Cada PR com mudança de prompt/retrieval/agent: eval rápida (subset 20)
- Merge para main: eval completa
- Semanal: eval completa + relatório comparativo

---

## 8. Observabilidade e Monitoramento

Coberto em detalhe na Fase 7. Princípios:
- Tudo tem trace
- Custos visíveis por query
- Eval scores ao longo do tempo são história contínua
- Alertas humanos, não ruidosos

---

## 9. Segurança e Responsible AI

### 9.1 Threat Model (resumido)
- **Prompt injection:** usuário tenta extrair informação fora do escopo ou manipular respostas
- **Data exfiltration:** tentativa de extrair prompts internos ou PII de outros usuários
- **Jailbreak:** contornar refusal policies
- **DoS:** flood de queries caras

### 9.2 Mitigações
Detalhadas na Fase 6. Resumo:
- Input/output guardrails em camadas
- Rate limiting
- Audit log completo
- PII handling estrito
- Disclaimer legal visível

### 9.3 Dogfooding LGPD
O sistema **pratica o que ensina:**
- Art. 18 (direitos do titular): implementado via endpoint de deleção
- Art. 46 (segurança): encryption at rest e in transit
- Art. 37 (registro de operações): audit log
- Art. 50 (boas práticas): documentado em `PRIVACY.md`

---

## 10. Custo Estimado

### 10.1 Desenvolvimento (5–7 semanas)
- Bedrock API (experimentação + eval runs): **$5–15**
- Embeddings (se usar cloud): $2–5
- AWS Free Tier cobre: EC2, RDS, S3, Lambda básico
- Domain (opcional): $10–15

**Total dev:** ~$20–35

### 10.2 Operação (mensal, baixo tráfego pós-deploy)
- ECS Fargate (1 task pequena): ~$10/mês se não desligar
- RDS Free Tier: $0 (primeiros 12 meses)
- Bedrock: depende de uso — com $5 de budget cobre bem demo
- S3/CloudWatch: <$1
- **Estratégia:** desligar serviços fora de horário de demo, usar budget alerts agressivos

**Total operação:** $10–20/mês se mantiver no ar. Você pode desligar e ligar sob demanda para entrevistas.

---

## 11. Entregáveis e Artefatos de Portfolio

Ao final, você terá:

### 11.1 Artefatos Técnicos
- [ ] Repositório GitHub público bem estruturado
- [ ] URL pública funcional (demo acessível)
- [ ] Video demo de 5 minutos
- [ ] Dataset de eval versionado
- [ ] CI/CD pipeline funcional

### 11.2 Artefatos de Documentação
- [ ] README.md matador
- [ ] ARCHITECTURE.md com diagramas
- [ ] EVALUATION.md com resultados mensuráveis
- [ ] PERFORMANCE.md com benchmarks
- [ ] SECURITY.md e PRIVACY.md
- [ ] OBSERVABILITY.md
- [ ] DEPLOYMENT.md
- [ ] 8+ ADRs em `docs/decisions/`

### 11.3 Artefatos de Comunicação
- [ ] Blog post técnico
- [ ] LinkedIn post com learnings
- [ ] Seção no seu site pessoal / portfolio

---

## 12. Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Escopo inflacionar | Alta | Alto | Roadmap fixo, cortar features antes de atrasar |
| Qualidade das respostas jurídicas ruim | Média | Alto | Eval rigoroso desde Fase 3, amigo advogado valida 10 respostas |
| Custo AWS estourar | Baixa | Médio | Budget alerts, desligar serviços, Free Tier |
| Bedrock indisponível em região | Baixa | Médio | Fallback para Anthropic API direto |
| Burnout / perder motivação | Média | Alto | Entregar algo visível a cada fase (dopamina de progresso) |
| Dependency de libs em beta (LangGraph) quebrar | Média | Médio | Pinning de versões, testes, abstrair interfaces |

---

## 13. Critérios de Conclusão

O projeto está **pronto para portfolio** quando:

- [ ] Todas as 11 fases completas com DoD atendido
- [ ] Eval mostra métricas acima dos thresholds definidos em RNF-03
- [ ] Sistema rodando em URL pública com HTTPS
- [ ] Documentação completa e polida
- [ ] Video demo publicado
- [ ] Blog post publicado (opcional mas recomendado)
- [ ] Você consegue explicar qualquer decisão arquitetural em < 2 minutos
- [ ] Você consegue rodar o projeto do zero em máquina nova em < 15 min

---

## Apêndice A — Perguntas Frequentes em Entrevista (Prep)

Prepare respostas curtas e estruturadas para:
1. Por que LangGraph e não CrewAI/AutoGen?
2. Por que Qdrant e não pgvector/Pinecone/Weaviate?
3. Como você avalia qualidade do sistema?
4. Como você garante que o LLM não alucina?
5. Como escalaria para 1000 QPS?
6. Qual foi o maior trade-off que você fez?
7. O que você faria diferente se começasse hoje?
8. Como você extenderia para GDPR? (spoiler: você já fez)
9. Como você detecta data drift?
10. Qual o custo por query e como você reduziu?

---

## Apêndice B — Sinais de "Está indo bem"

Se ao longo do projeto você consegue:
- Ter prazer em cortar features para entregar com qualidade
- Documentar decisões conforme toma, não depois
- Rodar o eval antes de qualquer mudança grande
- Explicar trade-offs sem precisar consultar nada
- Mostrar o projeto em 5 minutos para alguém leigo

...você está construindo um projeto tier 1 de verdade.

---

**Fim do documento.**
**Próximos passos recomendados:** ler o SDD inteiro uma vez, começar Fase 0, criar issues no GitHub para cada tarefa das fases iniciais.
