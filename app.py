import streamlit as st
import pandas as pd
import os
import requests

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="CartoLabs Pro", layout="wide")

# CSS REFINADO
st.markdown("""
<style>
    .main { background-color: #111; }
    .soccer-field {
        position: relative;
        width: 100%;
        max-width: 550px;
        height: 750px;
        margin: 0 auto;
        background: radial-gradient(circle, #35985d 0%, #2e8b57 100%);
        border: 4px solid #fff;
        border-radius: 15px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        overflow: hidden;
    }
    .mid-line { position: absolute; top: 50%; width: 100%; height: 2px; background: rgba(255,255,255,0.4); }
    .center-circle { 
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
        width: 100px; height: 100px; border: 2px solid rgba(255,255,255,0.4); border-radius: 50%; 
    }
    .player-node { position: absolute; transform: translate(-50%, -50%); text-align: center; width: 90px; }
    .player-img { width: 65px; height: 65px; border-radius: 50%; border: 2px solid #fff; background: #222; object-fit: cover; }
    .player-label { background: #000; color: #fff; font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 4px; margin-top: -8px; display: inline-block; width: 85px; white-space: nowrap; overflow: hidden; }
    .score-tag { background: #fff; color: #000; font-size: 9px; font-weight: 900; padding: 1px 5px; border-radius: 10px; margin-top: 2px; display: inline-block; }
    .cap-ring { border: 3px solid #00ff00 !important; box-shadow: 0 0 15px #00ff00 !important; }
    .cap-badge { position: absolute; top: -5px; right: 10px; background: #00ff00; color: #000; font-size: 10px; font-weight: bold; width: 18px; height: 18px; border-radius: 50%; line-height: 18px; z-index: 100; border: 1px solid #000; }
    
    /* ESTILO DO STATUS DO MERCADO */
    .status-container { padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; font-weight: bold; }
    .status-open { background-color: rgba(0, 255, 0, 0.1); color: #00ff00; border: 1px solid #00ff00; }
    .status-closed { background-color: rgba(255, 0, 0, 0.1); color: #ff4b4b; border: 1px solid #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# LÓGICA DE CARREGAMENTO (COM STATUS DO MERCADO)
@st.cache_data(ttl=600)
def load_full_data():
    url = "https://api.cartola.globo.com/atletas/mercado"
    try:
        response = requests.get(url, timeout=10)
        dados = response.json()
        
        # Extrair Status do Mercado (1 = Aberto, 2 = Fechado)
        status_id = dados.get('status_mercado', 0)
        
        df = pd.DataFrame(dados['atletas'])
        
        try:
            pos_dict = {int(k): v['abreviatura'].upper() for k, v in dados['posicoes'].items()}
        except:
            pos_dict = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
            
        df['posicao'] = df['posicao_id'].map(pos_dict)
        df['media_num'] = pd.to_numeric(df['media_num'], errors='coerce').fillna(0)
        df['preco_num'] = pd.to_numeric(df['preco_num'], errors='coerce').fillna(5)
        df['foto'] = df['foto'].fillna('').str.replace('FORMATO', '140x140')
        
        return df, status_id
    except Exception as e:
        st.error(f"Erro ao conectar com o Cartola: {e}")
        return None, 0

def get_squad(df, orcamento, esquema):
    config = {'4-3-3': {'GOL':1,'LAT':2,'ZAG':2,'MEI':3,'ATA':3,'TEC':1},
              '4-4-2': {'GOL':1,'LAT':2,'ZAG':2,'MEI':4,'ATA':2,'TEC':1}}[esquema]
    selection = []
    current_budget = orcamento
    df_sorted = df.sort_values('media_num', ascending=False)
    
    for pos, count in config.items():
        added = 0
        candidates = df_sorted[df_sorted['posicao'] == pos]
        for _, row in candidates.iterrows():
            if added < count and row['preco_num'] <= (current_budget / (12 - len(selection))):
                selection.append(row)
                current_budget -= row['preco_num']
                added += 1
    return pd.DataFrame(selection), (orcamento - current_budget)

pos_map = {
    '4-3-3': {
        'GOL': [(88, 50)], 'LAT': [(68, 15), (68, 85)], 'ZAG': [(78, 35), (78, 65)],
        'MEI': [(48, 50), (45, 25), (45, 75)], 'ATA': [(18, 50), (22, 20), (22, 80)], 'TEC': [(92, 10)]
    },
    '4-4-2': {
        'GOL': [(88, 50)], 'LAT': [(70, 15), (70, 85)], 'ZAG': [(78, 35), (78, 65)],
        'MEI': [(50, 30), (50, 70), (40, 50), (58, 50)], 'ATA': [(20, 35), (20, 65)], 'TEC': [(92, 10)]
    }
}

# INTERFACE PRINCIPAL
df, status_mercado = load_full_data()

if df is not None:
    with st.sidebar:
        st.title("🛠️ Ajustes")
        
        # EXIBIÇÃO DO STATUS
        if status_mercado == 1:
            st.markdown('<div class="status-container status-open">🟢 MERCADO ABERTO</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-container status-closed">🔴 MERCADO FECHADO</div>', unsafe_allow_html=True)
            st.info("Os preços só atualizarão quando o mercado abrir.")

        cash = st.slider("Carteira", 80.0, 250.0, 140.0)
        form = st.selectbox("Formação", ["4-3-3", "4-4-2"])
        go = st.button("GERAR TIME")

    if go:
        squad, total = get_squad(df, cash, form)
        if not squad.empty:
            squad = squad.sort_values('media_num', ascending=False).reset_index(drop=True)
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Investimento", f"C$ {total:.2f}")
            m2.metric("Média Total", f"{(squad['media_num'].sum() + squad.loc[0,'media_num']):.2f}")
            m3.metric("Saldo", f"C$ {cash-total:.2f}")

            html_field = '<div class="soccer-field"><div class="mid-line"></div><div class="center-circle"></div>'
            counts = {k: 0 for k in pos_map[form].keys()}
            
            for i, row in squad.iterrows():
                pos = row['posicao']
                if pos in pos_map[form] and counts[pos] < len(pos_map[form][pos]):
                    top, left = pos_map[form][pos][counts[pos]]
                    counts[pos] += 1
                    is_c = (i == 0)
                    img_style = "player-img cap-ring" if is_c else "player-img"
                    badge = '<div class="cap-badge">C</div>' if is_c else ""
                    foto = row['foto']

                    p_html = f"""
<div class="player-node" style="top:{top}%; left:{left}%;">
{badge}
<img src="{foto}" class="{img_style}">
<div class="player-label">{row['apelido'].upper()}</div>
<div class="score-tag">{row['media_num']:.1f}</div>
</div>"""
                    html_field += p_html

            html_field += '</div>'
            st.markdown(html_field, unsafe_allow_html=True)