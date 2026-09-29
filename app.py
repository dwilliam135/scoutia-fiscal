import streamlit as st
import pandas as pd
import os
import requests
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

st.title("🛡️ ScoutIA Fiscal — Detecção de Fraudes e Fechamentos")
st.markdown("Suba seus relatórios financeiros ou múltiplos XMLs para identificar **notas duplicadas, superfaturamento e anomalias**.")

# --- BANCO DE DADOS DE LICENÇAS COMERCIAIS ---
BANCO_DE_LICENCAS = {
    "LICENCA-STARTER-100": {"plano": "Starter", "limite_linhas": 20, "preco": "R$ 2.490/mês"},
    "LICENCA-ENTERPRISE-500": {"plano": "Enterprise", "limite_linhas": 200, "preco": "R$ 7.990/mês"},
    "LICENCA-PRO-999": {"plano": "Pro Custom", "limite_linhas": float('inf'), "preco": "Sob Consulta"}
}

st.sidebar.subheader("🔑 Autenticação do Cliente")
licenca_usuario = st.sidebar.text_input("Insira sua Chave de Licença ScoutIA:", type="password").strip()

# --- INICIALIZAÇÃO DA API GEMINI ---
# Tenta pegar a chave dos Secrets do Streamlit ou da variável de ambiente tradicional
CHAVE_INTERNA_IA = ""
if "GEMINI_API_KEY" in st.secrets:
    CHAVE_INTERNA_IA = st.secrets["GEMINI_API_KEY"]
else:
    CHAVE_INTERNA_IA = os.environ.get("GEMINI_API_KEY", "")

# Cria o cliente da IA se houver uma chave definida
client = None
if CHAVE_INTERNA_IA:
    try:
        client = genai.Client(api_key=CHAVE_INTERNA_IA)
    except Exception as e:
        st.sidebar.error(f"Erro ao inicializar cliente da IA: {str(e)}")

# Exibe aviso na barra lateral se a IA não estiver configurada
if not client:
    st.sidebar.warning("⚠️ IA offline: Defina a chave GEMINI_API_KEY nos Secrets do Streamlit.")

WEBHOOK_MONITORAMENTO = "https://google.com"

# Upload de arquivos (Híbrido)
arquivos_upload = st.file_uploader("Escolha o relatório CSV ou selecione múltiplas Notas Fiscais XML", type=["csv", "xml"], accept_multiple_files=True)

df = None
nome_arquivo_log = ""

if arquivos_upload and len(arquivos_upload) > 0:
    primeiro_arquivo = arquivos_upload[0]
    
    # CASO 1: PROCESSAMENTO DE ARQUIVO CSV
    if primeiro_arquivo.name.endswith('.csv'):
        try:
            df = pd.read_csv(primeiro_arquivo)
            nome_arquivo_log = primeiro_arquivo.name
            
            mapeamento_colunas = {
                'id_transacao': 'Numero_NF',
                'data': 'Data_Emissao',
                'descricao': 'Nome_Emitente',
                'categoria': 'Natureza_Operacao',
                'valor': 'Valor_Total'
            }
            
            df = df.rename(columns=mapeamento_colunas)
            
            if 'CNPJ_Emitente' not in df.columns:
                df['CNPJ_Emitente'] = df['Nome_Emitente']
                
            st.success(f"Relatório CSV '{nome_arquivo_log}' carregado e padronizado! ({len(df)} registros)")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV: {str(e)}")
            
    # CASO 2: PROCESSAMENTO DE MÚLTIPLOS XMLs
    else:
        st.info(f"Processando {len(arquivos_upload)} arquivo(s) XML...")
        dados_processados = []
        for arquivo in arquivos_upload:
            if arquivo.name.endswith('.xml'):
                try:
                    tree = ET.parse(arquivo)
                    root = tree.getroot()
                    
                    ns = {'ns': 'http://portalfiscal.inf.br'}
                    
                    def find_element(path):
                        el = root.find(f'.//ns:{path}', ns)
                        if el is None:
                            el = root.find(f'.//{path}')
                        return el

                    ide = find_element('ide')
                    emit = find_element('emit')
                    dest = find_element('dest')
                    total = find_element('ICMSTot')
                    infNfe = find_element('infNfe')
                    
                    dados_nota = {
                        "Chave_Acesso": infNfe.attrib.get('Id', '')[3:] if infNfe is not None else "N/A",
                        "Numero_NF": ide.find('{http://portalfiscal.inf.br}nNF').text if ide is not None and ide.find('{http://portalfiscal.inf.br}nNF') is not None else (ide.find('nNF').text if ide is not None and ide.find('nNF') is not None else "N/A"),
                        "Data_Emissao": ide.find('{http://portalfiscal.inf.br}dhEmi').text[:10] if ide is not None and ide.find('{http://portalfiscal.inf.br}dhEmi') is not None else (ide.find('dhEmi').text[:10] if ide is not None and ide.find('dhEmi') is not None else "N/A"),
                        "CNPJ_Emitente": emit.find('{http://portalfiscal.inf.br}CNPJ').text if emit is not None and emit.find('{http://portalfiscal.inf.br}CNPJ') is not None else (emit.find('CNPJ').text if emit is not None and emit.find('CNPJ') is not None else "N/A"),
                        "Nome_Emitente": emit.find('{http://portalfiscal.inf.br}xNome').text if emit is not None and emit.find('{http://portalfiscal.inf.br}xNome') is not None else (emit.find('xNome').text if emit is not None and emit.find('xNome') is not None else "N/A"),
                        "CNPJ_Destinatario": dest.find('{http://portalfiscal.inf.br}CNPJ').text if dest is not None and dest.find('{http://portalfiscal.inf.br}CNPJ') is not None else (dest.find('CNPJ').text if dest is not None and dest.find('CNPJ') is not None else "N/A"),
                        "Valor_Total": float(total.find('{http://portalfiscal.inf.br}vNF').text) if total is not None and total.find('{http://portalfiscal.inf.br}vNF') is not None else (float(total.find('vNF').text) if total is not None and total.find('vNF') is not None else 0.0),
                        "Natureza_Operacao": ide.find('{http://portalfiscal.inf.br}natOp').text if ide is not None and ide.find('{http://portalfiscal.inf.br}natOp') is not None else (ide.find('natOp').text if ide is not None and ide.find('natOp') is not None else "N/A")
                    }
                    dados_processados.append(dados_nota)
                except Exception as e:
                    st.warning(f"Erro ao processar o XML {arquivo.name}: {str(e)}")
        
        if dados_processados:
            df = pd.DataFrame(dados_processados)
            nome_arquivo_log = f"Lote_XML_{len(dados_processados)}_notas.csv"
            st.success(f"{len(df)} Nota(s) Fiscal(ais) consolidada(s) com sucesso!")

