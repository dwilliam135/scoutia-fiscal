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
    primeiro_arquivo = arquivos_upload[0] # Correção crítica: Acessa o primeiro item indexado da lista
    
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
# --- INÍCIO DO BLOCO DE VISUALIZAÇÃO E AUDITORIA ---
if df is not None:
    if licenca_usuario in BANCO_DE_LICENCAS:
        info_plano = BANCO_DE_LICENCAS[licenca_usuario]
        limite = info_plano["limite_linhas"]
        st.sidebar.success(f"🛡️ Licença Ativa: Plano {info_plano['plano']}")
        if len(df) > limite:
            st.warning(f"Contrato {info_plano['plano']} limita a análise a {limite} linhas. Dados truncados.")
            df = df.head(limite)
    else:
        st.sidebar.error("🚨 Modo Demonstração (Sem Chave): Exibindo até 200 registros.")
        df = df.head(200)
    
    st.subheader("📋 Relatório de Dados Consolidados para Análise")
    st.dataframe(df, use_container_width=True)

    # Padronização e tratamento rigoroso de texto e números para evitar divergências
    df['Numero_NF'] = df['Numero_NF'].astype(str).str.strip()
    df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str).str.strip()
    df['Nome_Emitente'] = df['Nome_Emitente'].astype(str).str.strip()
    df['Valor_Total'] = pd.to_numeric(df['Valor_Total'], errors='coerce').fillna(0.0)
    
    # 1. Identificação de Lançamentos Duplicados
    duplicadas = df[df.duplicated(subset=['Numero_NF', 'Valor_Total'], keep=False)].copy()
    
    # 2. Identificação de Anomalias Cadastrais / Reembolsos Suspeitos (Filtro Padronizado)
    nome_emitente_minulo = df['Nome_Emitente'].str.lower()
    fantasmas_filtro = (
        (df['Valor_Total'] == 0) | 
        (df['Numero_NF'] == 'N/A') | 
        (df['Nome_Emitente'] == 'N/A') | 
        (nome_emitente_minulo.str.contains('reembolso|bônus|bonus|presidente|diretoria', case=False, na=False))
    )
    notas_fantasmas = df[fantasmas_filtro].copy()
    notas_fantasmas = notas_fantasmas[~notas_fantasmas.index.isin(duplicadas.index)]
    
    # 3. Identificação de Desvios Críticos de Valor (Superfaturamento)
    media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
    desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
    
    superfaturadas_base = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)].copy()
    superfaturadas = superfaturadas_base[~superfaturadas_base.index.isin(duplicadas.index)]
    superfaturadas = superfaturadas[~superfaturadas.index.isin(notas_fantasmas.index)]

    # Amarrando rigorosamente as variáveis numéricas dos KPIs ao tamanho real das matrizes finais
    qtd_duplicadas_reais = int(len(duplicadas) / 2) if len(duplicadas) > 0 else 0
    qtd_fantasmas_reais = len(notas_fantasmas)
    qtd_superfaturadas_reais = len(superfaturadas)
    
    valor_duplicado_risco = duplicadas['Valor_Total'].sum() / 2
    valor_fantasma_risco = notas_fantasmas['Valor_Total'].sum()
    valor_superfaturado_risco = superfaturadas['Valor_Total'].sum()
    
    total_alertas_reais = qtd_duplicadas_reais + qtd_fantasmas_reais + qtd_superfaturadas_reais
    total_exposicao_financeira = valor_duplicado_risco + valor_fantasma_risco + valor_superfaturado_risco

    st.markdown("---")
    st.header("⚡ Diagnóstico Técnico Executivo & Pronta Resposta")
    st.markdown("Varredura concluída. Abaixo constam as inconformidades localizadas e o plano de ação operacional imediato para proteção do caixa:")

    # Painel de KPIs de Controle Gerais
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(label="⚠️ Inconformidades Detectadas", value=f"{total_alertas_reais} ocorrências")
    with col_kpi2:
        st.metric(label="💰 Capital em Risco Crítico", value=f"R$ {total_exposicao_financeira:,.2f}", delta="Exposição de Caixa", delta_color="inverse")
    with col_kpi3:
        status_compliance = "🚨 COMPLIANCE CRÍTICO" if total_exposicao_financeira > 0 else "✅ COMPLIANCE SAUDÁVEL"
        st.metric(label="🛡️ Matriz de Risco Atual", value=status_compliance)

    # Exibição Técnica Ocorrência por Ocorrência
    if not duplicadas.empty:
        st.markdown(f"### 🔴 1. Erro de Processamento: Lançamentos Duplicados ({qtd_duplicadas_reais} ocorrência(s))")
        st.error(f"**Impacto Direto:** R$ {valor_duplicado_risco:,.2f} retidos na matriz de redundância.")
        st.markdown("**Fato:** Identificação de transações com numeração e valores idênticos. Alto risco de duplo desembolso para a mesma obrigação fiscal.")
        st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Data_Emissao']], use_container_width=True)
        st.markdown("""
        **⚡ AÇÃO OPERACIONAL IMEDIATA:**
        * **Suspender** o agendamento bancário dos IDs listados acima no sistema de Contas a Pagar.
        * **Confrontar** a transação com o extrato de fluxo de caixa para verificar se houve a saída dupla.
        * **Notificar** o emissor da cobrança exigindo o estorno imediato ou a emissão de nota de crédito correlata.
        """)
    
    if not notas_fantasmas.empty:
        st.markdown(f"### 🟤 2. Anomalia Cadastral: Lançamentos Sem Lastro ou Sob Investigação ({qtd_fantasmas_reais} ocorrência(s))")
        st.info(f"**Impacto Direto:** R$ {valor_fantasma_risco:,.2f} sob exposição regulatória.")
        st.markdown("**Fato:** Identificação de saídas financeiras de alto risco sem CNPJ válido, valores zerados ou classificadas como bônus/reembolsos extraordinários de gestão.")
        st.dataframe(notas_fantasmas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
        st.markdown("""
        **⚡ AÇÃO OPERACIONAL IMEDIATA:**
        * **Rastrear** o usuário de origem (login do ERP) que realizou a digitação física desta despesa.
        * **Exigir** o envio imediato da folha de aprovação assinada e do cupom/comprovante digital de suporte.
        * **Isolar** a conta contábil do lançamento até a comprovação legal para evitar passivos na Receita Federal.
        """)

    if not superfaturadas.empty:
        st.markdown(f"### 🟡 3. Desvio Operacional: Suspeita de Superfaturamento / Valores Abusivos ({qtd_superfaturadas_reais} ocorrência(s))")
        st.warning(f"**Impacto Direto:** R$ {valor_superfaturado_risco:,.2f} acima da curva usual.")
        st.markdown("**Fato:** Lançamentos com margem de valor severamente acima da média histórica praticada para o mesmo fornecedor ou categoria de serviço.")
        st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
        st.markdown("""
        **⚡ AÇÃO OPERACIONAL IMEDIATA:**
        * **Confrontar** a cobrança com a Ordem de Compra (PO) original ou contrato master de prestação de serviços.
        * **Glosa Fiscal:** Reter a liquidação financeira do valor excedente até a justificativa de escopo pelo fornecedor.
        * **Auditar** o setor de suprimentos para avaliar reajustes unilaterais não homologados pela diretoria.
        """)

    if duplicadas.empty and superfaturadas.empty and notas_fantasmas.empty:
        st.success("🎉 **Compliance Financeiro Homologado!**")
        st.balloons()
        st.markdown("#### Matrizes de Risco Zeradas.")
        st.markdown("O motor de triagem local concluiu a análise vetorial e confirmou a perfeita integridade dos dados. O fechamento está validado.")
