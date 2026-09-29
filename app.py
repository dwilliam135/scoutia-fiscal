import streamlit as st
import pandas as pd
import os
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
                with st.spinner("O ScoutIA está processando os dados na nuvem... Aguarde."):
                    try:
                        # Inicialização limpa e direta do cliente
                        client = genai.Client(api_key=chave_limpa)
                        dados_em_texto = df.to_markdown(index=False)
                        
                        prompt_completo = (
                            "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
                            "Sua missão é identificar erros, anomalias e pagamentos duplicados de forma extremamente direta. "
                            f"Analise a tabela abaixo e gere um relatório em Markdown com Resumo Executivo, "
                            f"Alertas Críticos com IDs, Impacto Financeiro e Plano de Ação:\n\n{dados_em_texto}"
                        )
                        
                        # CORREÇÃO: Atualizado para o modelo obrigatório exigido pela Google
                        response = client.models.generate_content(
                            model='gemini-3.8-flash', 
                            contents=prompt_completo
                        )
                        
                        if response.text:
                            st.success("Auditoria Concluída com Sucesso!")
                            st.subheader("📋 Relatório Final de Auditoria e Conformidade")
                            st.markdown(response.text)
                        else:
                            st.error("O servidor retornou uma resposta vazia. Verifique os dados da planilha.")
                            
                    except Exception as e:
                        st.error(f"Falha na validação ou comunicação local da API: {str(e)}")
                        st.info("Dica: Certifique-se de que a chave colada na barra lateral está correta e ativa no Google AI Studio.")
                        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
