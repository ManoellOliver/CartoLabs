import requests
import pandas as pd

def buscar_dados_completos():
    """Coleta e organiza dados de atletas, clubes e partidas."""
    URL_MERCADO = "https://api.cartola.globo.com/atletas/mercado"
    URL_PARTIDAS = "https://api.cartola.globo.com/partidas"
    
    POSICOES = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
    STATUS = {7: 'Provável', 6: 'Nulo', 5: 'Contundido', 2: 'Dúvida', 3: 'Suspenso'}

    try:
        res_mercado = requests.get(URL_MERCADO).json()
        res_partidas = requests.get(URL_PARTIDAS).json()

        df_atletas = pd.DataFrame(res_mercado['atletas'])
        df_clubes = pd.DataFrame.from_dict(res_mercado['clubes'], orient='index')
        df_clubes['id'] = df_clubes['id'].astype(int)

        confrontos = {}
        for p in res_partidas['partidas']:
            m, v = p['clube_casa_id'], p['clube_visitante_id']
            confrontos[m] = {'adv': v, 'mando': 'Casa'}
            confrontos[v] = {'adv': m, 'mando': 'Fora'}

        df_atletas['posicao'] = df_atletas['posicao_id'].map(POSICOES)
        df_atletas['status'] = df_atletas['status_id'].map(STATUS)
        
        df = df_atletas.merge(df_clubes[['id', 'abreviacao']], left_on='clube_id', right_on='id')
        df['mando'] = df['clube_id'].map(lambda x: confrontos.get(x, {}).get('mando', 'N/A'))
        df['adv_id'] = df['clube_id'].map(lambda x: confrontos.get(x, {}).get('adv'))
        df = df.merge(df_clubes[['id', 'abreviacao']], left_on='adv_id', right_on='id', suffixes=('', '_adv'))

        # Score Base de Custo-Benefício
        df['score_cb'] = df['media_num'] / (df['preco_num'] + 0.1)
        df['valorizacao_potencial'] = (df['media_num'] > df['preco_num']).map({True: '🔥 Alta', False: '📉 Baixa'})

        return df
    except Exception as e:
        print(f"❌ Erro na coleta: {e}")
        return None

def escalar_time_pro_ajustado(df, orcamento=100, esquema='4-3-3'):
    """Algoritmo com Ponderação de Mando, Risco e Capitania."""
    config = {
        '4-3-3': {'GOL': 1, 'LAT': 2, 'ZAG': 2, 'MEI': 3, 'ATA': 3, 'TEC': 1},
        '4-4-2': {'GOL': 1, 'LAT': 2, 'ZAG': 2, 'MEI': 4, 'ATA': 2, 'TEC': 1}
    }.get(esquema)
    
    time_escalado = []
    custo_acumulado = 0
    df_provaveis = df[df['status'] == 'Provável'].copy()

    # --- LÓGICA DE INTELIGÊNCIA (Mando e Volatilidade) ---
    def calcular_score_elite(row):
        score = row['score_cb']
        
        # 1. Ajuste de Mando (Punição/Bônus para Defesa)
        if row['posicao'] in ['GOL', 'LAT', 'ZAG']:
            if row['mando'] == 'Casa':
                score *= 1.20  # +20% de peso por jogar em casa (SG)
            else:
                score *= 0.80  # -20% de peso por jogar fora
        
        # 2. Ajuste de Volatilidade (Risco de poucos jogos)
        if row['jogos_num'] < 3:
            score *= 0.85  # Pune quem tem média instável (menos de 3 jogos)
            
        return score

    df_provaveis['score_elite'] = df_provaveis.apply(calcular_score_elite, axis=1)

    # --- PROCESSO DE ESCALAÇÃO ---
    for pos, qtd_vagas in config.items():
        candidatos = df_provaveis[df_provaveis['posicao'] == pos].sort_values(by='score_elite', ascending=False)
        
        vagas_preenchidas = 0
        for _, jogador in candidatos.iterrows():
            vagas_totais_faltando = sum(config.values()) - len(time_escalado)
            reserva = (vagas_totais_faltando - 1) * 1.5
            
            if vagas_preenchidas < qtd_vagas:
                if (custo_acumulado + jogador['preco_num'] + reserva) <= orcamento:
                    time_escalado.append(jogador)
                    custo_acumulado += jogador['preco_num']
                    vagas_preenchidas += 1
        
        # Fallback (Garante time cheio mesmo se faltar verba)
        if vagas_preenchidas < qtd_vagas:
            baratos = candidatos.sort_values(by='preco_num', ascending=True)
            for _, jogador in baratos.iterrows():
                if vagas_preenchidas < qtd_vagas:
                    time_escalado.append(jogador)
                    custo_acumulado += jogador['preco_num']
                    vagas_preenchidas += 1
                
    df_time = pd.DataFrame(time_escalado)
    
    # --- INDICAÇÃO DE CAPITÃO ---
    # Capitão é o maior Score Elite que NÃO seja o técnico
    if not df_time.empty:
        id_capitao = df_time[df_time['posicao'] != 'TEC']['score_elite'].idxmax()
        df_time['cap'] = ""
        df_time.loc[id_capitao, 'cap'] = "⭐️"
    
    return df_time, custo_acumulado

def main():
    print("\n" + "="*65)
    print("      🧪 CARTOLALABS - SCANNER DE INTELIGÊNCIA PRO v1.2")
    print("="*65)

    df = buscar_dados_completos()
    
    if df is not None:
        try:
            patrimonio = float(input("💰 Patrimônio disponível (C$): "))
        except: patrimonio = 100.0

        formacao = input("🏟️ Formação (4-3-3 ou 4-4-2): ").strip()
        if formacao not in ['4-3-3', '4-4-2']: formacao = '4-3-3'

        time, custo = escalar_time_pro_ajustado(df, orcamento=patrimonio, esquema=formacao)
        
        print(f"\n✅ ESCALAÇÃO OTIMIZADA (Mando + Consistência + CB)")
        print("-" * 95)
        
        colunas_exib = ['cap', 'apelido', 'posicao', 'abreviacao', 'mando', 'abreviacao_adv', 'preco_num', 'media_num', 'jogos_num', 'valorizacao_potencial']
        
        exibicao = time[colunas_exib].rename(columns={
            'cap': ' ', 'abreviacao': 'CLU', 'abreviacao_adv': 'ADV', 
            'preco_num': 'PREÇO', 'media_num': 'MÉDIA', 'jogos_num': 'JOGOS', 'valorizacao_potencial': 'VALORIZ.'
        })
        
        print(exibicao.to_string(index=False))
        print("-" * 95)
        
        print(f"👥 Peças: {len(time)}/12 | 💸 Custo: C$ {custo:.2f} | 💰 Saldo: C$ {patrimonio-custo:.2f}")
        print(f"📊 Média Projetada: {time['media_num'].sum():.2f} pts")
        print("=" * 95)

if __name__ == "__main__":
    main()