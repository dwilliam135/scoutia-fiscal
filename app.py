import streamlit as st
import pandas as pd
import os
import time
import random
from google import genai
from google.genai import types

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

st.title("🛡️ ScoutIA Fiscal — Auditoria Sênior & Compliance")
st.markdown("Suba a planilha financeira da sua empresa para que a nossa inteligência artificial audite erros, fraudes e gargalos de caixa.")

# SISTEMA DE SEGURANÇA ALTERNATIVO PARA A CHAVE API
api_key_nuvem = os.environ.get("GEMINI_API_KEY")

if not api_key_nuvem:
    st.sidebar.subheader("🔑 Configuração de Acesso")
    api_key_usuario = st.sidebar.text_input("Insira sua Gemini API Key:", type="password")
    chave_final = api_key_usuario
else:
    chave_final = api_key_nuvem

# Campo para o cliente fazer o upload do arquivo CSV
arquivo_upload = st.file_uploader("Escolha o arquivo CSV da sua planilha", type=["csv"])

if arquivo_upload is not None:
    st.subheader("📊 Dados Carregados da Planilha")
    try:
        df = pd.read_csv(arquivo_upload)
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 Iniciar Auditoria Avançada"):
            if not chave_final:
                st.error("⚠️ Por favor, insira sua Gemini API Key na barra lateral esquerda para ativar o servidor de IA.")
            else:
                status_container = st.empty()
                
                with st.spinner("O ScoutIA está realizando uma varredura profunda... Aguarde."):
                    # MELHORIA DE INFRAESTRUTURA: Forçamos o cliente a rodar na rota estável 'v1'
                    # Isso desvia o tráfego do servidor v1beta congestionado do Google
                    client = genai.Client(
                        api_key=chave_final,
                        http_options=types.HttpOptions(api_version='v1')
                    )
                    
                    dados_em_texto = df.to_markdown(index=False)
                    
                    prompt_sistema = (
                        "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
                        "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta."
                    )
                    
                    instrucao_analise = (
                        f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                        f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                    )
                    
                    # Rota de modelos disponíveis nos canais de produção
                    esteira_modelos = ['gemini-3.8-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
                    max_tentativas_por_modelo = 5
                    sucesso = False
                    relatorio_texto = ""

                    for modelo in esteira_modelos:
                        if sucesso:
                            break
                        
                        backoff = 2.0 
                        
                        for tentativa in range(max_tentativas_por_modelo):
                            status_container.info(f"🔄 Conectando via Rota Estável v1 ({modelo} - Tentativa {tentativa + 1}/{max_tentativas_por_modelo})...")
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
                                    tempo_espera = backoff + random.uniform(0, 1.0)
                                    status_container.warning(f"⚠️ Rota ocupada. Insistindo em {tempo_espera:.1f}s...")
                                    time.sleep(tempo_espera)
                                    backoff *= 2.0
                                else:
                                    break
                                    
                    status_container.empty()

                    if sucesso:
                        st.success("Auditoria Concluída com Sucesso!")
                        st.subheader("📋 Relatório Final de Auditoria e Conformidade")
                        st.markdown(relatorio_texto)
                    else:
                        st.error("Erro Crítico de Infraestrutura: Todos os servidores da rota v1 e v1beta falharam. Tente novamente em instantes.")
                        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
