import os
import time
import pandas as pd
from google import genai
from google.genai import types

def analisar_dados_fiscais(caminho_csv: str) -> str:
    """
    Carrega um arquivo CSV e executa a auditoria utilizando uma esteira de modelos
    com retentativas automáticas e backoff exponencial contra erros de servidor (503).
    """
    if not os.environ.get("GEMINI_API_KEY"):
        return "Erro: A variável de ambiente GEMINI_API_KEY não foi encontrada."

    client = genai.Client()

    try:
        df = pd.read_csv(caminho_csv)
        dados_em_texto = df.to_markdown(index=False)
    except Exception as e:
        return f"Erro ao ler o arquivo CSV: {str(e)}"

    prompt_sistema = (
        "Você é o ScoutIA Fiscal, um especialista sênior em auditoria financeira e compliance. "
        "Sua missão é analisar dados corporativos brutos, identificar erros de preenchimento, "
        "valores discrepantes (anomalias), possíveis fraudes ou pagamentos duplicados. "
        "Seja extremamente direto, profissional e aponte exatamente onde a empresa está perdendo capital."
    )

    instrucao_analise = (
        f"Analise a tabela de dados fiscais/financeiros abaixo:\n\n{dados_em_texto}\n\n"
        "Gere um relatório estruturado em formato Markdown contendo:\n"
        "1. **Resumo Executivo**: Diagnóstico geral da saúde dos dados.\n"
        "2. **Alertas Críticos encontrados**: Linhas exatas ou IDs onde há erros/anomalias.\n"
        "3. **Estimativa de Impacto Financeiro**: Quanto dinheiro está em risco ou foi perdido.\n"
        "4. **Plano de Ação imediato**: O que a equipe financeira deve fazer para corrigir."
    )

    # Rota de redundância estendida (Geração 3 e Geração 2)
    esteira_modelos = ['gemini-3.8-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']
    max_tentativas_por_modelo = 3

    for modelo in esteira_modelos:
        backoff = 2 # Tempo inicial de espera em segundos
        
        for tentativa in range(max_tentativas_por_modelo):
            try:
                print(f"[ScoutIA] Processando via {modelo} (Tentativa {tentativa + 1}/{max_tentativas_por_modelo})...")
                
                response = client.models.generate_content(
                    model=modelo,
                    contents=instrucao_analise,
                    config=types.GenerateContentConfig(
                        system_instruction=prompt_sistema
                    ),
                )
                return response.text
                
            except Exception as e:
                erro_str = str(e)
                # Verifica se é falha de servidor indisponível ou limite de requisições
                if "503" in erro_str or "UNAVAILABLE" in erro_str or "ResourceExhausted" in erro_str:
                    print(f"[Aviso] Servidor {modelo} ocupado. Aguardando {backoff}s para tentar novamente...")
                    time.sleep(backoff)
                    backoff *= 2 # Dobra o tempo de espera para a próxima tentativa (Backoff Exponencial)
                else:
                    # Se for outro tipo de erro (ex: autenticação), quebra e muda o modelo
                    print(f"[Erro crítico no modelo {modelo}]: {erro_str}")
                    break
                    
        print(f"[Aviso] Mudando de modelo para rota alternativa...")
        print("-" * 40)
            
    return "Erro Crítico de Infraestrutura: Todos os servidores do ecossistema Google AI Studio falharam após múltiplas tentativas. Tente novamente em instantes."

if __name__ == "__main__":
    arquivo_teste = "dados_financeiros.csv"
    
    relatorio_final = analisar_dados_fiscais(arquivo_teste)
    print("\n=== RELATÓRIO FINAL DE AUDITORIA ===")
    print(relatorio_final)
