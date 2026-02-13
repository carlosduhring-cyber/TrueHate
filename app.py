from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import mysql.connector
from mysql.connector import Error, IntegrityError

app = Flask(__name__)
app.secret_key = 'segredo_super_importante'

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
def conectar():
    try:
        return mysql.connector.connect(
            host="tini.click",
            user="true_hate_app",
            password="5cce0bb5d17104cbc4e51ac1c737422f",
            database="true_hate_app"
        )
    except Error:
        return None

def historico(tipo, detalhes, usuario_id=None, nome=None):
    try:
        conexao = conectar()
        if not conexao: return
        
        cursor = conexao.cursor()
        nome = nome or session.get('usuario') or "Sistema"
        usuario_id = usuario_id or session.get('id_usuario') or 0
        
        cursor.execute("""
            INSERT INTO tb_historico (data_acao, tipo_acao, detalhes, usuario_id, nome_usuario) 
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), tipo, detalhes, usuario_id, nome))
        
        conexao.commit()
        cursor.close()
        conexao.close()
    except:
        pass

def validar(*args):
    return all(arg and str(arg).strip() for arg in args)

# ==============================
# DECORADOR DE ERROS
# ==============================
def tratar_erros(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            flash('Dados duplicados ou inválidos.', 'erro')
        except Error as e:
            flash('Erro no banco de dados.', 'erro')
        except Exception as e:
            print(f"Erro em {func.__name__}: {e}")
            flash('Erro inesperado.', 'erro')
        
        if func.__name__ in ['login', 'usuario', 'cadastro']:
            return render_template(f'{func.__name__}.html' if func.__name__ != 'usuario' else 'cadastro.html')
        return redirect(url_for('index'))
    
    wrapper.__name__ = func.__name__
    return wrapper

# ==============================
# ROTAS PRINCIPAIS
# ==============================
@app.route('/')
@app.route('/index')
@tratar_erros
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@tratar_erros
def login():
    if session.get('logado'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '').strip()
        tipo = request.form.get('tipo', '').strip()
        
        if not validar(usuario, senha, tipo):
            flash('Preencha todos os campos.', 'erro')
            return render_template('login.html')
        
        conexao = conectar()
        if not conexao:
            flash('Erro de conexão.', 'erro')
            return render_template('login.html')
        
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tb_usuario WHERE nome=%s AND senha=%s AND inadmin=%s", (usuario, senha, tipo))
        user = cursor.fetchone()
        cursor.close()
        conexao.close()
        
        if user:
            session.update({
                'logado': True,
                'usuario': user['nome'],
                'senha': user['senha'],
                'id_usuario': user['id'],
                'inadmin': user['inadmin']
            })
            historico("LOGIN", f"Usuário {user['nome']} fez login", user['id'], user['nome'])
            flash('Login realizado!', 'sucesso')
            return redirect(url_for('index'))
        
        flash('Usuário, senha ou tipo incorretos.', 'erro')
    
    return render_template('login.html')

@app.route('/logout')
@tratar_erros
def logout():
    if session.get('logado'):
        historico("LOGOUT", f"Usuário {session.get('usuario')} saiu", session.get('id_usuario'), session.get('usuario'))
    session.clear()
    flash('Logout realizado!', 'sucesso')
    return redirect(url_for('index'))

@app.route('/usuario', methods=['GET', 'POST'])
@tratar_erros
def usuario():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()
        tipo = request.form.get('tipo_conta', '0')
        
        if not validar(nome, email, senha):
            flash('Preencha todos os campos.', 'erro')
            return render_template('cadastro.html')
        
        if '@' not in email or '.' not in email:
            flash('Email inválido.', 'erro')
            return render_template('cadastro.html')
        
        if len(senha) < 4:
            flash('Senha muito curta.', 'erro')
            return render_template('cadastro.html')
        
        conexao = conectar()
        if not conexao:
            flash('Erro de conexão.', 'erro')
            return render_template('cadastro.html')
        
        cursor = conexao.cursor()
        
        # Verificar duplicados
        cursor.execute("SELECT id FROM tb_usuario WHERE email = %s OR nome = %s", (email, nome))
        if cursor.fetchone():
            flash('Email ou nome já cadastrado.', 'erro')
            cursor.close()
            conexao.close()
            return render_template('cadastro.html')
        
        inadmin = int(tipo) if tipo in ['0', '1', '2'] else 0
        cursor.execute("INSERT INTO tb_usuario (nome, email, senha, inadmin) VALUES (%s, %s, %s, %s)", 
                      (nome, email, senha, inadmin))
        conexao.commit()
        
        user_id = cursor.lastrowid
        cursor.close()
        conexao.close()
        
        # Login automático
        session.update({
            'logado': True,
            'usuario': nome,
            'senha': senha,
            'id_usuario': user_id,
            'inadmin': inadmin
        })
        
        tipo_nome = ['Usuário', 'Administrador', 'Empresa'][inadmin]
        historico("CADASTRO", f"Novo {tipo_nome}: {nome} ({email})", user_id, nome)
        flash(f'{tipo_nome} cadastrado!', 'sucesso')
        return redirect(url_for('index'))
    
    return render_template('cadastro.html')

@app.route('/pesquisar', methods=['POST'])
@tratar_erros
def pesquisar():
    termo = request.form.get('pesquisa', '').strip().lower()
    
    if not termo:
        flash('Digite algo para pesquisar!', 'erro')
        return redirect(url_for('index'))
    
    if session.get('logado'):
        historico("PESQUISA", f"Termo: '{termo}'")
    
    conexao = conectar()
    if not conexao:
        flash('Erro de conexão.', 'erro')
        return redirect(url_for('index'))
    
    cursor = conexao.cursor(dictionary=True)
    termo_like = f'%{termo}%'
    
    cursor.execute("""
        SELECT a.*, 
               COALESCE(u.nome, a.nomePessoaPublicou) as nome_usuario,
               COALESCE(u.inadmin, 0) as inadmin,
               (SELECT COUNT(*) FROM tb_comentario c WHERE c.avaliacao_id = a.id) as total_comentarios
        FROM tb_avaliacao a 
        LEFT JOIN tb_usuario u ON a.usuario_id = u.id
        WHERE a.nomePessoaPublicou LIKE %s OR a.texto LIKE %s OR a.nota LIKE %s OR a.nome_empresa LIKE %s
        ORDER BY a.dataPublicada DESC
    """, (termo_like, termo_like, termo_like, termo_like))
    
    resultados = cursor.fetchall()
    
    for r in resultados:
        cursor.execute("""
            SELECT c.*, 
                   COALESCE(u.nome, c.nome_usuario_comentou) as nome_usuario,
                   COALESCE(u.id, 0) as usuario_id,
                   COALESCE(u.inadmin, 0) as inadmin
            FROM tb_comentario c 
            LEFT JOIN tb_usuario u ON c.usuario_id = u.id 
            WHERE c.avaliacao_id = %s AND (c.comentario_pai_id IS NULL OR c.comentario_pai_id = 0)
            ORDER BY c.data_comentario DESC
        """, (r['id'],))
        
        comentarios = cursor.fetchall()
        for c in comentarios:
            cursor.execute("""
                SELECT c.*, 
                       COALESCE(u.nome, c.nome_usuario_comentou) as nome_usuario,
                       COALESCE(u.id, 0) as usuario_id,
                       COALESCE(u.inadmin, 0) as inadmin
                FROM tb_comentario c 
                LEFT JOIN tb_usuario u ON c.usuario_id = u.id 
                WHERE c.comentario_pai_id = %s
                ORDER BY c.data_comentario ASC
            """, (c['id'],))
            c['respostas'] = cursor.fetchall()
        
        r['comentarios'] = comentarios
    
    cursor.close()
    conexao.close()
    
    return render_template('resultados_pesquisa.html', 
                         resultados=resultados, 
                         termo=termo, 
                         total_resultados=len(resultados))

@app.route('/avaliacao/nova', methods=['GET', 'POST'])
@tratar_erros
def nova_avaliacao():
    if session.get('inadmin') == 2:
        flash('Empresas não podem fazer avaliações!', 'erro')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        empresa = request.form.get('nome_empresa', '').strip()
        texto = request.form.get('texto', '').strip()
        nota = request.form.get('nota', '').strip()
        anonimo = request.form.get('anonimo') == 'on'
        
        if not validar(empresa, texto, nota):
            flash('Preencha todos os campos.', 'erro')
            return render_template('nova_avaliacao.html')
        
        try:
            nota_int = int(nota)
            if not 1 <= nota_int <= 5:
                raise ValueError
        except:
            flash('Nota inválida (1-5).', 'erro')
            return render_template('nova_avaliacao.html')
        
        if anonimo:
            nome = "Anônimo"
            user_id = None
        else:
            if not session.get('logado'):
                flash('Faça login para avaliações não anônimas.', 'erro')
                return redirect(url_for('login'))
            nome = session['usuario']
            user_id = session.get('id_usuario')
        
        conexao = conectar()
        if not conexao:
            flash('Erro de conexão.', 'erro')
            return render_template('nova_avaliacao.html')
        
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO tb_avaliacao (nome_empresa, nomePessoaPublicou, texto, nota, dataPublicada, usuario_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (empresa, nome, texto, nota_int, datetime.now().date(), user_id))
        
        conexao.commit()
        cursor.close()
        conexao.close()
        
        tipo = "AVALIAÇÃO_ANONIMA" if anonimo else "AVALIAÇÃO"
        historico(tipo, f"⭐ {nota}/5 - Empresa: {empresa}")
        
        flash('Avaliação publicada!' + (' (Anônimo)' if anonimo else ''), 'sucesso')
        return redirect(url_for('listar_avaliacoes'))
    
    return render_template('nova_avaliacao.html')

@app.route('/avaliacoes')
@tratar_erros
def listar_avaliacoes():
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, 
               COALESCE(u.nome, a.nomePessoaPublicou) as nome_usuario,
               COALESCE(u.inadmin, 0) as inadmin,
               (SELECT COUNT(*) FROM tb_comentario c WHERE c.avaliacao_id = a.id) as total_comentarios
        FROM tb_avaliacao a 
        LEFT JOIN tb_usuario u ON a.usuario_id = u.id
        ORDER BY a.dataPublicada DESC
    """)
    
    avaliacoes = cursor.fetchall()
    
    for a in avaliacoes:
        cursor.execute("""
            SELECT c.*, 
                   COALESCE(u.nome, c.nome_usuario_comentou) as nome_usuario,
                   COALESCE(u.id, 0) as usuario_id,
                   COALESCE(u.inadmin, 0) as inadmin
            FROM tb_comentario c 
            LEFT JOIN tb_usuario u ON c.usuario_id = u.id 
            WHERE c.avaliacao_id = %s AND (c.comentario_pai_id IS NULL OR c.comentario_pai_id = 0)
            ORDER BY c.data_comentario DESC
        """, (a['id'],))
        
        comentarios = cursor.fetchall()
        for c in comentarios:
            cursor.execute("""
                SELECT c.*, 
                       COALESCE(u.nome, c.nome_usuario_comentou) as nome_usuario,
                       COALESCE(u.id, 0) as usuario_id,
                       COALESCE(u.inadmin, 0) as inadmin
                FROM tb_comentario c 
                LEFT JOIN tb_usuario u ON c.usuario_id = u.id 
                WHERE c.comentario_pai_id = %s
                ORDER BY c.data_comentario ASC
            """, (c['id'],))
            c['respostas'] = cursor.fetchall()
        
        a['comentarios'] = comentarios
    
    cursor.close()
    conexao.close()
    return render_template('listar_avaliacoes.html', avaliacoes=avaliacoes)

