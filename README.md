# Turna

Sistema inteligente para geração automática de escalas cirúrgicas otimizadas, facilitando a alocação de demandas cirúrgicas aos profissionais médicos disponíveis.

## Funcionalidades Principais

### 📋 **Extração Automática de Demandas**
- **Leitura inteligente de documentos**: Extrai automaticamente as demandas cirúrgicas de PDFs ou imagens (JPEG/PNG) usando inteligência artificial
- **Processamento híbrido**: Utiliza análise de texto quando disponível ou visão computacional para documentos escaneados
- **Identificação automática**: Reconhece horários, identificadores e características das demandas (incluindo demanda pediátrica)

### 👥 **Gestão de Profissionais**
- **Cadastro de equipe médica**: Gerencia a lista de profissionais disponíveis para alocação
- **Especialidades**: Suporta profissionais com especialidade em pediatria e profissionais gerais
- **Controle de disponibilidade**: Considera períodos de férias e folgas de cada profissional
- **Sequenciamento**: Mantém ordem de prioridade na alocação dos profissionais

### 🤖 **Alocação Automática Inteligente**
- **Duas estratégias de otimização**:
  - **Greedy (Rápida)**: Alocação eficiente e rápida, ideal para escalas diárias
  - **CP-SAT (Otimizada)**: Algoritmo avançado de otimização para escalas mais complexas
- **Respeito às restrições**:
  - Apenas profissionais pediatras podem atender demandas pediátricas
  - Não sobrepõe horários (cada profissional atende uma demanda por vez)
  - Respeita períodos de férias e folgas
- **Priorização inteligente**: Sistema penaliza demandas não alocadas, com atenção especial para demandas pediátricas

### 📊 **Visualização e Relatórios**
- **Visualização no console**: Exibe escala de forma visual e clara, mostrando horários e alocações
- **Geração de PDF**: Cria escalas formatadas em PDF para impressão ou compartilhamento
- **Relatórios detalhados**: Mostra visão geral das demandas, profissionais e custos totais
- **Identificação de conflitos**: Destaca visualmente demandas pediátricas e profissionais especializados

### 🔍 **Diagnóstico e Validação**
- **Verificação de viabilidade**: Analisa se todas as demandas podem ser atendidas
- **Identificação de gargalos**: Detecta períodos com mais demandas que profissionais disponíveis
- **Elegibilidade por demanda**: Lista quais profissionais podem atender cada demanda considerando especialidade e disponibilidade
- **Alertas de problemas**: Sinaliza demandas sem profissionais elegíveis ou períodos com sobrecarga

### ⚙️ **Configuração e Flexibilidade**
- **Arquivos JSON**: Dados de demandas e profissionais em formato JSON, facilitando edição
- **Parâmetros ajustáveis**: Permite configurar penalidades e prioridades
- **Múltiplos dias**: Suporta escalas para vários dias simultaneamente
- **Demandas descobertas**: Opção de permitir demandas sem alocação (marcadas como "descobertas")

## Benefícios para os Profissionais Médicos

- **Economia de tempo**: Elimina o trabalho manual de criar escalas
- **Justiça na distribuição**: Algoritmos garantem distribuição equilibrada entre profissionais
- **Respeito às restrições**: Sistema sempre respeita especialidades e disponibilidades
- **Transparência**: Visualização clara de quem atende cada demanda e quando
- **Flexibilidade**: Facilita ajustes e reagendamentos quando necessário
