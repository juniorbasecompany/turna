# Turna

Sistema inteligente para geração automática de escalas cirúrgicas otimizadas, facilitando a alocação de demandas cirúrgicas aos profissionais médicos disponíveis.

## Status atual vs. roadmap

### Implementado (MVP web admin ~90%)
- **Autenticação**: Login OAuth Google, JWT, multi-tenant
- **Gestão**: Clínicas, associados (membros), hospitais com prompt customizável
- **Arquivos**: Upload de PDF/imagens, visualização, thumbnails
- **Extração IA**: Extração de demandas cirúrgicas via OpenAI
- **Demandas**: CRUD completo de demandas cirúrgicas
- **Escalas**: Geração com solver Greedy, publicação e download de PDF
- **Jobs**: Sistema assíncrono (Arq/Redis) para processamento pesado
- **Email**: Envio de convites via Resend
- **Frontend**: Next.js com painéis de Dashboard, Hospitais, Clínicas, Associados, Arquivos, Demandas, Escalas, Jobs

### Em progresso
- Melhorias na página de escalas no frontend

### Futuro
- App mobile (React Native) para profissionais consultarem escalas
- Solver CP-SAT (otimização avançada com Google OR-Tools)
- Abstração completa do AI Provider para múltiplos provedores

As seções abaixo descrevem a visão do produto (funcionalidades principais e benefícios), alinhada ao que já existe e ao que está previsto.

## Funcionalidades Principais

### **Extração Automática de Demandas**
- **Leitura inteligente de documentos**: Extrai automaticamente as demandas cirúrgicas de documentos ou imagens usando inteligência artificial
- **Processamento híbrido**: Utiliza análise de texto quando disponível ou leitura visual para documentos escaneados
- **Identificação automática**: Reconhece horários, identificadores e características das demandas (incluindo demanda pediátrica)

### **Gestão de Profissionais**
- **Cadastro de equipe médica**: Gerencia a lista de profissionais disponíveis para alocação
- **Especialidades**: Suporta profissionais com especialidade em pediatria e profissionais gerais
- **Controle de disponibilidade**: Considera períodos de férias e folgas de cada profissional
- **Sequenciamento**: Mantém ordem de prioridade na alocação dos profissionais

### **Alocação Automática Inteligente**
- **Duas estratégias de otimização**:
  - **Rápida**: Alocação eficiente e rápida, ideal para escalas diárias
  - **Otimizada**: Algoritmo avançado de otimização para escalas mais complexas
- **Respeito às restrições**:
  - Apenas profissionais pediatras podem atender demandas pediátricas
  - Não sobrepõe horários (cada profissional atende uma demanda por vez)
  - Respeita períodos de férias e folgas
- **Priorização inteligente**: Sistema penaliza demandas não alocadas, com atenção especial para demandas pediátricas

### **Visualização e Relatórios**
- **Visualização**: Exibe escala de forma visual e clara, mostrando horários e alocações
- **Geração de documentos**: Cria escalas formatadas para impressão ou compartilhamento
- **Relatórios detalhados**: Mostra visão geral das demandas, profissionais e custos totais
- **Identificação de conflitos**: Destaca visualmente demandas pediátricas e profissionais especializados

### **Diagnóstico e Validação**
- **Verificação de viabilidade**: Analisa se todas as demandas podem ser atendidas
- **Identificação de gargalos**: Detecta períodos com mais demandas que profissionais disponíveis
- **Elegibilidade por demanda**: Lista quais profissionais podem atender cada demanda considerando especialidade e disponibilidade
- **Alertas de problemas**: Sinaliza demandas sem profissionais elegíveis ou períodos com sobrecarga

### **Configuração e Flexibilidade**
- **Arquivos de dados**: Dados de demandas e profissionais em formato simples, facilitando edição
- **Parâmetros ajustáveis**: Permite configurar penalidades e prioridades
- **Múltiplos dias**: Suporta escalas para vários dias simultaneamente
- **Demandas descobertas**: Opção de permitir demandas sem alocação (marcadas como "descobertas")

## Benefícios para os Profissionais Médicos

- **Economia de tempo**: Elimina o trabalho manual de criar escalas
- **Justiça na distribuição**: Garante distribuição equilibrada entre profissionais
- **Respeito às restrições**: Sistema sempre respeita especialidades e disponibilidades
- **Transparência**: Visualização clara de quem atende cada demanda e quando
- **Flexibilidade**: Facilita ajustes e reagendamentos quando necessário
