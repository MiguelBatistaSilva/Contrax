import streamlit as st
import main

st.set_page_config(layout="wide",
                   initial_sidebar_state="expanded",
                   page_title="Contrax")

st.title('📑 Contrax Framework')

# Upload de arquivos
arquivos_subidos = st.file_uploader("📂 Carregar contratos", type=["docx"], accept_multiple_files=True)
arquivos_dict = {arquivo.name: arquivo for arquivo in arquivos_subidos} if arquivos_subidos else {}
versoes_validas = list(arquivos_dict.keys())

if len(versoes_validas) >= 2:
    col1, col2 = st.columns(2)
    with col1:
        versao_antiga = st.selectbox("📌 Versão Antiga:", versoes_validas, key="versao_antiga_unificado")
    with col2:
        versao_nova = st.selectbox("📌 Versão Nova:", versoes_validas, key="versao_nova_unificado")

    arquivo_antigo = arquivos_dict[versao_antiga]
    arquivo_novo = arquivos_dict[versao_nova]

    # Extrai as seções
    secoes_antigas = main.extrair_secoes(arquivo_antigo)
    secoes_novas = main.extrair_secoes(arquivo_novo)

    secoes_comuns = sorted(list(set(secoes_antigas.keys()) & set(secoes_novas.keys())))
    opcoes_selectbox = ["Contrato Inteiro"] + secoes_comuns

    secao_escolhida = st.selectbox("📌 Escolha a Cláusula (ou Contrato Inteiro):", opcoes_selectbox)

    # CSS da tabela
    css = """
    <style>
      :root {
          --background-color: transparent;
          --text-color: #000000;
      }
      [data-theme="dark"] {
          --background-color: #1e1e1e;
          --text-color: #ffffff !important; 
      }
      table.diff-table {
          width: 100%;
          font-family: 'Inter', sans-serif;    
      }
      table.diff-table th, table.diff-table td {
          padding: 12px 15px;
          white-space: pre-wrap;
          border-left: none !important;
          border-right: none !important;
          border-bottom: none !important;
      }
      table.diff-table thead {
          font-weight: 600;                
      }
      .diff-removed {
          background-color: #FFEBEE !important;
          color: #B71C1C !important;
      }
      .diff-added {
          background-color: #E8F5E9 !important;
          color: #1B5E20 !important;
      }
      [data-theme="dark"] .diff-removed {
          background-color: #330000 !important;
          color: #FF6666 !important;
      }
      [data-theme="dark"] .diff-added {
          background-color: #002200 !important;
          color: #66FF66 !important;
      }
      .comment-summary {
        font-size: 0.8em;
        opacity: 0.5;
        margin-top: 4px;
        padding-top: 4px;
        border-top: 1px solid var(--border-color);
      }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    if st.button("🔍 Comparar"):
        # Comparação Geral
        if secao_escolhida == "Contrato Inteiro":
            comentarios_antigos = main.extrair_comentarios(arquivo_antigo)
            comentarios_novos = main.extrair_comentarios(arquivo_novo)

            parags_antigos = main.extrair_paragrafos_com_tooltip(arquivo_antigo, comentarios_antigos)
            parags_novos = main.extrair_paragrafos_com_tooltip(arquivo_novo, comentarios_novos)

        # Comparação por Seção
        else:
            parags_antigos_brutos = secoes_antigas.get(secao_escolhida, [])
            parags_novos_brutos = secoes_novas.get(secao_escolhida, [])

            parags_antigos = main.split_paragraphs(parags_antigos_brutos)
            parags_novos = main.split_paragraphs(parags_novos_brutos)

            parags_antigos = [(p, "") for p in parags_antigos]
            parags_novos = [(p, "") for p in parags_novos]

        html_table = main.gerar_tabela_com_diff_somente_diferencas(parags_antigos, parags_novos)
        st.session_state.resultado_comparacao = html_table
        st.markdown(html_table, unsafe_allow_html=True)

    elif st.session_state.get("resultado_comparacao"):
        st.markdown(st.session_state.resultado_comparacao, unsafe_allow_html=True)

else:
    st.info("Por favor, carregue dois ou mais contratos para comparar.")
