"""
Configurações do sistema de extração de demandas.

Este módulo centraliza as configurações que podem ser modificadas
sem quebrar o sistema.
"""

# -----------------------------
# Configurações de PDF
# -----------------------------
DEFAULT_DPI = 200  # DPI padrão para renderização do PDF em imagens
MIN_CHARS_FOR_TEXT_ONLY = 40  # Mínimo de caracteres por página para usar modo text-only

# -----------------------------
# Configurações de IA
# -----------------------------
DEFAULT_MODEL = "gpt-4.1-mini"  # Modelo OpenAI padrão
DEFAULT_TEMPERATURE = 0  # Temperatura para chamadas da IA (0 = determinístico)
# Timeout em segundos para chamadas à API OpenAI (evita job travado em "Lendo o conteúdo")
DEFAULT_OPENAI_TIMEOUT = 300  # 5 minutos

# -----------------------------
# Configurações de output
# -----------------------------
DEFAULT_OUTPUT_PATH = "test/demanda.json"  # Caminho padrão para saída JSON
