"""
Prompts usados na extração de demandas via IA.

Este módulo centraliza os prompts da IA, permitindo modificações
sem quebrar o sistema.
"""

# Versão do prompt (para tracking de mudanças)
PROMPT_VERSION = "v2.0"

# Prompt do sistema
SYSTEM_PROMPT = """Você é um extrator de dados de agenda cirúrgica.
Extraia as demandas (linhas de tabela) do PDF.
Você DEVE responder APENAS com JSON válido (sem markdown, sem explicações).
"""

# Prompt do usuário (instruções detalhadas)
USER_PROMPT = """Extraia as demandas cirúrgicas do documento.
Regras:
- Responda APENAS JSON.
- O JSON DEVE conter as chaves: meta, demands.
- demands é uma lista de objetos com:
  - room (string ou null)
  - start_time (ISO datetime com timezone, ex: "2026-01-12T09:30:00-03:00")
  - end_time (ISO datetime com timezone, ex: "2026-01-12T12:00:00-03:00")
  - procedure (string)
  - anesthesia_type (string ou null)
  - skills (lista; se não houver, [])
  - priority ("Urgente" | "Emergência" | null)  # extrair de notes quando houver "Prioridade: ..."
  - complexity (string ou null)  # se existir como complexidade do caso (Baixa/Média/Alta)
  - members (lista; se não houver, [])
  - notes (string ou null)
- Não invente dados que não estejam no documento.
"""
