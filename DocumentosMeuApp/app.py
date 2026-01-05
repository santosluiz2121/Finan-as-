import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
import plotly.express as px
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Budget Buddy Pro", page_icon="🔒", layout="wide")

# --- FUNÇÕES DE SEGURANÇA E BANCO DE DADOS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

conn = sqlite3.connect('budget_pro.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, password TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions 
                 (id INTEGER PRIMARY KEY, user TEXT, date TEXT, name TEXT, 
                  type TEXT, category TEXT, amount REAL)''')
    conn.commit()

init_db()

# --- LÓGICA DE USUÁRIO ---
def create_user(username, password):
    c.execute('INSERT INTO users(username, password) VALUES (?,?)', (username, make_hashes(password)))
    conn.commit()

def login_user(username, password):
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, make_hashes(password)))
    return c.fetchone()

# --- INTERFACE DE LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔐 Acesso ao Budget Buddy")
    
    menu = ["Login", "Criar Conta"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Login":
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type='password')
        if st.button("Entrar"):
            result = login_user(user, password)
            if result:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

    elif choice == "Criar Conta":
        new_user = st.text_input("Novo Usuário")
        new_password = st.text_input("Nova Senha", type='password')
        if st.button("Registrar"):
            try:
                create_user(new_user, new_password)
                st.success("Conta criada! Vá para o Login.")
            except:
                st.error("Usuário já existe.")
else:
    # --- APLICATIVO APÓS LOGIN ---
    current_user = st.session_state['username']
    
    st.sidebar.title(f"Bem-vindo, {current_user}!")
    if st.sidebar.button("Sair"):
        st.session_state['logged_in'] = False
        st.rerun()

    st.title("💰 Budget Buddy Pro")
    st.markdown("---")

    # --- BARRA LATERAL: ENTRADA DE DADOS ---
    st.sidebar.header("Nova Transação")
    t_date = st.sidebar.date_input("Data", datetime.now())
    t_name = st.sidebar.text_input("Descrição")
    t_type = st.sidebar.selectbox("Tipo", ["Receita", "Despesa"])
    t_cat = st.sidebar.selectbox("Categoria", ["Alimentação", "Lazer", "Salário", "Transporte", "Moradia", "Saúde", "Outros"])
    t_amount = st.sidebar.number_input("Valor (R$)", min_value=0.0, step=0.1)

    if st.sidebar.button("Adicionar"):
        c.execute('INSERT INTO transactions (user, date, name, type, category, amount) VALUES (?,?,?,?,?,?)',
                  (current_user, t_date, t_name, t_type, t_cat, t_amount))
        conn.commit()
        st.sidebar.success("Adicionado!")
        st.rerun()

    # --- DASHBOARD ---
    df = pd.read_sql_query('SELECT * FROM transactions WHERE user = ? ORDER BY date DESC', conn, params=(current_user,))

    if not df.empty:
        # Métricas Rápidas
        receitas = df[df['type'] == 'Receita']['amount'].sum()
        despesas = df[df['type'] == 'Despesa']['amount'].sum()
        saldo = receitas - despesas

        m1, m2, m3 = st.columns(3)
        m1.metric("Saldo", f"R$ {saldo:,.2f}")
        m2.metric("Receitas", f"R$ {receitas:,.2f}")
        m3.metric("Despesas", f"R$ {despesas:,.2f}")

        # Gráficos
        st.markdown("### Visualização de Gastos")
        c1, c2 = st.columns(2)

        with c1:
            df_gastos = df[df['type'] == 'Despesa']
            fig = px.pie(df_gastos, values='amount', names='category', title="Gastos por Categoria", hole=0.3)
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.markdown("### Histórico")
            st.dataframe(df[['date', 'name', 'category', 'amount', 'type']], use_container_width=True)

        # --- EXPORTAÇÃO ---
        st.markdown("---")
        st.subheader("📥 Exportar Dados")
        
        # Gerar Excel em memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Relatório')
        
        st.download_button(
            label="Baixar Relatório em Excel",
            data=output.getvalue(),
            file_name=f"finance_buddy_{current_user}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.info("Nenhum dado registrado ainda. Use o menu à esquerda!")