# APLICAÇÃO DAS REGRAS DE AUDITORIA E ANÁLISE ESTATÍSTICA
if df is not None:
    if licenca_usuario in BANCO_DE_LICENCAS:
        info_plano = BANCO_DE_LICENCAS[licenca_usuario]
        limite = info_plano["limite_linhas"]
        if len(df) > limite:
            st.warning(f"Contrato {info_plano['plano']} limita a análise a {limite} linhas. Dados truncados.")
            df = df.head(limite)
    else:
        st.sidebar.error("Modo Demonstração: Limitado a 50 registros para testes.")
        df = df.head(50)
    
    st.subheader("📋 Painel de Dados Consolidados")
    st.dataframe(df)

    # --- MOTOR DE PRÉ-AUDITORIA DETECTIVA (PANDAS) ---
    st.subheader("🔍 Triagem Automatizada de Riscos")
    
    df['Numero_NF'] = df['Numero_NF'].astype(str)
    df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str)
    df['Valor_Total'] = pd.to_numeric(df['Valor_Total'], errors='coerce').fillna(0.0)
    
    # 1. Detecção de Notas/Transações Duplicadas
    duplicadas = df[df.duplicated(subset=['Numero_NF', 'Valor_Total'], keep=False)]
    
    # 2. Desvios e Possível Superfaturamento
    media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
    desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
    
    superfaturadas = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Suspeitas de Duplicidade (Mesmo ID/Valor)", len(duplicadas))
        if not duplicadas.empty:
            st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']])
            
    with col2:
        st.metric("Desvios Críticos de Valor", len(superfaturadas))
        if not superfaturadas.empty:
            st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']])

    # --- DISPARO DA INTELIGÊNCIA ARTIFICIAL ---
    if st.button("🛡️ Gerar Parecer Antifraude com ScoutIA"):
        if not client:
            st.error("Erro: A IA não pôde ser iniciada. Certifique-se de configurar a variável 'GEMINI_API_KEY' nas configurações (Secrets) do seu painel Streamlit.")
        else:
            with st.spinner("A IA está cruzando os indícios e redigindo o parecer técnico..."):
                try:
                    resumo_auditoria = {
                        "total_transacoes_analisadas": len(df),
                        "total_valor_movimentado": float(df['Valor_Total'].sum()),
                        "casos_duplicidade_detectados": duplicadas.head(10).to_dict(orient='records'),
                        "casos_desvio_valor_detectados": superfaturadas.head(10).to_dict(orient='records'),
                        "maiores_gastos_por_categoria": df.groupby('Natureza_Operacao')['Valor_Total'].sum().nlargest(5).to_dict()
                    }
                    
                    prompt_sistema = (
                        "Você é um Perito Forense Digital e Auditor Fiscal Sênior especializado em Compliance e Prevenção a Fraudes. "
                        "Analise o resumo dos dados de fechamento fornecidos. Seu papel é emitir um Relatório de Investigação Fiscal detalhado.\n\n"
                        "Foque em apontar e explicar riscos de: \n"
                        "1) Lançamentos Duplicados ou IDs idênticos com saídas iguais.\n"
