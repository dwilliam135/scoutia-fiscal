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
st.markdown("Suba seus relatórios financeiros ou múltiplos XMLs para identificar **notas duplicadas, superfaturamento e notas fantasmas**.")

# --- BANCO DE DADOS DE LICENÇAS COMERCIAIS ---
BANCO_DE_LICENCAS = {
    "LICENCA-STARTER-100": {"plano": "Starter", "limite_linhas": 20, "preco": "R$ 2.490/mês"},
    "LICENCA-ENTERPRISE-500": {"plano": "Enterprise", "limite_linhas": 200, "preco": "R$ 7.990/mês"},
    "LICENCA-PRO-999": {"plano": "Pro Custom", "limite_linhas": float('inf'), "preco": "Sob Consulta"}
}

st.sidebar.subheader("🔑 Autenticação do Cliente")
licenca_usuario = st.sidebar.text_input("Insira sua Chave de Licença ScoutIA:", type="password").strip()

# Inicialização do Cliente Gemini
CHAVE_INTERNA_IA = os.environ.get("GEMINI_API_KEY", "")
if not CHAVE_INTERNA_IA:
    CHAVE_INTERNA_IA = "SUA_GEMINI_API_KEY_AQUI" 

client = None
if CHAVE_INTERNA_IA and CHAVE_INTERNA_IA != "SUA_GEMINI_API_KEY_AQUI":
    client = genai.Client(api_key=CHAVE_INTERNA_IA)

WEBHOOK_MONITORAMENTO = "https://google.com"

# Upload de arquivos
arquivos_upload = st.file_uploader("Escolha os relatórios CSV ou selecione múltiplas Notas Fiscais XML", type=["csv", "xml"], accept_multiple_files=True)

df = None
nome_arquivo_log = ""

if arquivos_upload and len(arquivos_upload) > 0:
    dados_processados = []
    
    # Se for um arquivo CSV único (relatório de fechamento)
    if arquivos_upload[0].name.endswith('.csv'):
        try:
            df = pd.read_csv(arquivos_upload[0])
            nome_arquivo_log = arquivos_upload[0].name
            st.success(f"Relatório CSV '{nome_arquivo_log}' carregado. ({len(df)} registros)")
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV: {str(e)}")
            
    # Se forem múltiplos XMLs de Notas Fiscais
    else:
        st.info(f"Processando {len(arquivos_upload)} arquivos XML...")
        for arquivo in arquivos_upload:
            if arquivo.name.endswith('.xml'):
                try:
                    tree = ET.parse(arquivo)
                    root = tree.getroot()
                    ns = {'ns': 'http://portalfiscal.inf.br'}
                    
                    ide = root.find('.//ns:ide', ns)
                    emit = root.find('.//ns:emit', ns)
                    dest = root.find('.//ns:dest', ns)
                    total = root.find('.//ns:total/ns:ICMSTot', ns)
                    
                    # Captura de chaves essenciais para cruzamento antifraude
                    dados_nota = {
                        "Chave_Acesso": root.find('.//ns:infNfe', ns).attrib.get('Id', '')[3:] if root.find('.//ns:infNfe', ns) is not None else "N/A",
                        "Numero_NF": ide.find('ns:nNF', ns).text if ide is not None and ide.find('ns:nNF', ns) is not None else "N/A",
                        "Data_Emissao": ide.find('ns:dhEmi', ns).text[:10] if ide is not None and ide.find('ns:dhEmi', ns) is not None else "N/A",
                        "CNPJ_Emitente": emit.find('ns:CNPJ', ns).text if emit is not None and emit.find('ns:CNPJ', ns) is not None else "N/A",
                        "Nome_Emitente": emit.find('ns:xNome', ns).text if emit is not None and emit.find('ns:xNome', ns) is not None else "N/A",
                        "CNPJ_Destinatario": dest.find('ns:CNPJ', ns).text if dest is not None and dest.find('ns:CNPJ', ns) is not None else "N/A",
                        "Valor_Total": float(total.find('ns:vNF', ns).text) if total is not None and total.find('ns:vNF', ns) is not None else 0.0,
                        "Natureza_Operacao": ide.find('ns:natOp', ns).text if ide is not None and ide.find('ns:natOp', ns) is not None else "N/A"
                    }
                    dados_processados.append(dados_nota)
                except Exception as e:
                    st.warning(f"Erro ao processar o XML {arquivo.name}: {str(e)}")
        
        if dados_processados:
            df = pd.DataFrame(dados_processados)
            nome_arquivo_log = f"Lote_XML_{len(dados_processados)}_notas.csv"
            st.success(f"{len(df)} Notas Fiscais consolidadas com sucesso!")

