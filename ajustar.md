# Ajustes pendentes para aderir ao `DIRECTIVE.md`

Este arquivo lista itens que ainda precisam ser ajustados para ficar 100% coerente com as diretivas do projeto.
**Observação**: esta lista não aplica mudanças automaticamente; é apenas um guia.

## Datas e horários (timestamptz / ISO 8601 / validação)

- **Rejeitar timestamps sem fuso explícito na API**
  - **Motivo**: `DIRECTIVE.md` exige rejeitar timestamps sem offset/`Z`.
  - **Onde**: `app/api/route.py` (função `_isoformat_utc` atualmente “assume UTC” quando `tzinfo is None`).
  - **Ajuste esperado**: em vez de assumir UTC, retornar erro/invalidar quando receber/gerar timestamp sem tz explícito (ou garantir upstream que isso nunca aconteça e falhar explicitamente).

- **Padronizar comportamento de serialização de datetime**
  - **Motivo**: diretiva pede ISO 8601 completo com offset/`Z`.
  - **Onde**: `app/api/route.py` (respostas montadas manualmente e `response_model` com `from_attributes`).
  - **Ajuste esperado**: definir um padrão único (ex.: sempre emitir `Z`/offset e nunca produzir naive datetimes).

## API (contratos e padronização de erros)

- **Padronizar payload e mensagens de erro**
  - **Motivo**: `DIRECTIVE.md` pede padronização de respostas de erro (mensagens e status codes).
  - **Onde**: `app/api/route.py`, `app/api/auth.py`, `app/auth/dependencies.py`, `app/auth/oauth.py`, `app/auth/jwt.py`.
  - **Ajuste esperado**: um formato consistente para `detail` (idioma, códigos, estrutura) e mapeamento consistente de status (401/403/404/422/500).

## Nomenclatura (singular vs plural)

- **Prefixos S3 em plural**
  - **Motivo**: diretiva recomenda preferir singular e evitar plural.
  - **Onde**: `app/storage/service.py`
    - `_generate_s3_key(... file_type="imports", ...)` (plural)
    - docstring cita exemplos `"imports", "pdfs", "schedules"`
  - **Ajuste esperado**: decidir um conjunto de prefixes em singular (ex.: `import`, `pdf`, `schedule`) e alinhar docstrings/uso.
  - **Status**: implementado (prefix `import`, docstrings atualizadas).

- **Enums/constantes com plural**
  - **Motivo**: diretiva recomenda evitar plural em nomes.
  - **Onde**: `app/model/job.py` (`JobType.EXTRACT_DEMANDS`)
  - **Ajuste esperado**: renomear para singular (ex.: `EXTRACT_DEMAND`), se fizer sentido no domínio e sem quebrar compatibilidade com dados existentes.

- **Pastas/padrões que permanecem em plural por convenção**
  - **Onde**: `alembic/versions/` (padrão do Alembic)
  - **Nota**: manter como está é razoável; só documentar explicitamente a exceção nas diretivas.

## Scripts (prefixo `script_`)

- **Arquivos “script” sem prefixo `script_`**
  - **Motivo**: `DIRECTIVE.md` exige prefixo `script_` para scripts Python.
  - **Candidatos** (avaliar intenção): `login.py`, `diagnose.py`, `turna.py` (raiz do repo).
  - **Ajuste esperado**: manter como está. Isto será tratado no futuro.

## Dependências (atualidade / reprodutibilidade)

- **`requirements.txt` parcialmente sem versões (não pinado)**
  - **Motivo**: diretiva pede manter dependências atuais/seguras e `requirements.txt` atualizado; pinagem melhora reprodutibilidade.
  - **Onde**: `requirements.txt` (ex.: `openai`, `python-dotenv`, `pypdfium2`, `pillow`, `pdfplumber`, `requests`, `bcrypt` sem versão).
  - **Ajuste esperado**: pin parcial, os que já têm versão, manter.
  Vou sugerir algumas e você vê se está aderente ao projeto:
openai>=1.0,<2.0
python-dotenv>=1.0,<2.0
requests>=2.31,<3.0
bcrypt>=4.0,<5.0
pillow>=10.0,<11.0
pypdfium2>=4.30,<5.0
pdfplumber>=0.11,<1.0
Estas não precisa pinar: ortools, reportlab

## Documentação / consistência de nomes públicos

- **Consistência de naming entre endpoints e tags**
  - **Motivo**: diretiva de consistência/legibilidade; evita confusão em `/docs`.
  - **Onde**: `app/api/route.py`
    - `tags` no singular (`"Job"`, `"Tenant"`, `"File"`) vs outros lugares/histórico em plural.
  - **Ajuste esperado**: escolher singular para tags e manter consistente.

## Segurança (boas práticas)

- **Checar se não há logs com dados sensíveis**
  - **Motivo**: diretiva de evitar logar tokens/headers/PII.
  - **Onde**: pontos de auth/erros (`app/auth/*`, `app/api/*`) e workers.
  - **Ajuste esperado**: garantir que exceções não incluam tokens/headers; mensagens de erro devem ser seguras.

