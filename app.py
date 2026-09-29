import streamlit as st
import pandas as pd
import os
import time
from google import genai
from google.genai import types

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

# Cabeçalho da Interface
st.title("🛡️ ScoutIA Fiscal — Auditoria Sênior & Compliance")
st.markdown("Suba a planilha financeira da sua empresa para que a nossa inteligência artificial audite erros, fraudes e gargalos de caixa.")

# Campo para o cliente fazer o upload do arquivo CSV
arquivo_upload = st.file_uploader("Escolha o arquivo CSV da sua planilha", type=["csv"])

if arquivo_upload is not None:
    # Mostrar os dados brutos para o cliente na tela
    st.subheader("📊 Dados Carregados da Planilha")
    try:
        df = pd.read_csv(arquivo_upload)
        st.dataframe(df, use_container_width=True)
        
        # Botão para iniciar a auditoria
        if st.button("🚀 Iniciar Auditoria Avançada"):
            if not os.environ.get("GEMINI_API_KEY"):
                st.error("Erro: A chave GEMINI_API_KEY não está configurada no servidor.")
            else:
                # Criamos um container de status para o cliente ver as tentativas em tempo real
                status_container = st.empty()
                
                with st.spinner("O ScoutIA está varrendo os dados... Aguarde."):
                    client = genai.Client()
                    dados_em_texto = df.to_markdown(index=False)
                    
                    prompt_sistema = (
                        "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
                        "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta."
                    )
                    
                    instrucao_analise = (
                        f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                        f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                    )
                    
                    # Esteira de redundância idêntica à do terminal
                    esteira_modelos = ['gemini-3.8-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
                    max_tentativas_por_modelo = 3
                    sucesso = False
                    relatorio_texto = ""

                    for modelo in esteira_modelos:
                        if sucesso:
                            break
                        backoff = 2
                        
                        for tentativa in range(max_tentativas_por_modelo):
                            status_container.info(f"🔄 Conectando via {modelo} (Tentativa {tentativa + 1}/{max_tentativas_por_modelo})...")
                            try:
                                response = client.models.generate_content(
                                    model=modelo,
                                    contents=instrucao_analise,
                                    config=types.GenerateContentConfig(system_instruction=prompt_sistema),
                                )
                                relatorio_texto = response.text
                                sucesso = True
                                break
                            except Exception as e:
                                erro_str = str(e)
                                if "503" in erro_str or "UNAVAILABLE" in erro_str or "ResourceExhausted" in erro_str:
                                    time.sleep(backoff)
                                    backoff *= 2
                                else:
                                    break
                                    
                    # Limpa o aviso de conexões após terminar
                    status_container.empty()

                    if sucesso:
                        st.success("Auditoria Concluída com Sucesso!")
                        st.subheader("📋 Relatório Final de Auditoria e Conformidade")
                        st.markdown(relatorio_texto)
                    else:
                        st.error("Erro Crítico de Infraestrutura: Todos os servidores do Google AI Studio falharam após múltiplas tentativas devido à alta demanda global. Tente novamente em instantes.")
                        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
