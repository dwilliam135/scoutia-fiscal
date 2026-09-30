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

    # --- MOTOR DE AUDITORIA INTERNA (PANDAS LOCAL) ---
    df['Numero_NF'] = df['Numero_NF'].astype(str)
    df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str)
    df['Valor_Total'] = pd.to_numeric(df['Valor_Total'], errors='coerce').fillna(0.0)
    
    # 1. Identificação de Contas/Notas Duplicadas
    duplicadas = df[df.duplicated(subset=['Numero_NF', 'Valor_Total'], keep=False)]
    
    # 2. Identificação de Gastos Fora do Comum (Superfaturamento)
    media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
    desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
    superfaturadas = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)]
    
    # CORREÇÃO DA CONTAGEM: Garante que os alertas de superfaturamento não se sobreponham a notas fantasmas
    superfaturadas = superfaturadas.drop(duplicadas.index, errors='ignore')
    
    # 3. Identificação de Notas Suspeitas / Sem Informação (Notas Fantasmas)
    notas_fantasmas = df[(df['Valor_Total'] == 0) | (df['Numero_NF'] == 'N/A') | (df['Nome_Emitente'] == 'N/A') | (df['Nome_Emitente'].str.contains('Reembolso|Bônus', case=False, na=False))]
    notas_fantasmas = notas_fantasmas.drop(duplicadas.index, errors='ignore')

    # --- CÁLCULO DE IMPACTO FINANCEIRO ---
    # Divide por 2 as duplicadas porque o sistema aponta os dois lançamentos parados na tabela
    qtd_duplicadas_reais = int(len(duplicadas) / 2) if len(duplicadas) > 0 else 0
    valor_duplicado_risco = duplicadas['Valor_Total'].sum() / 2
    
    qtd_superfaturadas_reais = len(superfaturadas)
    valor_superfaturado_risco = superfaturadas['Valor_Total'].sum()
    
    qtd_fantasmas_reais = len(notas_fantasmas)
    valor_fantasma_risco = notas_fantasmas['Valor_Total'].sum()
    
    # Totalizadores exatos para os cartões do topo
    total_alertas_reais = qtd_duplicadas_reais + qtd_superfaturadas_reais + qtd_fantasmas_reais
    total_exposicao_financeira = valor_duplicado_risco + valor_superfaturado_risco + valor_fantasma_risco

    # --- PAINEL DE RESPOSTAS SIMPLIFICADO E DIRECIONADO AO CLIENTE ---
    st.markdown("---")
    st.header("📊 Diagnóstico Financeiro e Direcionamento de Caixa")
    st.markdown("O sistema realizou a varredura automática dos seus dados. Veja abaixo os pontos de atenção encontrados e o que fazer com cada um deles:")

    # 1. Painel Executivo com Linguagem Clara
    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    with col_kpi1:
        st.metric(label="⚠️ Problemas Encontrados", value=f"{total_alertas_reais} erros no total")
    with col_kpi2:
        st.metric(label="💰 Dinheiro em Risco no Caixa", value=f"R$ {total_exposicao_financeira:,.2f}", delta="Prejuízo Provável", delta_color="inverse")
    with col_kpi3:
        status_compliance = "🚨 RISCO ALTO" if total_exposicao_financeira > 0 else "✅ TUDO CERTO"
        st.metric(label="🛡️ Situação Atual da Empresa", value=status_compliance)

    # 2. Explicação Prática e Caminho das Pedras para o Cliente
    
    # Cenário 1: Pagamentos Duplicados
    if not duplicadas.empty:
        st.markdown(f"### 🔴 Cobranças ou Pagamentos Duplicados ({qtd_duplicadas_reais} caso(s) encontrado(s))")
        st.error(f"**Prejuízo no Caixa:** R$ {valor_duplicado_risco:,.2f}")
        st.markdown(
            "**O que aconteceu:** O sistema encontrou contas ou notas com o mesmo número e mesmo valor. "
            "Isso significa que a sua empresa pode ter pago duas vezes pela mesma coisa sem perceber, ou o fornecedor enviou a cobrança em dobro."
        )
        st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Data_Emissao']], use_container_width=True)
        
        # O CAMINHO PARA O CLIENTE SEGUIR:
        st.markdown("""
        **🧭 Como resolver este problema (Passo a Passo):**
        1. **Bloqueio Imediato:** Entre em contato com o setor de Contas a Pagar e mande suspender qualquer pagamento agendado para esses números.
        2. **Conferência Bancária:** Abra o extrato do seu banco e verifique se o dinheiro já saiu duas vezes.
        3. **Estorno:** Caso o pagamento duplo tenha acontecido, envie o comprovante ao fornecedor e exija a devolução do dinheiro ou um crédito na próxima compra.
        """)
    
    # Cenário 2: Gastos Suspeitos / Valores Muito Altos (Superfaturamento)
    if not superfaturadas.empty:
        st.markdown(f"### 🟡 Gastos Acima do Normal / Suspeita de Valores Excessivos ({qtd_superfaturadas_reais} caso(s) encontrado(s))")
        st.warning(f"**Prejuízo no Caixa:** R$ {valor_superfaturado_risco:,.2f}")
        st.markdown(
            "**O que aconteceu:** Estes fornecedores cobraram valores muito mais altos do que o combinado ou do que eles costumam cobrar normalmente. "
            "Isso pode indicar um erro de digitação do funcionário, um reajuste de preço abusivo do fornecedor ou cobrança por serviços não realizados."
        )
        st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Natureza_Operacao']], use_container_width=True)
        
        # O CAMINHO PARA O CLIENTE SEGUIR:
        st.markdown("""
        **🧭 Como resolver este problema (Passo a Passo):**
        1. **Auditoria de Contrato:** Pegue o contrato assinado com esse fornecedor e veja se o preço bate com o que está na tabela acima.
        2. **Cobrar Justificativa:** Ligue para o fornecedor e pergunte por que o valor dessa transação veio tão acima da média usual.
        3. **Aprovação Interna:** Verifique com o gerente da área se ele autorizou esse gasto extra por escrito antes da compra ser feita.
        """)

    # Cenário 3: Notas sem Identificação / Gastos Estranhos (Notas Fantasmas)
    if not notas_fantasmas.empty:
        st.markdown(f"### 🟤 Lançamentos Sem Comprovação ou Sem Nome ({qtd_fantasmas_reais} caso(s) encontrado(s))")
        st.info(f"**Prejuízo no Caixa:** R$ {valor_fantasma_risco:,.2f}")
        st.markdown(
            "**O que aconteceu:** Foram encontrados lançamentos com valores zerados, sem o nome do fornecedor ou marcados como 'Reembolso/Bônus' sem nenhuma nota fiscal anexada. "
            "Isso é perigoso porque a empresa pode estar gastando dinheiro com saídas falsas ou sem comprovação para a Receita Federal."
        )
        st.dataframe(notas_fantasmas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
        
        # O CAMINHO PARA O CLIENTE SEGUIR:
        st.markdown("""
        **🧭 Como resolver este problema (Passo a Passo):**
        1. **Rastrear o Funcionário:** Descubra no seu sistema financeiro quem foi o funcionário que registrou essa transação.
        2. **Exigir o Documento:** Dê um prazo para o responsável apresentar o cupom fiscal ou a nota fiscal física que comprove o gasto.
        3. **Correção Fiscal:** Caso a nota não exista, converse com o seu contador para estornar ou corrigir o lançamento para evitar multas pesadas do governo.
        """)

    # Cenário 4: Tudo perfeito
    if duplicadas.empty and superfaturadas.empty and notas_fantasmas.empty:
        st.success("🎉 **Seu Fechamento de Caixa está Perfeito!**")
        st.balloons()
        st.markdown("#### Nenhuma irregularidade ou perda de dinheiro foi encontrada.")
        st.markdown(
            "O sistema revisou linha por linha e confirmou que não existem contas pagas em dobro, "
            "todos os valores cobrados estão dentro do combinado com os fornecedores e não há nenhum lançamento suspeito sem documento. "
            "Seu balanço financeiro está totalmente seguro e pronto para ser fechado."
        )