# APLICAÇÃO DAS REGRAS DE AUDITORIA
if df is not None:
    # Ajuste de limite por plano comercial
    if licenca_usuario in BANCO_DE_LICENCAS:
        info_plano = BANCO_DE_LICENCAS[licenca_usuario]
        limite = info_plano["limite_linhas"]
        if len(df) > limite:
            st.warning(f"Contrato {info_plano['plano']} limita a análise a {limite} linhas. Dados truncados.")
            df = df.head(limite)
    else:
        st.sidebar.error("Modo Demonstração: Limitado a 10 registros.")
        df = df.head(10)
    
    st.subheader("📋 Painel de Dados Consolidados")
    st.dataframe(df)

    # --- MOTOR DE PRÉ-AUDITORIA DETECTIVA (PANDAS) ---
    st.subheader("🔍 Triagem Automatizada de Riscos")
    
    # 1. Detecção de Notas Duplicadas (Mesmo Emitente, Número e Valor)
    # Garante a conversão correta para evitar erros de tipo
    df['Numero_NF'] = df['Numero_NF'].astype(str)
    df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str)
    
    duplicadas = df[df.duplicated(subset=['Numero_NF', 'CNPJ_Emitente', 'Valor_Total'], keep=False)]
    
    # 2. Desvios e Possível Superfaturamento (Notas com valores muito acima da média do mesmo fornecedor)
    media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
    desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
    # Alerta se o valor for maior que a média + 2 desvios padrões (regra estatística clássica)
    superfaturadas = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)]

    # Exibição dos alertas na tela para o auditor humano
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Suspeitas de Duplicidade", len(duplicadas))
        if not duplicadas.empty:
            st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']])
            
    with col2:
        st.metric("Suspeitas de Superfaturamento", len(superfaturadas))
        if not superfaturadas.empty:
            st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']])

    # --- DISPARO DA INTELIGÊNCIA ARTIFICIAL ---
    if st.button("🛡️ Gerar Parecer Antifraude com ScoutIA"):
        if not client:
            st.error("Erro: API Key do Gemini não configurada.")
        else:
            with st.spinner("A IA está cruzando os indícios e redigindo o parecer técnico..."):
                try:
                    # Criamos um resumo estruturado para enviar para a IA. 
                    # Isso evita enviar milhares de linhas cruas e foca apenas no que importa.
                    resumo_auditoria = {
                        "total_registros_analisados": len(df),
                        "total_valor_movimentado": float(df['Valor_Total'].sum()),
                        "casos_duplicidade_detectados": duplicadas.to_dict(orient='records'),
                        "casos_desvio_valor_detectados": superfaturadas.to_dict(orient='records'),
                        "principais_fornecedores": df.groupby('Nome_Emitente')['Valor_Total'].sum().nlargest(5).to_dict()
                    }
                    
                    prompt_sistema = (
                        "Você é um Perito Forense Digital e Auditor Fiscal Sênior especializado em Compliance e Prevenção a Fraudes. "
                        "Analise o resumo dos dados de fechamento fornecidos. Seu papel é emitir um Relatório de Investigação Fiscal detalhado. "
                        "Foque em apontar riscos de: \n"
                        "1) Notas Fiscais Duplicadas (fraude de duplo pagamento).\n"
                        "2) Notas com indícios de Superfaturamento (valores discrepantes para o mesmo fornecedor).\n"
                        "3) Risco de Notas Fantasmas (ex: volumes financeiros incompatíveis, fornecedores desconhecidos concentrando muito valor).\n\n"
                        "Seja extremamente formal, contundente e aponte recomendações de auditoria interna para cada inconsistência."
                    )
                    
                    resposta = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"Dados consolidados da pré-triagem:\n\n{str(resumo_auditoria)}",
                        config=types.GenerateContentConfig(
                            system_instruction=prompt_sistema,
                            temperature=0.1 # Resposta puramente factual e analítica
                        )
                    )
                    
                    st.subheader("🛡️ Relatório Pericial Forense (ScoutIA)")
                    st.markdown(resposta.text)
                    
                except Exception as e:
                    st.error(f"Erro na comunicação com o cérebro da IA: {str(e)}")
