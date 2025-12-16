import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Tenant, User, Rubric
from app.auth import get_password_hash
import sys


async def create_seeds():
    """Criar dados iniciais"""
    async with AsyncSessionLocal() as db:
        try:
            # 1. Criar tenant padrão
            tenant = Tenant(
                name="Empresa Padrão"
            )
            db.add(tenant)
            await db.flush()
            
            print(f"✓ Tenant criado: {tenant.name} (ID: {tenant.id})")
            
            # 2. Criar usuário admin
            admin_user = User(
                tenant_id=tenant.id,
                name="Administrador",
                email="admin@financeiro.com",
                password_hash=get_password_hash("admin123"),
                role="admin",
                active=True
            )
            db.add(admin_user)
            
            print(f"✓ Usuário admin criado: {admin_user.email}")
            
            # 3. Criar usuário financeiro
            finance_user = User(
                tenant_id=tenant.id,
                name="Financeiro",
                email="financeiro@financeiro.com",
                password_hash=get_password_hash("financeiro123"),
                role="financeiro",
                active=True
            )
            db.add(finance_user)
            
            print(f"✓ Usuário financeiro criado: {finance_user.email}")
            
            # 4. Criar rubricas padrão
            rubrics_data = [
                # Folha
                {"name": "Salário Base", "category": "folha", "entra_clt": True, "entra_calculo_percentual": True, "recurring": True},
                {"name": "Periculosidade", "category": "folha", "entra_clt": True, "entra_calculo_percentual": True, "recurring": True},
                {"name": "Insalubridade", "category": "folha", "entra_clt": True, "entra_calculo_percentual": True, "recurring": True},
                {"name": "Horas Extras", "category": "folha", "entra_clt": True, "entra_calculo_percentual": True, "recurring": False},
                
                # Benefícios
                {"name": "Vale Refeição", "category": "beneficio", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                {"name": "Vale Transporte", "category": "beneficio", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                {"name": "Plano de Saúde", "category": "beneficio", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                {"name": "Auxílio Educação", "category": "beneficio", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                
                # Reembolsos
                {"name": "Combustível", "category": "reembolso", "entra_clt": False, "entra_calculo_percentual": False, "recurring": False},
                {"name": "Aluguel Carro", "category": "reembolso", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                {"name": "Celular", "category": "reembolso", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
                {"name": "Internet", "category": "reembolso", "entra_clt": False, "entra_calculo_percentual": False, "recurring": True},
            ]
            
            for rubric_data in rubrics_data:
                rubric = Rubric(
                    tenant_id=tenant.id,
                    **rubric_data
                )
                db.add(rubric)
            
            print(f"✓ {len(rubrics_data)} rubricas criadas")
            
            await db.commit()
            
            print("\n" + "="*60)
            print("SEEDS EXECUTADOS COM SUCESSO!")
            print("="*60)
            print("\nCredenciais de acesso:")
            print(f"  Admin:      admin@financeiro.com / admin123")
            print(f"  Financeiro: financeiro@financeiro.com / financeiro123")
            print("\nAcesse: http://localhost:8000/docs")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"✗ Erro ao criar seeds: {e}")
            await db.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_seeds())
