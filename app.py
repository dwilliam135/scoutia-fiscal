import streamlit as st
import pandas as pd
import os
import time
import random
import requests
import xml.etree.ElementTree as ET
from google import genai

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

st.title("🛡️ ScoutIA Fiscal — Auditoria Sênior & Compliance")
st.markdown("Suba seus relatórios financeiros (**CSV**) ou suas **Notas Fiscais (múltiplos XMLs)** para auditoria instantânea por Inteligência Artificial.")

# --- BANCO DE DADOS DE LICENÇAS COMERCIAIS ---
BANCO_DE_LICENCAS = {
    "LICENCA-STARTER-100": {"plano": "Starter", "limite_linhas": 20, "preco": "R$ 2.490/mês"},
    "LICENCA-ENTERPRISE-500": {"plano": "Enterprise", "limite_linhas": 200, "preco": "R$ 7.990/mês"},
    "LICENCA-PRO-999": {"plano": "Pro Custom", "limite_linhas": float('inf'), "preco": "Sob Consulta"}
}

st.sidebar.subheader("🔑 Autenticação do Cliente")
licenca_usuario = st.sidebar.text_input("Insira sua Chave de Licença ScoutIA:", type="password").strip()

CHAVE_INTERNA_IA = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6ITcrnd309KcEI_WnR8CQVamYFP6lE2lefUDPcVVYDtJQ")
WEBHOOK_MONITORAMENTO = "https://google.com"

# 📥 NOVO SISTEMA DE ARQUIVOS HYBRIDO (Aceita CSV ou múltiplos XMLs)
arquivos_upload = st.file_uploader("Escolha os relatórios CSV ou selecione múltiplas Notas Fiscais XML", type=["csv", "xml"], accept_multiple_files=True)

df = None
nome_arquivo_log = ""

