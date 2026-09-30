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

# Processamento da lista de arquivos de forma segura
if arquivos_upload and len(arquivos_upload) > 0:
    primeiro_arquivo = arquivos_upload[0] # Pega o primeiro item de forma segura para checar o tipo
    
    # CASO 1: PROCESSAMENTO DE ARQUIVO CSV (Balanço de Caixa)
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
if df is not None:
    # --- CONTROLE DE PLANO COMERCIAL ---
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

    # --- MOTOR FORENSE ULTRA-RÁPIDO (PANDAS LOCAL) ---
    df['Numero_NF'] = df['Numero_NF'].astype(str)
    df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str)
    df['Valor_Total'] = pd.to_numeric(df['Valor_Total'], errors='coerce').fillna(0.0)
    
    # 1. Cruzamento de Duplicidades (Mesmo ID e Valor)
    duplicadas = df[df.duplicated(subset=['Numero_NF', 'Valor_Total'], keep=False)]
    
    # 2. Análise Estatística de Superfaturamento (Acima de 2 Desvios Padrões e > R$ 5.000)
    media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
    desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
    superfaturadas = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)]
    
    # 3. Investigação de Notas Fantasmas (Inconsistências Cadastrais Críticas ou Valores Zerados)
    notas_fantasmas = df[(df['Valor_Total'] == 0) | (df['Numero_NF'] == 'N/A') | (df['Nome_Emitente'] == 'N/A') | (df['Nome_Emitente'].str.contains('Reembolso|Bônus', case=False, na=False))]

    # --- CÁLCULO DE RISCO FINANCEIRO (IMPACTO NO CAIXA) ---
    # Soma o valor total em risco para mostrar o prejuízo recuperável ao cliente
    valor_duplicado_risco = duplicadas['Valor_Total'].sum() / 2 # Divide por 2 pois aponta o valor pago duplicado em si
    valor_superfaturado_risco = superfaturadas['Valor_Total'].sum()
    valor_fantasma_risco = notas_fantasmas['Valor_Total'].sum()
    total_exposicao_financeira = valor_duplicado_risco + valor_superfaturado_risco + valor_fantasma_risco

    # --- NOVO PAINEL DE RESPOSTAS VISUAL E CONSULTIVO ---
    st.markdown("---")
    st.header("📊 Painel Pericial de Riscos e Compliance")
    st.markdown("Abaixo constam as inconformidades estruturais identificadas instantaneamente pelo motor analítico do **ScoutIA Fiscal**.")

    # 1. KPIs Executivos com Impacto Financeiro
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(label="🚨 Alertas de Risco Identificados", value=f"{len(duplicadas) + len(superfaturadas) + len(notas_fantasmas)} ocorrências")
    with col_kpi2:
        st.metric(label="💰 Exposição Financeira Total", value=f"R$ {total_exposicao_financeira:,.2f}", delta="Risco ao Caixa", delta_color="inverse")
    with col_kpi3:
        status_compliance = "CRÍTICO" if total_exposicao_financeira > 0 else "SAUDÁVEL"
        st.metric(label="🛡️ Status de Compliance Geral", value=status_compliance)

    # 2. Exibição Detalhada e Estratégica dos Riscos Encontrados
    
    # Caso A: Lançamentos Duplicados
    if not duplicadas.empty:
        st.markdown("### 🔴 1. Risco Crítico: Duplicação de Pagamentos e Notas")
        st.error(f"**Impacto Financeiro Estimado:** R$ {valor_duplicado_risco:,.2f} em pagamentos redundantes.")
        st.markdown("Foram detectadas transações repetidas contendo exatamente o mesmo número de identificação e valor financeiro. Este padrão indica falha grave de conciliação ou risco de duplo desembolso para o mesmo passivo.")
        st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Data_Emissao']], use_container_width=True)
        st.info("💡 **Ação Recomendada:** Reter imediatamente as ordens de pagamento deste lote e realizar o cruzamento direto com o extrato bancário para verificar se o desembolso duplo já ocorreu.")
    
    # Caso B: Superfaturamentos / Desvios Críticos
    if not superfaturadas.empty:
        st.markdown("### 🟡 2. Alerta de Desvio: Suspeitas de Superfaturamento de Gastos")
        st.warning(f"**Impacto Financeiro Estimado:** R$ {valor_superfaturado_risco:,.2f} fora do padrão operacional padrão.")
        st.markdown("Identificamos lançamentos cujo valor ultrapassa severamente o desvio padrão de gastos usual cadastrado para este tipo de despesa ou fornecedor. Pode indicar reajustes abusivos, erros de digitação ou superfaturamento de escopo.")
        st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Natureza_Operacao']], use_container_width=True)
        st.info("💡 **Ação Recomendada:** Solicitar o contrato de prestação de serviços ou o pedido de compras (Purchase Order) dessas transações para validar se o valor cobrado possui aprovação da diretoria.")

    # Caso C: Notas Fantasmas e Inconsistências de Auditoria
    if not notas_fantasmas.empty:
        st.markdown("### 🟤 3. Auditoria Cadastral: Lançamentos Anômalos ou Sem Lastro (Notas Fantasmas)")
        st.info(f"**Impacto Financeiro Estimado:** R$ {valor_fantasma_risco:,.2f} sob investigação cadastral.")
        st.markdown("Transações identificadas com preenchimento nulo, sem nome do emissor oficial, ou classificadas sob rúbricas de altíssimo risco regulatório (como bônus/reembolsos extraordinários sem identificação fiscal).")
        st.dataframe(notas_fantasmas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Natureza_Operacao' if 'Natureza_Operacao' in notas_fantasmas.columns else 'Valor_Total']], use_container_width=True)
        st.info("💡 **Ação Recomendada:** Realizar auditoria de rastreabilidade (Tracing) para identificar qual usuário originou este lançamento no ERP e exigir a nota fiscal física de suporte.")

    # Caso D: Tudo limpo e aprovado
    if duplicadas.empty and superfaturadas.empty and notas_fantasmas.empty:
        st.success("🎉 **Compliance Fiscal Aprovado!**")
        st.balloons()
        st.markdown("#### Parabéns! Nenhuma inconformidade foi localizada.")
        st.markdown("O motor analítico do **ScoutIA Fiscal** realizou a varredura completa nas matrizes de duplicidade, verificou as curvas de desvio padrão financeiro por fornecedor e checou o lastro cadastral de todos os registros. Os dados deste fechamento estão 100% saudáveis e prontos para o balanço final.")
