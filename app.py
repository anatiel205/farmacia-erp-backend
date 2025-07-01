import os
import json
from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras

# 1. Configurações Iniciais
app = Flask(__name__, template_folder='templates', static_folder='static')

# 2. Configuração da Conexão com o Banco de Dados
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DEBUG: Lendo DATABASE_URL: {'Definida' if DATABASE_URL else 'Nao definida'}")

if not DATABASE_URL:
    raise Exception("A variável de ambiente 'DATABASE_URL' não foi definida.")

# 3. Funções de Banco de Dados

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro fatal ao conectar ao banco de dados: {e}")
        raise

def inicializar_banco():
    """Cria as tabelas iniciais do banco de dados se elas não existirem."""
    print("DEBUG DB: Verificando e inicializando o banco de dados...")
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Tabela de Farmácias
        print("DEBUG DB: Criando tabela 'farmacias' se não existir...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS farmacias (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT NOT NULL,
                telefone TEXT,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tabela de Produtos
        print("DEBUG DB: Criando tabela 'produtos' se não existir...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                farmacia_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                descricao TEXT,
                preco NUMERIC(10, 2) NOT NULL,
                quantidade INTEGER DEFAULT 0,
                codigo_barras TEXT UNIQUE,
                criado_em TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_farmacia
                    FOREIGN KEY(farmacia_id)
                    REFERENCES farmacias(id)
                    ON DELETE CASCADE
            );
        """)

        conn.commit()
        cur.close()
        print("DEBUG DB: Tabelas verificadas/criadas com sucesso.")
    except psycopg2.Error as e:
        print(f"Erro na inicialização do banco de dados: {e}")
        raise  # Lança a exceção para interromper a execução se o DB falhar
    finally:
        if conn is not None:
            conn.close()

# 4. Endpoints da API (JSON)

@app.route('/api/status', methods=['GET'])
def api_status():
    """Verifica o status da API."""
    return jsonify({"status": "API is running"})

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    """Retorna uma lista de produtos (atualmente vazia)."""
    return jsonify([])

@app.route('/api/produtos', methods=['POST'])
def add_produto():
    """Recebe um novo produto, loga e retorna uma mensagem."""
    produto_data = request.json
    print(f"DEBUG: Produto recebido via API: {json.dumps(produto_data, indent=2)}")
    return jsonify({"message": "Produto recebido (ainda nao salvo)"}), 201

@app.route('/api/farmacias', methods=['GET'])
def get_farmacias():
    """Retorna uma lista de farmácias (atualmente vazia)."""
    return jsonify([])

@app.route('/api/farmacias', methods=['POST'])
def add_farmacia():
    """Recebe uma nova farmácia, loga e retorna uma mensagem."""
    farmacia_data = request.json
    print(f"DEBUG: Farmácia recebida via API: {json.dumps(farmacia_data, indent=2)}")
    return jsonify({"message": "Farmacia recebida (ainda nao salva)"}), 201

# 5. Endpoints para Páginas Web (HTML)

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

# 6. Bloco de Execução Principal
if __name__ == '__main__':
    try:
        # Inicializa o banco de dados na inicialização do aplicativo
        inicializar_banco()

        port = int(os.environ.get('PORT', 5000))
        print(f"DEBUG: Lendo PORT: {port}")

        # Define o modo debug com base em uma variável de ambiente
        is_debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        print(f"DEBUG: Modo debug: {is_debug}")

        # Inicia o servidor Flask
        print(f"Iniciando servidor Flask em http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=is_debug)

    except Exception as e:
        print(f"Erro fatal ao iniciar a aplicação: {e}")
        # Em um ambiente de produção, isso seria logado em um sistema de monitoramento
        os._exit(1)  # Sai com código de erro
