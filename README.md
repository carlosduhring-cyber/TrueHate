# TrueHate

##  Sobre o Projeto

O **TrueHate** é uma plataforma web desenvolvida para permitir o relato de problemas internos em empresas e instituições de ensino. A proposta é oferecer um ambiente seguro onde funcionários ou alunos possam registrar denúncias de forma **anônima ou identificada**, promovendo transparência e melhoria no ambiente organizacional.

##  Funcionalidades

* Registro de denúncias (anônimas ou identificadas)
* Sistema de autenticação de usuários
* Painel administrativo
* Gerenciamento de relatos (visualizar, organizar e acompanhar)
* Interface simples e intuitiva

##  Tecnologias Utilizadas

* **Backend:** Flask (Python)
* **Frontend:** HTML, CSS
* **Banco de Dados:** MySQL

##  Segurança

O sistema foi pensado para preservar a confidencialidade dos usuários, especialmente em relatos anônimos, garantindo maior segurança no envio das informações.

##  Estrutura do Projeto

```
TrueHate/
│-- static/
│-- templates/
│-- app.py
│-- database.sql
│-- requirements.txt
```

##  Como Executar o Projeto

1. Clone o repositório:

```bash
git clone https://github.com/CarlosDuhring/TrueHate.git
```

2. Acesse a pasta do projeto:

```bash
cd TrueHate
```

3. Crie um ambiente virtual:

```bash
python -m venv venv
```

4. Ative o ambiente virtual:

* Linux:

```bash
source venv/bin/activate
```

* Windows:

```bash
venv\Scripts\activate
```

5. Instale as dependências:

```bash
pip install -r requirements.txt
```

6. Configure o banco de dados MySQL e importe o arquivo `database.sql`.

7. Execute a aplicação:

```bash
python app.py
```

8. Acesse no navegador:

```
http://localhost:5000
```

##  Objetivo

O objetivo do TrueHate é incentivar a comunicação interna e ajudar na identificação de problemas organizacionais, contribuindo para ambientes mais saudáveis e seguros.

## 👨‍💻 Autor

Carlos Eduardo Duhring

---

Se este projeto foi útil para você, considere deixar uma ⭐ no repositório!