@app.route('/comentar/<int:avaliacao_id>', methods=['GET', 'POST'])
@tratar_erros
def comentar(avaliacao_id):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_avaliacao WHERE id = %s", (avaliacao_id,))
    avaliacao = cursor.fetchone()
    
    if request.method == 'POST':
        texto = request.form.get('texto', '').strip()
        anonimo = request.form.get('anonimo') == 'on'
        
        if not texto:
            flash('Digite um comentário.', 'erro')
            return render_template('comentarios.html', avaliacao=avaliacao)
        
        if anonimo:
            nome = "Anônimo"
            user_id = None
        else:
            if not session.get('logado'):
                flash('Faça login para comentar.', 'erro')
                return redirect(url_for('login'))
            nome = session['usuario']
            user_id = session.get('id_usuario')
        
        cursor.execute("""
            INSERT INTO tb_comentario (texto, data_comentario, usuario_id, avaliacao_id, nome_usuario_comentou) 
            VALUES (%s, %s, %s, %s, %s)
        """, (texto, datetime.now().date(), user_id, avaliacao_id, nome))
        
        conexao.commit()
        cursor.close()
        conexao.close()
        
        tipo = "COMENTARIO_ANONIMO" if anonimo else "COMENTÁRIO"
        historico(tipo, f"💬 na avaliação #{avaliacao_id}")
        
        flash('Comentário publicado!' + (' (Anônimo)' if anonimo else ''), 'sucesso')
        return redirect(url_for('listar_avaliacoes'))
    
    cursor.close()
    conexao.close()
    return render_template('comentarios.html', avaliacao=avaliacao)

