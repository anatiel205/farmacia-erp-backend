# app.py - Backend da API e Servidor Web para ERP de Farmácias

import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras

# --- 1. Configuração do Aplicativo Flask ---
app = Flask(__name__, template_folder='templates', static_folder='static')

# --- 2. Configuração da Conexão ao Banco de Dados ---
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DEBUG: Lendo DATABASE_URL: {'Definida' if DATABASE_URL else 'Nao definida'}")

if not DATABASE_URL:
    print("ERRO CRÍTICO: A variável de ambiente 'DATABASE_URL' não foi definida.")
    raise Exception("A variável de ambiente 'DATABASE_URL' é obrigatória para a conexão com o PostgreSQL.")

# --- 3. Funções de Banco de Dados ---

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERRO CRÍTICO: Falha ao conectar ao banco de dados. Detalhes: {e}")
        raise

def inicializar_banco():
    """Cria as tabelas iniciais do banco de dados se elas não existirem."""
    print("DEBUG DB: Iniciando processo de inicialização do banco de dados...")
    conn = None
    try:
        conn = get_db_connection()
        print("DEBUG DB: Conexão com o banco de dados estabelecida.")
        cur = conn.cursor()

        # Tabela de Farmácias
        print("DEBUG DB: Criando tabela 'farmacias'...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS farmacias (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(100) UNIQUE NOT NULL, -- Adicionado UNIQUE para nome
            endereco TEXT,
            telefone VARCHAR(20),
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        print("DEBUG DB: Tabela 'farmacias' verificada/pronta.")

        # Tabela de Produtos
        print("DEBUG DB: Criando tabela 'produtos'...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            farmacia_id INTEGER NOT NULL,
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            preco NUMERIC(10,2) NOT NULL,
            quantidade INTEGER DEFAULT 0,
            codigo_barras VARCHAR(50) UNIQUE, -- Adicionado UNIQUE para codigo_barras
            criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
            ON DELETE CASCADE
        );
        """)
        print("DEBUG DB: Tabela 'produtos' verificada/pronta.")

        # Outras tabelas podem ser adicionadas aqui (vendas, gastos, etc.)

        conn.commit()
        cur.close()
        print("DEBUG DB: Inicialização do banco de dados concluída com sucesso.")
    except psycopg2.Error as e:
        print(f"ERRO DB: Falha ao inicializar as tabelas do banco de dados. Detalhes: {e}")
        # SE ESTE ERRO APARECER, O DEPLOY VAI FALHAR!
        os._exit(1) # Força a saída do processo com erro se o DB falhar
    finally:
        if conn is not None:
            conn.close()
            print("DEBUG DB: Conexão com o banco de dados fechada.")

# --- 4. Endpoints da API (JSON) ---

@app.route('/api/status', methods=['GET'])
def api_status():
    """Verifica o status da API."""
    return jsonify({"status": "API is running"}), 200

@app.route('/api/farmacias', methods=['POST'])
def add_farmacia():
    """Adiciona uma nova farmácia ao banco de dados."""
    farmacia_data = request.json
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        nome = farmacia_data.get('nome')
        endereco = farmacia_data.get('endereco')
        telefone = farmacia_data.get('telefone')

        if not nome:
            return jsonify({"error": "Nome da farmácia é obrigatório."}), 400

        cur.execute("""
            INSERT INTO farmacias (nome, endereco, telefone, criado_em)
            VALUES (%s, %s, %s, %s) RETURNING id;
        """, (nome, endereco, telefone, datetime.now()))
        
        farmacia_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        print(f"DEBUG DB: Farmácia '{nome}' salva com ID: {farmacia_id}")
        return jsonify({"message": "Farmácia salva com sucesso", "farmacia_id": farmacia_id}), 201
    except (psycopg2.IntegrityError) as e: # Captura erros de UNIQUE (nome já existe)
        if "duplicate key value violates unique constraint" in str(e):
             print(f"ERRO DB: Farmácia '{nome}' já existe: {e}")
             return jsonify({"error": "Farmácia com este nome já existe."}), 409 # Conflict
        else:
             print(f"ERRO DB: Falha ao salvar farmácia. Detalhes: {e}")
             if conn: conn.rollback()
             return jsonify({"error": f"Erro ao salvar farmácia: {e}"}), 500
    except Exception as e: # Captura outros erros
        print(f"ERRO DB: Falha ao salvar farmácia. Detalhes: {e}")
        if conn: conn.rollback()
        return jsonify({"error": f"Erro ao salvar farmácia: {e}"}), 500
    finally:
        if conn: conn.close()


@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    """Retorna uma lista de produtos para a farmácia com ID 1 (padrão para testes)."""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        # Assumindo farmacia_id=1 para testes por enquanto
        cur.execute("SELECT id, farmacia_id, nome, descricao, preco, quantidade, codigo_barras FROM produtos WHERE farmacia_id = %s ORDER BY nome ASC;", (1,))
        produtos = [dict(row) for row in cur.fetchall()]
        cur.close()
        return jsonify(produtos), 200
    except psycopg2.Error as e:
        print(f"ERRO DB: Falha ao buscar produtos. Detalhes: {e}")
        return jsonify({"error": "Erro interno do servidor ao buscar produtos."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/produtos', methods=['POST'])
def add_produto():
    """Adiciona um novo produto ao banco de dados."""
    produto_data = request.json
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Usa farmacia_id=1 como padrão se não for fornecido ou se o sistema não tiver autenticação de farmácia
        farmacia_id = produto_data.get('farmacia_id', 1) 
        
        # Validação básica de campos obrigatórios
        nome = produto_data.get('nome')
        preco = produto_data.get('preco')
        if not nome or preco is None:
            return jsonify({"error": "Nome e preço do produto são obrigatórios."}), 400

        cur.execute("""
            INSERT INTO produtos (farmacia_id, nome, descricao, preco, quantidade, codigo_barras, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;
        """, (
            farmacia_id,
            nome,
            produto_data.get('descricao'),
            preco,
            produto_data.get('quantidade', 0),
            produto_data.get('codigo_barras'),
            datetime.now()
        ))
        produto_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        print(f"DEBUG DB: Produto '{nome}' salvo com ID: {produto_id}")
        return jsonify({"message": "Produto salvo com sucesso", "produto_id": produto_id}), 201
    except psycopg2.IntegrityError as e: # Captura erros de chave estrangeira ou UNIQUE
        if "foreign key constraint" in str(e):
            print(f"ERRO DB: Farmacia_id {farmacia_id} não existe: {e}")
            return jsonify({"error": "Farmácia com o ID fornecido não existe."}), 400
        elif "duplicate key value violates unique constraint" in str(e) and 'codigo_barras' in str(e):
             print(f"ERRO DB: Código de barras '{produto_data.get('codigo_barras')}' já existe: {e}")
             return jsonify({"error": "Produto com este código de barras já existe."}), 409
        else:
             print(f"ERRO DB: Falha de integridade ao salvar produto. Detalhes: {e}")
             if conn: conn.rollback()
             return jsonify({"error": f"Erro de integridade ao salvar produto: {e}"}), 500
    except Exception as e:
        print(f"ERRO DB: Falha geral ao salvar produto. Detalhes: {e}")
        if conn: conn.rollback()
        return jsonify({"error": f"Erro geral ao salvar produto: {e}"}), 500
    finally:
        if conn: conn.close()

# --- 5. Endpoints para Páginas Web (HTML) ---

@app.route('/', methods=['GET'])
def index():
    """Renderiza a página inicial."""
    return render_template('index.html', title="Bem-vindo ao ERP Farmácia")

@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Renderiza o painel principal."""
    return render_template('dashboard.html', title="Dashboard da Farmácia")

@app.route('/pdv', methods=['GET'])
def pdv():
    """Renderiza o painel de venda rápida."""
    return render_template('pdv.html', title="Painel de Venda Rápida")

# --- 6. Bloco de Execução Principal ---

if __name__ == '__main__':
    try:
        print("INFO: Iniciando aplicação...")
        inicializar_banco() # Inicializa o banco de dados na inicialização do aplicativo
        print("INFO: Banco de dados pronto.")

        port = int(os.environ.get('PORT', 5000))
        print(f"DEBUG: Lendo PORT: {port}")

        is_debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        print(f"DEBUG: Modo debug: {is_debug}")

        print(f"INFO: Servidor Flask pronto para iniciar em http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=is_debug)

    except Exception as e:
        print(f"ERRO CRÍTICO: Falha ao iniciar a aplicação. Detalhes: {e}")
        os._exit(1) # Sai com código de erro se houver falha na inicialização
