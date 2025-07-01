import os
import json
from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

# 1. Configuração do Flask
app = Flask(__name__)

# 2. Configuração da Conexão com o Banco de Dados
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DEBUG: Lendo DATABASE_URL: {'Definida' if DATABASE_URL else 'Nao definida'}")

if not DATABASE_URL:
    raise Exception("A variável de ambiente 'DATABASE_URL' não foi definida.")

def get_db_connection():
    """Cria e retorna uma nova conexão com o banco de dados."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise

def inicializar_banco():
    """Cria as tabelas iniciais do banco de dados se elas não existirem."""
    print("DEBUG DB: Tentando inicializar o banco de dados...")
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
    finally:
        if conn is not None:
            conn.close()

# 3. Endpoints da API

@app.route('/api/status', methods=['GET'])
def status():
    """Verifica o status da API."""
    return jsonify({"status": "API is running"})

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    """Retorna uma lista de produtos (atualmente vazia)."""
    # Em uma implementação futura, buscaria os produtos do banco de dados.
    return jsonify([])

@app.route('/api/produtos', methods=['POST'])
def add_produto():
    """Recebe um novo produto e loga os dados."""
    produto_data = request.json
    print(f"DEBUG: Produto recebido via POST: {json.dumps(produto_data, indent=2)}")
    # A lógica para salvar no banco de dados seria implementada aqui.
    return jsonify({"message": "Produto recebido (ainda nao salvo)"}), 201

# 4. Bloco de Execução Principal
if __name__ == '__main__':
    # Inicializa o banco de dados na inicialização do aplicativo
    inicializar_banco()

    # Obtém a porta do ambiente ou usa 5000 como padrão
    port = int(os.environ.get('PORT', 5000))
    print(f"DEBUG: Lendo PORT: {port}")

    # Inicia o servidor Flask
    print(f"Iniciando servidor Flask na porta {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
