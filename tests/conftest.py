from pathlib import Path
import sys
import shutil
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TMP_ROOT = ROOT / ".tmp-tests"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TMP_ROOT.mkdir(exist_ok=True)


SAMPLE_NOTE = """---
title: Decisao sobre persistencia do MVP
compartment: arquitetura
source_type: markdown
---
# Banco do MVP

Projeto: Brain4me
Problema: escolher persistencia inicial do MVP
Decisao: usar SQLite no MVP
Evidencia: reduz complexidade operacional
Alternativa: Neo4j
Risco: consultas relacionais avancadas podem exigir revisao futura
"""

NATURAL_NOTE = """---
title: Revisao contextual da persistencia
compartment: arquitetura
source_type: markdown
---
# Revisao de persistencia

Projeto: Brain4me
Problema: definir persistencia inicial com baixo atrito
Conclusao: manter SQLite como persistencia inicial
Motivo: reduzir complexidade operacional e setup
Alternativa: Neo4j
Conflito: Neo4j facilita exploracao relacional mais profunda
Excecao: revisar a escolha quando o grafo crescer demais
"""

FREEFORM_NOTE = """---
title: Escolha de persistencia em texto corrido
compartment: arquitetura
source_type: markdown
---
# Decisao de persistencia

Para validar rapido o Brain4me, SQLite parece melhor que Neo4j porque reduz complexidade operacional.
O risco e limitar consultas relacionais avancadas no futuro.
"""

FREEFORM_ENRICHED_NOTE = """---
title: Revisao livre de persistencia
compartment: arquitetura
source_type: markdown
---
# Revisao livre

O objetivo atual e validar rapido o Brain4me.
O problema imediato e escolher persistencia inicial com baixo atrito.
Para validar rapido o Brain4me, SQLite parece melhor que Neo4j porque reduz complexidade operacional.
O risco e limitar consultas relacionais avancadas no futuro.
"""

EXTERNAL_NOTE = """---
title: Comparativo externo
compartment: arquitetura
source_type: markdown
source_origin_type: external
---
# Fonte externa

Projeto: Brain4me
Problema: escolher persistencia inicial do MVP
Decisao: usar SQLite no MVP
Evidencia: benchmark externo recomenda cautela
Alternativa: Neo4j
Risco: dependencia de consultas complexas no futuro
"""

CONFLICTING_DECISION_NOTE = """---
title: Decisao concorrente sobre persistencia
compartment: arquitetura
source_type: markdown
---
# Alternativa de persistencia

Projeto: Brain4me
Problema: escolher persistencia inicial do MVP
Decisao: usar Neo4j no MVP
Evidencia: priorizar consultas relacionais nativas desde o inicio
Alternativa: SQLite
Risco: maior complexidade operacional no MVP
"""

INFERENCE_NOTE = """---
title: Analise inferencial da persistencia
compartment: arquitetura
source_type: markdown
---
# Analise inferencial

Projeto: Brain4me
Problema: escolher persistencia inicial do MVP
Decisao: manter SQLite no MVP
Evidencia: equipe precisa validar rapido o fluxo do produto
Inferencia: priorizar a opcao com menor atrito operacional enquanto o grafo ainda e pequeno
Alternativa: Neo4j
Risco: revisar a escolha quando a exploracao relacional se tornar critica
"""

LINKER_VARIANT_NOTE = """---
title: Repeticao com variacao textual
compartment: arquitetura
source_type: markdown
---
# Variacao textual

Projeto: Brain4me
Problema: validar persistencia com nomenclatura inconsistente
Decisao: manter SQLite no MVP
Evidencia: setup mais simples para iteracao local
Alternativa: neo4j
Risco: perder uniformidade terminologica nas notas
"""

SEMANTIC_LINKER_NOTE = """---
title: Decisao semanticamente equivalente
compartment: arquitetura
source_type: markdown
---
# Variacao semantica

Projeto: Brain4me
Problema: escolher persistencia inicial do MVP
Decisao: usar SQLite como banco inicial
Evidencia: menor atrito operacional
Alternativa: Neo4j
Risco: limitar consultas de grafo no inicio
"""


class WorkspaceTempDirTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TMP_ROOT / self.id().replace(".", "_")
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