@app.route('/admin', methods=['GET', 'POST'])
@tratar_erros
def administrador():
    if not session.get('logado') or session.get('inadmin') != 1:
        flash('Acesso restrito!', 'erro')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        inadmin = request.form.get('inadmin', '0')
        
        if not validar(usuario):
            flash('Preencha todos os campos.', 'erro')
            return render_template('administrador.html')
        
        conexao = conectar()
        if not conexao:
            flash('Erro de conexão.', 'erro')
            return render_template('administrador.html')
        
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM tb_usuario WHERE nome=%s", (usuario,))  # Corrigido
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE tb_usuario SET inadmin=%s WHERE id=%s", (int(inadmin), user['id']))
            conexao.commit()
            cursor.close()
            conexao.close()
            
            historico("ADMIN", f"Permissões atualizadas para {user['nome']}")
            flash('Permissões atualizadas!', 'sucesso')
            return redirect(url_for('index'))
        
        cursor.close()
        conexao.close()
        flash('Usuário não encontrado.', 'erro')
        return render_template('administrador.html')
    
    return render_template('administrador.html')

@app.route('/editar', methods=['GET', 'POST'])
@tratar_erros
def editar():
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()
        user_id = session['id_usuario']
        
        if not validar(nome, email):
            flash('Nome e email são obrigatórios.', 'erro')
            return redirect(url_for('editar'))
        
        if senha:
            cursor.execute("UPDATE tb_usuario SET nome=%s, email=%s, senha=%s WHERE id=%s", 
                          (nome, email, senha, user_id))
        else:
            cursor.execute("UPDATE tb_usuario SET nome=%s, email=%s WHERE id=%s", 
                          (nome, email, user_id))
        
        conexao.commit()
        historico("EDIÇÃO_PERFIL", f"Perfil atualizado: {nome}")
        session['usuario'] = nome
        flash('Perfil atualizado!', 'sucesso')
        return redirect(url_for('index'))
    
    cursor.execute("SELECT * FROM tb_usuario WHERE id = %s", (session['id_usuario'],))
    item = cursor.fetchone()
    cursor.close()
    conexao.close()
    return render_template('editar.html', item=item)

