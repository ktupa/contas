# 💼 Sistema Financeiro Pro

<div align="center">

![Status](https://img.shields.io/badge/status-active-success.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Mobile](https://img.shields.io/badge/mobile-responsive-green.svg)

**Sistema completo de gestão financeira empresarial com interface mobile-first**

[Demo](https://contas.semppreonline.com.br) · [Documentação](#-documentação) · [Reportar Bug](https://github.com/ktupa/contas/issues)

</div>

---

## 📋 Sobre o Projeto

Sistema integrado de gestão financeira e recursos humanos desenvolvido com tecnologias modernas. Oferece controle completo de folha de pagamento, despesas, competências e integração fiscal com a SEFAZ.

### ✨ Principais Funcionalidades

- 👥 **Gestão de Colaboradores** - Cadastro completo com regime CLT/PJ
- 💰 **Folha de Pagamento** - Cálculo automático de proventos e descontos
- 📊 **Competências** - Controle mensal por colaborador
- 💳 **Pagamentos** - Rastreamento de adiantamentos, vales e salários
- 🧾 **Despesas** - Controle de despesas operacionais
- 📝 **Assinaturas Digitais** - Integração com Documenso
- 🏢 **Multi-empresas** - Gestão de múltiplas empresas
- 📈 **Relatórios** - Análises financeiras detalhadas
- 🔐 **Fiscal (NF-e)** - Consulta e manifestação de notas fiscais
- 📱 **Mobile-First** - 100% responsivo e otimizado

---

## 🚀 Tecnologias

**Backend:** FastAPI • PostgreSQL • SQLAlchemy • MinIO  
**Frontend:** Next.js 14 • TypeScript • Mantine UI • Zustand  
**Infra:** Docker • Nginx • SSL/TLS

---

## 📦 Quick Start

```bash
git clone https://github.com/ktupa/contas.git
cd contas
cp backend/.env.example backend/.env
docker-compose up -d
docker-compose exec api alembic upgrade head
```

Acesse: `http://localhost`  
Login: `admin@financeiro.com` / `admin123`

---

## 📱 Interface Responsiva

✅ Mobile-first design  
✅ Tabelas → Cards no mobile  
✅ Modals fullscreen  
✅ Touch-optimized

---

## 📖 Documentação Completa

Veja [ARCHITECTURE.md](ARCHITECTURE.md) e [QUICKSTART.md](QUICKSTART.md)

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit (`git commit -m 'feat: Nova funcionalidade'`)
4. Push (`git push origin feature/NovaFuncionalidade`)
5. Pull Request

---

## 📝 Changelog

**v2.0.0** (16/12/2025)
- ✨ Responsividade mobile completa
- 🔧 Fix cálculo de descontos
- 📱 UX mobile otimizada

**v1.5.0** - Módulo Fiscal (NF-e)  
**v1.0.0** - Release inicial

---

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE)

---

<div align="center">

**⭐ Gostou? Deixe uma estrela!**

Feito com ❤️ por [Sistema Financeiro Pro Team](https://github.com/ktupa)

</div>
