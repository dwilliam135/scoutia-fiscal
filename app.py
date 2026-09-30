import streamlit as st
import pandas as pd
import os
import xml.etree.ElementTree as ET

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

st.title("🛡️ ScoutIA Fiscal — Auditoria Sênior Contábil")
st.markdown("Auditoria instantânea de fechamentos, balanços financeiros (**CSV**) e **Notas Fiscais (XMLs)** rodando localmente.")

# --- BANCO DE DADOS DE LICENÇAS COMERCIAIS ---
BANCO_DE_LICENCAS = {
    "LICENCA-STARTER-100": {"plano": "Starter", "limite_linhas": 20, "preco": "R$ 2.490/mês"},
    "LICENCA-ENTERPRISE-500": {"plano": "Enterprise", "limite_linhas": 200, "preco": "R$ 7.990/mês"},
    "LICENCA-PRO-999": {"plano": "Pro Custom", "limite_linhas": float('inf'), "preco": "Sob Consulta"}
}

st.sidebar.subheader("🔑 Autenticação do Cliente")
licenca_usuario = st.sidebar.text_input("Insira sua Chave de Licença ScoutIA:", type="password").strip()

# Upload de arquivos (Configurado para aceitar múltiplos arquivos)
arquivos_upload = st.file_uploader("Escolha o relatório CSV ou selecione múltiplas Notas Fiscais XML", type=["csv", "xml"], accept_multiple_files=True)

df = None
nome_arquivo_log = ""

# Processamento seguro da lista de uploads
if arquivos_upload and len(arquivos_upload) > 0:
    primeiro_arquivo = arquivos_upload[0] # Acessa o primeiro item indexado da lista
    
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
                
            st.success(f"Relatório CSV '{nome_arquivo_log}' carregado! ({len(df)} registros)")
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
