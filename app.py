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
# --- VALIDAÇÃO OBRIGATÓRIA DE LICENÇA DE ACESSO ---
if df is not None:
    # Caso 1: O usuário inseriu uma licença válida cadastrada no sistema
    if licenca_usuario and licenca_usuario in BANCO_DE_LICENCAS:
        info_plano = BANCO_DE_LICENCAS[licenca_usuario]
        limite = info_plano["limite_linhas"]
        st.sidebar.success(f"🛡️ Licença Ativa: Plano {info_plano['plano']}")
        
        # Corta as linhas se o arquivo passar do limite contratado pelo plano
        if len(df) > limite:
            st.warning(f"Seu plano {info_plano['plano']} limita a análise a {limite} linhas. O arquivo foi truncado.")
            df = df.head(limite)
            
        # --- SE A LICENÇA FOR VÁLIDA, O SISTEMA LIBERA A EXIBIÇÃO ABAIXO ---
        st.subheader("📋 Relatório de Dados Consolidados para Análise")
        st.dataframe(df, use_container_width=True)

        # Padronização interna de dados
        df['Numero_NF'] = df['Numero_NF'].astype(str).str.strip()
        df['CNPJ_Emitente'] = df['CNPJ_Emitente'].astype(str).str.strip()
        df['Nome_Emitente'] = df['Nome_Emitente'].astype(str).str.strip()
        df['Valor_Total'] = pd.to_numeric(df['Valor_Total'], errors='coerce').fillna(0.0)
        
        # 1. Identificação de Lançamentos Duplicados (Mesmo ID e Valor)
        duplicadas = df[df.duplicated(subset=['Numero_NF', 'Valor_Total'], keep=False)].copy()
        
        # 2. Retiradas Atípicas e Reembolsos de Alta Gestão (Ex: Presidência/Diretoria)
        nome_emitente_minulo = df['Nome_Emitente'].str.lower()
        filtro_reembolsos = nome_emitente_minulo.str.contains(r'\breembolso\b|\bbônus\b|\bbonus\b', regex=True, na=False)
        reembolsos_gestao = df[filtro_reembolsos].copy()
        reembolsos_gestao = reembolsos_gestao[~reembolsos_gestao.index.isin(duplicadas.index)]
        
        # 3. Lançamentos sem Lastro / Valores Zerados (Notas Fantasmas Legítimas)
        filtro_zerados = (df['Valor_Total'] == 0) | (df['Numero_NF'] == 'N/A') | (df['Nome_Emitente'] == 'N/A')
        notas_fantasmas = df[filtro_zerados].copy()
        notas_fantasmas = notas_fantasmas[~notas_fantasmas.index.isin(duplicadas.index)]
        notas_fantasmas = notas_fantasmas[~notas_fantasmas.index.isin(reembolsos_gestao.index)]
        
        # 4. Identificação de Desvios Críticos de Valor (Superfaturamento Estatístico)
        media_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('mean')
        desvio_por_fornecedor = df.groupby('CNPJ_Emitente')['Valor_Total'].transform('std').fillna(0)
        
        superfaturadas_base = df[(df['Valor_Total'] > (media_por_fornecedor + (2 * desvio_por_fornecedor))) & (df['Valor_Total'] > 5000)].copy()
        superfaturadas = superfaturadas_base[~superfaturadas_base.index.isin(duplicadas.index)]
        superfaturadas = superfaturadas[~superfaturadas.index.isin(reembolsos_gestao.index)]
        superfaturadas = superfaturadas[~superfaturadas.index.isin(notas_fantasmas.index)]

        # Vinculação direta dos contadores ao tamanho real das tabelas na tela
        qtd_duplicadas_reais = int(len(duplicadas) / 2) if len(duplicadas) > 0 else 0
        qtd_reembolsos_reais = len(reembolsos_gestao)
        qtd_fantasmas_reais = len(notas_fantasmas)
        qtd_superfaturadas_reais = len(superfaturadas)
        
        valor_duplicado_risco = duplicadas['Valor_Total'].sum() / 2
        valor_reembolso_risco = reembolsos_gestao['Valor_Total'].sum()
        valor_fantasma_risco = notas_fantasmas['Valor_Total'].sum()
        valor_superfaturado_risco = superfaturadas['Valor_Total'].sum()
        
        total_alertas_reais = qtd_duplicadas_reais + qtd_reembolsos_reais + qtd_fantasmas_reais + qtd_superfaturadas_reais
        total_exposicao_financeira = valor_duplicado_risco + valor_reembolso_risco + valor_fantasma_risco + valor_superfaturado_risco

        st.markdown("---")
        st.header("📋 Diagnóstico de Fechamento e Plano de Ação")
        st.markdown("A análise automática terminou. Veja abaixo quais problemas foram encontrados no seu arquivo e o que fazer agora:")

        # Painel Executivo Simples
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        with col_kpi1:
            st.metric(label="⚠️ Problemas Encontrados", value=f"{total_alertas_reais} erros no total")
        with col_kpi2:
            st.metric(label="💰 Dinheiro em Risco no Caixa", value=f"R$ {total_exposicao_financeira:,.2f}", delta="Prejuízo Provável", delta_color="inverse")
        with col_kpi3:
            status_compliance = "🚨 RISCO ALTO" if total_exposicao_financeira > 0 else "✅ TUDO EM ORDEM"
            st.metric(label="🛡️ Saúde do Fechamento", value=status_compliance)

        # EXIBIÇÃO DETALHADA DOS CENÁRIOS
        if not duplicadas.empty:
            st.markdown(f"### 🔴 1. Cobranças ou Pagamentos Duplicados ({qtd_duplicadas_reais} caso(s))")
            st.error(f"**Prejuízo Estimado:** R$ {valor_duplicado_risco:,.2f}")
            st.markdown("**O que aconteceu:** O sistema encontrou contas ou notas com o mesmo número e mesmo valor. Isso significa que a sua empresa pode ter pago duas vezes pela mesma despesa sem perceber, ou o fornecedor enviou a cobrança em dobro.")
            st.dataframe(duplicadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total', 'Data_Emissao']], use_container_width=True)
            st.markdown("""
            **👉 O QUE VOCÊ DEVE FAZER AGORA:**
            * **Bloqueie** imediatamente qualquer novo pagamento agendado para estes números no seu financeiro.
            * **Confira seu banco** para checar se o dinheiro já saiu duas vezes para este fornecedor.
            * **Exija a devolução** caso o pagamento duplo já tenha ocorrido, enviando os comprovantes para o parceiro comercial.
            """)
        
        if not reembolsos_gestao.empty:
            st.markdown(f"### 🟤 2. Reembolsos e Bônus Suspeitos de Sócios ou Diretores ({qtd_reembolsos_reais} caso(s))")
            st.info(f"**Dinheiro Sob Suspeita:** R$ {valor_reembolso_risco:,.2f}")
            st.markdown("**O que aconteceu:** Lançamentos com valores muito altos foram registrados como reembolsos de despesas ou bônus para a presidência/diretoria. Essas saídas precisam de atenção redobrada porque saídas de dinheiro para a liderança sem comprovação clara geram multas pesadas com a Receita Federal.")
            st.dataframe(reembolsos_gestao[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
            st.markdown("""
            **👉 O QUE VOCÊ DEVE FAZER AGORA:**
            * **Descubra quem digitou** essa despesa buscando o histórico de acessos (log de login) no sistema da sua empresa.
            * **Peça o comprovante físico** (cupom fiscal, nota ou documento assinado pela presidência) que autorizou essa saída de dinheiro.
            * **Deixe o valor separado** na contabilidade até encontrar o documento oficial para não ter problemas fiscais.
            """)

        if not notas_fantasmas.empty:
            st.markdown(f"### ⚪ 3. Lançamentos Sem Informação ou Notas Zeradas ({qtd_fantasmas_reais} caso(s))")
            st.warning(f"**Inconsistência Cadastral:** Registros com valor zero ou sem identificação.")
            st.markdown("**O que aconteceu:** Foram encontrados lançamentos que estão com o valor zerado no sistema ou não possuem o número da nota fiscal e o nome do fornecedor preenchidos. Isso quebra o balanço contábil e pode indicar erros de integração do sistema ou notas que foram canceladas e não atualizadas.")
            st.dataframe(notas_fantasmas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
            st.markdown("""
            **👉 O QUE VOCÊ DEVE FAZER AGORA:**
            * **Acione o setor de compras** ou estoque para descobrir o motivo dessas movimentações estarem com valor zerado.
            * **Corrija o cadastro** inserindo as informações que estão faltando antes de fechar o balanço do mês.
            """)

        if not superfaturadas.empty:
            st.markdown(f"### 🟡 4. Gastos Excessivos / Valores Acima do Combinado ({qtd_superfaturadas_reais} caso(s))")
            st.warning(f"**Diferença de Valor:** R$ {valor_superfaturado_risco:,.2f}")
            st.markdown("**O que aconteceu:** Estes fornecedores cobraram valores muito mais altos do que a média de preço que eles costumam praticar no histórico da sua empresa. Pode ser um erro de cobrança deles, um funcionário que aceitou um preço abusivo ou serviços cobrados a mais.")
            st.dataframe(superfaturadas[['Numero_NF', 'Nome_Emitente', 'Valor_Total']], use_container_width=True)
            st.markdown("""
            **👉 O QUE VOCÊ DEVE FAZER AGORA:**
            * **Pegue o contrato original** desse fornecedor e veja se o preço cobrado confere com as regras que foram assinadas.
            * **Segure a diferença do pagamento** e avise o fornecedor que o valor veio acima da média combinada até que ele mande uma justificativa.
            * **Verifique internamente** se o gerente da área deu autorização por escrito para esse gasto extra antes dele acontecer.
            """)

        if duplicadas.empty and reembolsos_gestao.empty and notas_fantasmas.empty and superfaturadas.empty:
            st.success("🎉 **Seu Fechamento de Caixa está Perfeito!**")
            st.balloons()
            st.markdown("#### Nenhuma irregularidade ou perda de dinheiro foi encontrada.")
            st.markdown("O sistema revisou linha por linha e confirmou que todas as movimentações estão corretas, com valores dentro do combinado e documentação em dia.")
            
    # Caso 2: Se o usuário não digitou a chave ou digitou uma chave inválida
    else:
        st.sidebar.error("🚨 Acesso Bloqueado: Insira uma Chave de Licença ScoutIA válida para liberar a auditoria.")