@app.route('/listusuario')
@tratar_erros
def listusuario():
    if not session.get('logado') or session.get('inadmin') != 1:
        flash('Acesso restrito!', 'erro')
        return redirect(url_for('index'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_usuario")
    dados = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('listarusuario.html', dados=dados)

@app.route('/usuario/excluir/<int:id>')
@tratar_erros
def excluir_usuario(id):
    if not session.get('logado') or session.get('inadmin') != 1:
        flash('Acesso restrito!', 'erro')
        return redirect(url_for('index'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    
    cursor.execute("SELECT nome, email FROM tb_usuario WHERE id=%s", (id,))
    usuario = cursor.fetchone()
    
    cursor.execute("DELETE FROM tb_historico WHERE usuario_id = %s", (id,))
    cursor.execute("DELETE FROM tb_comentario WHERE usuario_id = %s", (id,))
    
    cursor.execute("SELECT id FROM tb_avaliacao WHERE usuario_id = %s", (id,))
    for avaliacao in cursor.fetchall():
        cursor.execute("DELETE FROM tb_comentario WHERE avaliacao_id = %s", (avaliacao['id'],))
        cursor.execute("DELETE FROM tb_avaliacao WHERE id = %s", (avaliacao['id'],))
    
    cursor.execute("DELETE FROM tb_usuario WHERE id=%s", (id,))
    conexao.commit()
    
    if usuario:
        historico("EXCLUSÃO_USUÁRIO", f"Usuário excluído: {usuario['nome']}")
    
    cursor.close()
    conexao.close()
    flash('Usuário excluído!', 'sucesso')
    return redirect(url_for('listusuario'))

@app.route('/editar_avaliacao/<int:id>', methods=['GET', 'POST'])
@tratar_erros
def editar_avaliacao(id):
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_avaliacao WHERE id = %s", (id,))
    avaliacao = cursor.fetchone()
    
    if not avaliacao:
        flash('Avaliação não encontrada!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if session.get('inadmin') != 1 and (avaliacao['usuario_id'] is None or session.get('id_usuario') != avaliacao['usuario_id']):
        flash('Sem permissão!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if request.method == 'POST':
        empresa = request.form.get('nome_empresa', '').strip()
        texto = request.form.get('texto', '').strip()
        nota = request.form.get('nota', '').strip()
        
        if not validar(empresa, texto, nota):
            flash('Preencha todos os campos.', 'erro')
            return render_template('editar_avaliacao.html', avaliacao=avaliacao)
        
        try:
            nota_int = int(nota)
            if not 1 <= nota_int <= 5:
                raise ValueError
        except:
            flash('Nota inválida.', 'erro')
            return render_template('editar_avaliacao.html', avaliacao=avaliacao)
        
        cursor.execute("UPDATE tb_avaliacao SET nome_empresa=%s, texto=%s, nota=%s WHERE id=%s", 
                      (empresa, texto, nota_int, id))
        conexao.commit()
        historico("EDIÇÃO_AVALIAÇÃO", f"Avaliação #{id} atualizada")
        flash('Avaliação atualizada!', 'sucesso')
        return redirect(url_for('listar_avaliacoes'))
    
    cursor.close()
    conexao.close()
    return render_template('editar_avaliacao.html', avaliacao=avaliacao)

@app.route('/excluir_avaliacao/<int:id>')
@tratar_erros
def excluir_avaliacao(id):
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_avaliacao WHERE id = %s", (id,))
    avaliacao = cursor.fetchone()
    
    if not avaliacao:
        flash('Avaliação não encontrada!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if session.get('inadmin') != 1 and (avaliacao['usuario_id'] is None or session.get('id_usuario') != avaliacao['usuario_id']):
        flash('Sem permissão!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    historico("EXCLUSÃO_AVALIAÇÃO", f"Avaliação #{id} excluída")
    cursor.execute("DELETE FROM tb_comentario WHERE avaliacao_id = %s", (id,))
    cursor.execute("DELETE FROM tb_avaliacao WHERE id = %s", (id,))
    conexao.commit()
    
    cursor.close()
    conexao.close()
    flash('Avaliação excluída!', 'sucesso')
    return redirect(url_for('listar_avaliacoes'))

@app.route('/responder_comentario/<int:comentario_id>', methods=['GET', 'POST'])
@tratar_erros
def responder_comentario(comentario_id):
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.*, a.id as avaliacao_id, a.texto as avaliacao_texto 
        FROM tb_comentario c 
        JOIN tb_avaliacao a ON c.avaliacao_id = a.id 
        WHERE c.id = %s
    """, (comentario_id,))
    comentario = cursor.fetchone()
    
    if request.method == 'POST':
        texto = request.form.get('texto', '').strip()
        anonimo = request.form.get('anonimo') == 'on'
        
        if not texto:
            flash('Digite uma resposta.', 'erro')
            return render_template('responder_comentario.html', comentario=comentario)
        
        if anonimo:
            nome = "Anônimo"
            user_id = None
        else:
            if not session.get('logado'):
                flash('Faça login para responder.', 'erro')
                return redirect(url_for('login'))
            nome = session['usuario']
            user_id = session.get('id_usuario')
        
        cursor.execute("""
            INSERT INTO tb_comentario (texto, data_comentario, usuario_id, avaliacao_id, nome_usuario_comentou, comentario_pai_id) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (texto, datetime.now().date(), user_id, comentario['avaliacao_id'], nome, comentario_id))
        
        conexao.commit()
        cursor.close()
        conexao.close()
        
        tipo = "RESPOSTA_ANONIMA" if anonimo else "RESPOSTA"
        historico(tipo, f"Resposta ao comentário #{comentario_id}")
        
        flash('Resposta publicada!' + (' (Anônimo)' if anonimo else ''), 'sucesso')
        return redirect(url_for('listar_avaliacoes'))
    
    cursor.close()
    conexao.close()
    return render_template('responder_comentario.html', comentario=comentario)

@app.route('/editar_comentario/<int:id>', methods=['GET', 'POST'])
@tratar_erros
def editar_comentario(id):
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.*, a.id as avaliacao_id 
        FROM tb_comentario c 
        JOIN tb_avaliacao a ON c.avaliacao_id = a.id 
        WHERE c.id = %s
    """, (id,))
    comentario = cursor.fetchone()
    
    if not comentario:
        flash('Comentário não encontrado!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if session.get('inadmin') != 1 and session.get('id_usuario') != comentario['usuario_id']:
        flash('Sem permissão!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if request.method == 'POST':
        texto = request.form.get('texto', '').strip()
        
        if not texto:
            flash('Digite um comentário.', 'erro')
            return render_template('editar_comentario.html', comentario=comentario)
        
        cursor.execute("UPDATE tb_comentario SET texto=%s WHERE id=%s", (texto, id))
        conexao.commit()
        historico("EDIÇÃO_COMENTÁRIO", f"Comentário #{id} atualizado")
        flash('Comentário atualizado!', 'sucesso')
        return redirect(url_for('listar_avaliacoes'))
    
    cursor.close()
    conexao.close()
    return render_template('editar_comentario.html', comentario=comentario)

@app.route('/excluir_comentario/<int:id>')
@tratar_erros
def excluir_comentario(id):
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_comentario WHERE id = %s", (id,))
    comentario = cursor.fetchone()
    
    if not comentario:
        flash('Comentário não encontrado!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    if session.get('inadmin') != 1 and session.get('id_usuario') != comentario['usuario_id']:
        flash('Sem permissão!', 'erro')
        return redirect(url_for('listar_avaliacoes'))
    
    historico("EXCLUSÃO_COMENTÁRIO", f"Comentário #{id} excluído")
    if comentario['comentario_pai_id'] is None:
        cursor.execute("DELETE FROM tb_comentario WHERE comentario_pai_id = %s", (id,))
    cursor.execute("DELETE FROM tb_comentario WHERE id = %s", (id,))
    conexao.commit()
    
    cursor.close()
    conexao.close()
    flash('Comentário excluído!', 'sucesso')
    return redirect(url_for('listar_avaliacoes'))

@app.route('/meu_historico')
@tratar_erros
def meu_historico():
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    user_id = session['id_usuario']
    
    cursor.execute("""
        SELECT h.*, u.nome as nome_completo
        FROM tb_historico h
        LEFT JOIN tb_usuario u ON h.usuario_id = u.id
        WHERE h.usuario_id = %s
        ORDER BY h.data_acao DESC
        LIMIT 50
    """, (user_id,))
    
    historico = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('meu_historico.html', historico=historico)

@app.route('/historico_admin')
@tratar_erros
def historico_admin():
    if not session.get('logado') or session.get('inadmin') != 1:
        flash('Acesso restrito!', 'erro')
        return redirect(url_for('index'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT h.*, u.nome as nome_completo
        FROM tb_historico h
        LEFT JOIN tb_usuario u ON h.usuario_id = u.id
        ORDER BY h.data_acao DESC
        LIMIT 100
    """)
    
    historico = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('historico_admin.html', historico=historico)

@app.route('/editar_usuario/<int:usuario_id>', methods=['GET', 'POST'])
@tratar_erros
def editar_usuario(usuario_id):
    if not session.get('logado') or session.get('inadmin') != 1:
        flash('Acesso restrito!', 'erro')
        return redirect(url_for('index'))
    
    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '').strip()
        inadmin = request.form.get('inadmin', '0')
        
        if not validar(nome, email):
            flash('Nome e email são obrigatórios.', 'erro')
            return redirect(url_for('editar_usuario', usuario_id=usuario_id))
        
        if senha:
            cursor.execute("UPDATE tb_usuario SET nome=%s, email=%s, senha=%s, inadmin=%s WHERE id=%s", 
                          (nome, email, senha, int(inadmin), usuario_id))
        else:
            cursor.execute("UPDATE tb_usuario SET nome=%s, email=%s, inadmin=%s WHERE id=%s", 
                          (nome, email, int(inadmin), usuario_id))
        
        conexao.commit()
        historico("EDIÇÃO_USUÁRIO", f"Usuário editado: {nome}")
        flash('Usuário atualizado!', 'sucesso')
        return redirect(url_for('listusuario'))
    
    cursor.execute("SELECT * FROM tb_usuario WHERE id = %s", (usuario_id,))
    item = cursor.fetchone()
    cursor.close()
    conexao.close()
    
    if not item:
        flash('Usuário não encontrado!', 'erro')
        return redirect(url_for('listusuario'))
    
    return render_template('editar_usuario.html', item=item)

@app.route('/perfil')
@tratar_erros
def perfil():
    if not session.get('logado'):
        flash('Faça login para ver seu perfil.', 'erro')
        return redirect(url_for('login'))
    
    conexao = conectar()
    if not conexao:
        flash('Erro de conexão.', 'erro')
        return render_template('perfil.html', 
                             total_avaliacoes=0,
                             total_comentarios=0,
                             total_pesquisas=0,
                             dias_cadastro=0,
                             ultimas_avaliacoes=[],
                             data_cadastro='',
                             ultimo_login='')
    
    cursor = conexao.cursor(dictionary=True)
    user_id = session['id_usuario']
    
    # 1. Contar avaliações do usuário
    cursor.execute("SELECT COUNT(*) as total FROM tb_avaliacao WHERE usuario_id = %s", (user_id,))
    total_avaliacoes = cursor.fetchone()['total']
    
    # 2. Contar comentários do usuário
    cursor.execute("SELECT COUNT(*) as total FROM tb_comentario WHERE usuario_id = %s", (user_id,))
    total_comentarios = cursor.fetchone()['total']
    
    # 3. Contar pesquisas do usuário (do histórico)
    cursor.execute("SELECT COUNT(*) as total FROM tb_historico WHERE usuario_id = %s AND tipo_acao = 'PESQUISA'", (user_id,))
    total_pesquisas = cursor.fetchone()['total']
    
    # 4. Data de cadastro do usuário
    cursor.execute("SELECT criado_em FROM tb_usuario WHERE id = %s", (user_id,))
    usuario_info = cursor.fetchone()
    data_cadastro = usuario_info['criado_em'].strftime('%d/%m/%Y') if usuario_info and usuario_info['criado_em'] else 'Desconhecida'
    
    # 5. Último login (do histórico)
    cursor.execute("""
        SELECT data_acao FROM tb_historico 
        WHERE usuario_id = %s AND tipo_acao = 'LOGIN' 
        ORDER BY data_acao DESC LIMIT 1
    """, (user_id,))
    ultimo_login_result = cursor.fetchone()
    ultimo_login = ultimo_login_result['data_acao'].strftime('%d/%m/%Y %H:%M') if ultimo_login_result else 'Nunca'
    
    # 6. Dias no sistema
    if usuario_info and usuario_info['criado_em']:
        dias_cadastro = (datetime.now().date() - usuario_info['criado_em'].date()).days
    else:
        dias_cadastro = 0
    
    # 7. Últimas 3 avaliações do usuário
    cursor.execute("""
        SELECT * FROM tb_avaliacao 
        WHERE usuario_id = %s 
        ORDER BY dataPublicada DESC 
        LIMIT 3
    """, (user_id,))
    ultimas_avaliacoes = cursor.fetchall()
    
    cursor.close()
    conexao.close()
    
    return render_template('perfil.html', 
                         total_avaliacoes=total_avaliacoes,
                         total_comentarios=total_comentarios,
                         total_pesquisas=total_pesquisas,
                         dias_cadastro=dias_cadastro,
                         ultimas_avaliacoes=ultimas_avaliacoes,
                         data_cadastro=data_cadastro,
                         ultimo_login=ultimo_login)

# ==============================
# MANIPULADORES DE ERRO
# ==============================
@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template('erro_404.html'), 404

@app.errorhandler(500)
def erro_interno(e):
    return render_template('erro_500.html'), 500

@app.route('/sobre')
@tratar_erros
def sobre():
    return render_template('sobre.html')

@app.route('/relatar_problema', methods=['GET', 'POST'])
@tratar_erros
def relatar_problema():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip()
        telefone = request.form.get('telefone', '').strip()
        problema = request.form.get('problema', '').strip()

        if not validar(nome, email, telefone, problema):
            flash("Preencha todos os campos!", "erro")
            return render_template('relatar_problema.html')

        conexao = conectar()
        if not conexao:
            flash("Erro ao conectar ao banco.", "erro")
            return render_template('relatar_problema.html')

        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO tb_problemas (nome, email, telefone, problema, data_envio)
            VALUES (%s, %s, %s, %s, %s)
        """, (nome, email, telefone, problema, datetime.now()))

        conexao.commit()
        cursor.close()
        conexao.close()

        historico("RELATO_PROBLEMA", f"Problema reportado por {nome}")

        flash("Problema enviado com sucesso!", "sucesso")
        return redirect(url_for('index'))

    return render_template('relatar_problema.html')


@app.route('/admin/problemas')
@tratar_erros
def admin_problemas():
    if not session.get('logado') or session.get('inadmin') != 1:
        flash("Acesso restrito!", "erro")
        return redirect(url_for('index'))

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tb_problemas ORDER BY data_envio DESC")
    problemas = cursor.fetchall()
    cursor.close()
    conexao.close()

    return render_template('admin_problemas.html', problemas=problemas)

@app.route('/admin/problemas/excluir/<int:id>')
@tratar_erros
def excluir_problema(id):
    if not session.get('logado') or session.get('inadmin') != 1:
        flash("Acesso restrito!", "erro")
        return redirect(url_for('index'))

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("SELECT nome FROM tb_problemas WHERE id = %s", (id,))
    problema = cursor.fetchone()

    if not problema:
        flash("Problema não encontrado!", "erro")
        return redirect(url_for('admin_problemas'))

    cursor.execute("DELETE FROM tb_problemas WHERE id = %s", (id,))
    conexao.commit()

    historico("EXCLUSÃO_PROBLEMA", f"Problema #{id} excluído")

    cursor.close()
    conexao.close()

    flash("Problema excluído com sucesso!", "sucesso")
    return redirect(url_for('admin_problemas'))

# ==============================
# INICIALIZAÇÃO
# ==============================
if __name__ == '__main__':
    app.run(debug=True)
    
    

