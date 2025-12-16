"""
Script para recalcular os totais de todas as competências
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import Competency, CompetencyItem, Rubric
from app.config import settings

async def recalculate_all():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Buscar todas as competências
        result = await db.execute(select(Competency))
        competencies = result.scalars().all()
        
        print(f"Encontradas {len(competencies)} competências")
        
        for comp in competencies:
            print(f"\nProcessando competência ID {comp.id} - {comp.month}/{comp.year}")
            
            # Buscar todos os itens com rubricas
            result = await db.execute(
                select(CompetencyItem, Rubric).join(Rubric).where(
                    CompetencyItem.competency_id == comp.id
                )
            )
            items_with_rubrics = result.all()
            
            # Calcular totais
            total_proventos = 0.0
            total_descontos = 0.0
            total_clt = 0.0
            total_beneficios = 0.0
            
            for item, rubric in items_with_rubrics:
                valor = float(item.value)
                print(f"  - {rubric.name}: {rubric.type} = R$ {valor:.2f}")
                
                # Soma proventos ou descontos
                if rubric.type == "provento":
                    total_proventos += valor
                else:  # desconto
                    total_descontos += valor
                
                # Itens que entram na base CLT
                if rubric.entra_clt:
                    if rubric.type == "provento":
                        total_clt += valor
                    else:
                        total_clt -= valor
                
                # Benefícios (apenas proventos)
                if rubric.category == "beneficio" and rubric.type == "provento":
                    total_beneficios += valor
            
            # Total geral = proventos - descontos
            total_geral = total_proventos - total_descontos
            
            totals = {
                "total_proventos": total_proventos,
                "total_descontos": total_descontos,
                "total_clt": total_clt,
                "total_beneficios": total_beneficios,
                "total_geral": total_geral
            }
            
            print(f"  Proventos: R$ {total_proventos:.2f}")
            print(f"  Descontos: R$ {total_descontos:.2f}")
            print(f"  LÍQUIDO: R$ {total_geral:.2f}")
            
            # Atualizar competência
            comp.totals_json = totals
        
        await db.commit()
        print(f"\n✅ Recálculo concluído!")

if __name__ == "__main__":
    asyncio.run(recalculate_all())