if arquivos_upload:
    dados_processados = []
    
    # Caso 1: O usuário subiu um ou mais arquivos CSV
    if arquivos_upload[0].name.endswith('.csv'):
        # Pegamos o primeiro CSV para processamento
        arquivo = arquivos_upload[0]
        try:
            df = pd.read_csv(arquivo)
            nome_arquivo_log = arquivo.name
        except Exception as e:
            st.error(f"Erro ao ler o arquivo CSV: {str(e)}")
            
    # Caso 2: O usuário subiu uma pilha de arquivos XML de notas fiscais
    elif arquivos_upload[0].name.endswith('.xml'):
        nome_arquivo_log = f"{len(arquivos_upload)} Notas Fiscais XML"
        
        with st.spinner("Extraindo e estruturando dados dos XMLs..."):
            for arquivo in arquivos_upload:
                try:
                    # Ler o conteúdo do XML direto da memória do upload
                    conteudo_xml = arquivo.read()
                    root = ET.fromstring(conteudo_xml)
                    
                    # Remover namespaces padrões do XML da receita (NF-e) para facilitar a busca
                    for elem in root.iter():
                        if '}' in elem.tag:
                            elem.tag = elem.tag.split('}', 1)[1]
                            
                    # Extração cirúrgica dos dados baseados na estrutura oficial da NF-e
                    # Se não achar a tag específica (NFe), tenta ler formatos genéricos de recibos
                    id_nota = root.find('.//chNFe')
                    id_nota = id_nota.text if id_nota is not None else root.find('.//nNF').text if root.find('.//nNF') is not None else f"XML-{random.randint(1000,9999)}"
                    
                    data_emissao = root.find('.//dhEmi')
                    data_emissao = data_emissao.text[:10] if data_emissao is not None else root.find('.//dEmi').text if root.find('.//dEmi') is not None else time.strftime("%Y-%m-%d")
                    
                    emitente = root.find('.//xNome')
                    emitente = emitente.text if emitente is not None else "Fornecedor Não Identificado"
                    
                    valor_nota = root.find('.//vNF')
                    valor_nota = float(valor_nota.text) if valor_nota is not None else 0.0
                    
                    status_nota = "Pago" # Padrão para notas emitidas e recebidas
                    
                    dados_processados.append({
                        'id_transacao': id_nota,
                        'data': data_emissao,
                        'descricao': f"Nota Fiscal: {emitente}",
                        'categoria': 'Notas Recebidas',
                        'valor': valor_nota,
                        'status': status_nota
                    })
                    # Reseta o ponteiro de leitura do arquivo na memória
                    arquivo.seek(0)
                except Exception as e:
                    st.warning(f"Aviso: Não foi possível ler o arquivo {arquivo.name}. Estrutura inválida.")
            
            if dados_processados:
                df = pd.DataFrame(dados_processados)
    
    # Se os dados foram extraídos com sucesso (seja via CSV ou XML), mostra na tela
    if df is not None:
        st.subheader("📊 Lote de Dados Estruturados para Auditoria")
        st.dataframe(df, use_container_width=True)
        total_linhas_cliente = len(df)
        
        if st.button("🚀 Iniciar Auditoria Avançada"):
            if not licenca_usuario:
                st.error("⚠️ Acesso Negado: Por favor, insira uma Chave de Licença ScoutIA válida na barra lateral para ativar o software.")
            elif licenca_usuario not in BANCO_DE_LICENCAS:
                st.error("❌ Licença Inválida: O código inserido não foi localizado em nossa base de dados ativa.")
            else:
                dados_plano = BANCO_DE_LICENCAS[licenca_usuario]
                limite_permitido = dados_plano["limite_linhas"]
                
                if total_linhas_cliente > limite_permitido:
                    st.error(f"🚫 Limite do Plano Excedido! Seu lote possui **{total_linhas_cliente} registros**, mas seu plano **{dados_plano['plano']}** só permite até **{limite_permitido} registros** por lote.")
                    st.warning("💡 Faça o Upgrade do seu plano para liberar mais capacidade de processamento:")
                    st.table([
                        {"Plano": "Starter", "Capacidade": "Até 20 registros/lote", "Preço": "R$ 2.490/mês"},
                        {"Plano": "Enterprise", "Capacidade": "Até 200 registros/lote", "Preço": "R$ 7.990/mês"},
                        {"Plano": "Pro Custom", "Capacidade": "Registros Ilimitados", "Preço": "Sob Consulta"}
                    ])
                    st.info("📧 Contato comercial para liberação imediata de chaves: comercial@scoutia.ai")
                
                else:
                    st.sidebar.success(f"✅ Licença Ativa: Plano {dados_plano['plano']}")
                    status_container = st.empty()
                    sucesso = False
                    relatorio_final = ""
                    
                    # Telemetria enviada para o seu Google Sheets administrativo
                    try:
                        dados_uso = {
                            "licenca": licenca_usuario,
                            "plano": dados_plano["plano"],
                            "linhas_processadas": total_linhas_cliente,
                            "arquivo": nome_arquivo_log,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                        requests.post(WEBHOOK_MONITORAMENTO, json=dados_uso, timeout=2)
                    except Exception: pass

                    with st.spinner(f"O ScoutIA está executando a varredura do plano {dados_plano['plano']}..."):
                        # Tentativa via Inteligência Artificial na Nuvem
                        try:
                            client = genai.Client(api_key=CHAVE_INTERNA_IA)
                            dados_em_texto = df.to_markdown(index=False)
                            prompt_completo = (
                                "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
                                "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta. "
                                f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                                f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                            )
                            
                            max_tentativas = 3
                            tempo_base = 2.0
                            for tentativa in range(max_tentativas):
                                status_container.info(f"🔄 Conectando ao servidor seguro ({tentativa + 1}/{max_tentativas})...")
                                try:
                                    response = client.models.generate_content(model='gemini-3.8-flash', contents=prompt_completo)
                                    relatorio_final = response.text
                                    if relatorio_final: sucesso = True
                                    break
                                except Exception as e:
                                    erro_str = str(e)
                                    if "503" in erro_str or "UNAVAILABLE" in erro_str:
                                        time.sleep(tempo_base + random.uniform(0.1, 0.5))
                                        tempo_base *= 1.5
                                    else: break
                        except Exception: pass
                        
                        # Motor de Contingência Analítico Local
                        if not sucesso:
                            status_container.warning("⚠️ Canais externos ocupados. Acionando Motor de Contingência Analítico Local...")
                            time.sleep(1.0)
                            
                            duplicados = df[df.duplicated(subset=['data', 'descricao', 'valor'], keep=False)]
                            ids_duplicados = duplicados['id_transacao'].tolist()
                            alertas = []
                            perda_confirmada = 0.0
