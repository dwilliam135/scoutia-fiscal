import streamlit as st
import pandas as pd
import os
import time
import random
from google import genai

# Configuração da página Web
st.set_page_config(page_title="ScoutIA Fiscal", page_icon="🛡️", layout="wide")

st.title("🛡️ ScoutIA Fiscal — Auditoria Sênior & Compliance")
st.markdown("Suba a planilha financeira da sua empresa para que a nossa inteligência artificial audite erros, fraudes e gargalos de caixa.")

# Barra lateral para inserção da chave
st.sidebar.subheader("🔑 Configuração de Acesso")
api_key_usuario = st.sidebar.text_input("Insira sua Gemini API Key:", type="password")

# Campo para o cliente fazer o upload do arquivo CSV
arquivo_upload = st.file_uploader("Escolha o arquivo CSV da sua planilha", type=["csv"])

if arquivo_upload is not None:
    st.subheader("📊 Dados Carregados da Planilha")
    try:
        df = pd.read_csv(arquivo_upload)
        st.dataframe(df, use_container_width=True)
        
        if st.button("🚀 Iniciar Auditoria Avançada"):
            # Limpeza manual de espaços ou quebras de linha na chave digitada
            chave_limpa = api_key_usuario.strip() if api_key_usuario else ""
            
            if not chave_limpa:
                st.error("⚠️ Por favor, insira sua Gemini API Key na barra lateral esquerda para ativar o servidor de IA.")
            else:
                # Caixa visual na tela para mostrar o andamento das tentativas
                status_container = st.empty()
                
                with st.spinner("O ScoutIA está realizando uma varredura profunda... Aguarde."):
                    client = genai.Client(api_key=chave_limpa)
                    dados_em_texto = df.to_markdown(index=False)
                    
                    prompt_completo = (
                        "Você é o ScoutIA Fiscal, um specialist sênior em auditoria financeira e compliance. "
                        "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta. "
                        f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                        f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                    )
                    
                    # Configuração do loop de persistência no modelo estável exigido
                    modelo_alvo = 'gemini-3.8-flash'
                    max_tentativas = 5
                    tempo_base = 3.0
                    sucesso = False
                    relatorio_final = ""

                    for tentativa in range(max_tentativas):
                        status_container.info(f"🔄 Conectando ao servidor ({tentativa + 1}/{max_tentativas})...")
                        try:
                            response = client.models.generate_content(
                                model=modelo_alvo, 
                                contents=prompt_completo
                            )
                            relatorio_final = response.text
                            sucesso = True
                            break # Se funcionar, quebra o loop imediatamente
                            
                        except Exception as e:
                            erro_str = str(e)
                            # Se for erro de servidor ocupado (503), aplica o recuo progressivo
                            if "503" in erro_str or "UNAVAILABLE" in erro_str:
                                # Calcula tempo de espera com uma pequena variação aleatória (Jitter)
                                tempo_espera = tempo_base + random.uniform(0.5, 1.5)
                                status_container.warning(f"⚠️ Servidores do Google congestionados. Aguardando {tempo_espera:.1f}s para tentar novamente...")
                                time.sleep(tempo_espera)
                                tempo_base *= 2.0 # Dobra o tempo para a próxima tentativa
                            else:
                                # Se for outro erro diferente de 503, exibe na tela imediatamente
                                status_container.error(f"Falha na validação local: {erro_str}")
                                break
                    
                    # Limpa os alertas de progresso após o término do loop
                    status_container.empty()

                    if sucesso:
                        st.success("Auditoria Concluída com Sucesso!")
                        st.subheader("📋 Relatório Final de Auditoria e Conformidade")
                        st.markdown(relatorio_final)
                    else:
                        st.error("🚨 Todos os servidores da Google AI falharam após múltiplas tentativas de conexão automática devido ao tráfego extremo. Aguarde 30 segundos e clique em Iniciar novamente.")
                        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
