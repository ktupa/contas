# Correções na Dashboard e Despesas

## Data: 16/12/2025

### Problemas Identificados

1. **Erro 500 ao criar despesas**
   - **Causa**: Conflito de timezone entre dados enviados do frontend (com timezone) e database (naive datetime)
   - **Erro**: `TypeError: can't subtract offset-naive and offset-aware datetimes`

2. **Descontos incorretos na dashboard**
   - **Problema**: Dashboard não separava corretamente:
     - Descontos por rubrica (já calculados no total_previsto)
     - Descontos por pagamento (payment.kind="desconto")
   - **Resultado**: Total pago incorreto, saldo errado

### Correções Aplicadas

#### 1. ExpenseBase Schema (backend/app/schemas.py)

**Antes:**
```python
class ExpenseBase(BaseModel):
    date: datetime
    due_date: Optional[datetime] = None
    # ... outros campos
```

**Depois:**
```python
class ExpenseBase(BaseModel):
    date: datetime
    due_date: Optional[datetime] = None
    # ... outros campos
    
    @field_validator('date', 'due_date', mode='before')
    @classmethod
    def strip_timezone(cls, v):
        """Remove timezone info to store as naive datetime (UTC assumed)"""
        if v is None:
            return v
        if isinstance(v, datetime) and v.tzinfo is not None:
            return v.replace(tzinfo=None)
        if isinstance(v, str):
            from dateutil import parser
            dt = parser.parse(v)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        return v
```

**Resultado**: Agora despesas podem ser criadas sem erro de timezone.

#### 2. Cálculo de Total Pago (backend/app/routers/competencies.py)

**Antes:**
```python
# Total pago
result = await db.execute(
    select(func.sum(Payment.amount)).where(
        and_(
            Payment.competency_id == competency_id,
            Payment.status == "pago"
        )
    )
)
total_pago = result.scalar() or 0
```

**Depois:**
```python
# Total pago (excluindo descontos automáticos de rubrica)
# Descontos por rubrica já estão no total_previsto (total_geral)
# Aqui contamos apenas pagamentos efetivos (não kind='desconto')
result = await db.execute(
    select(func.sum(Payment.amount)).where(
        and_(
            Payment.competency_id == competency_id,
            Payment.status == "pago",
            Payment.kind != "desconto"  # Exclui descontos automáticos
        )
    )
)
total_pago = result.scalar() or 0
```

**Resultado**: Agora o total pago reflete apenas pagamentos reais, não descontos por rubrica.

### Como Funciona Agora

#### Fluxo de Descontos

1. **Desconto por Rubrica**
   - Adicionado como `CompetencyItem` com rubrica tipo "desconto"
   - Entra no cálculo do `total_previsto` (total_geral = proventos - descontos)
   - Pode gerar pagamento automático negativo (kind="desconto")
   - **Na dashboard**: Aparece no valor previsto, não como "desconto por pagamento"

2. **Desconto por Pagamento**
   - Pagamento manual criado com kind="desconto"
   - **Não** conta no `total_pago` (excluído pelo filtro)
   - Usado para registrar descontos aplicados durante pagamento

#### Exemplo Prático

**Colaborador: João**
- Salário base (provento): R$ 5.000,00
- Vale transporte (desconto rubrica): -R$ 200,00
- **Total Previsto**: R$ 4.800,00 ✅

**Pagamentos:**
- Adiantamento: R$ 1.500,00 (kind="adiantamento")
- Desconto negociado: -R$ 100,00 (kind="desconto") ❌ Não conta no total_pago
- Salário final: R$ 3.200,00 (kind="salario")
- **Total Pago**: R$ 4.700,00 ✅ (1.500 + 3.200, sem desconto)

**Saldo**: R$ 100,00 (4.800 - 4.700)

### Testes Recomendados

1. ✅ Criar despesa com data atual (timezone)
2. ✅ Criar competência com descontos por rubrica
3. ✅ Adicionar pagamentos mistos (adiantamento + salário)
4. ✅ Verificar dashboard mostra valores corretos
5. ✅ Confirmar saldo a pagar está correto

### Arquivos Modificados

- `backend/app/schemas.py` - ExpenseBase com validator de timezone
- `backend/app/routers/competencies.py` - Filtro de kind!="desconto" no total_pago

### Status

- ✅ Erro 500 corrigido
- ✅ Dashboard calculando corretamente
- ✅ Separação de descontos por tipo funcional
- ✅ API reiniciada e testada

---

**Build**: 51fd7be97c48
**Ambiente**: Produção
**Última atualização**: 16/12/2025 14:05
