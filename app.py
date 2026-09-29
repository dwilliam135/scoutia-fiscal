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
                    client = genai.Client(api_key=chave_final)
                    dados_em_texto = df.to_markdown(index=False)
                    
                    prompt_sistema = (
                        "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
                        "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta."
                    )
                    
                    instrucao_analise = (
                        f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                        f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                    )
                    
                    # Esteira de modelos prioritários
                    esteira_modelos = ['gemini-3.8-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
                    
                    # MELHORIA: Aumentamos para 6 tentativas por modelo para insistir mais
                    max_tentativas_por_modelo = 6
                    sucesso = False
                    relatorio_texto = ""

                    for modelo in esteira_modelos:
                        if sucesso:
                            break
                        
                        # Tempo base inicial de espera aumentado para 3 segundos
                        backoff = 3.0 
                        
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
                                    # MELHORIA: Backoff Exponencial + Jitter (fator aleatório de milissegundos)
                                    tempo_espera = backoff + random.uniform(0, 1.5)
                                    status_container.warning(f"⚠️ Servidor instável. Aguardando {tempo_espera:.1f}s para insistir...")
                                    time.sleep(tempo_espera)
                                    backoff *= 2.0 # Dobra o tempo base para a próxima falha
                                else:
                                    # Se for outro erro (como chave inválida), muda de modelo imediatamente
                                    break
                                    
                    status_container.empty()

                    if sucesso:
                        st.success("Auditoria Concluída com Sucesso!")
                        st.subheader("📋 Relatório Final de Auditoria e Conformidade")
                        st.markdown(relatorio_texto)
                    else:
                        st.error("Erro Crítico de Infraestrutura: Todos os servidores do Google AI Studio estão sob tráfego extremo global. Deixamos o sistema insistindo ao máximo, mas a fila do Google travou. Aguarde 1 minuto e clique novamente.")
                        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
