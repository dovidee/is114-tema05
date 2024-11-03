# kgcontroller module
import pandas as pd
import numpy as np
import altair as alt
import plotly
import plotly.express as px
from functools import reduce
from dbexcel import *
from kgmodel import *
import sqlite3
from flask import request
# CRUD metoder

# Create
# pd.append, pd.concat eller df.loc[-1] = [1,2] df.index = df.index + 1 df = df.sort_index()
def insert_foresatt(f):
    # Ikke en god praksis å oppdaterer DataFrame ved enhver endring!
    # DataFrame er ikke egnet som en databasesystem for webapplikasjoner.
    # Vanligvis bruker man databaseapplikasjoner som MySql, Postgresql, sqlite3 e.l.
    # 3 fremgangsmåter for å oppdatere DataFrame:
    # (1) df.colums er [['a', 'b']]
    #     df = pd.concat([pd.DataFrame([[1,2]], columns=df.columns), df], ignore_index=True)
    # (2) df = df.append({'a': 1, 'b': 2}, ignore_index=True)
    # (3) df.loc[-1] = [1,2]
    #     df.index = df.index + 1
    #     df = df.sort_index()
    global forelder
    new_id = 0
    if forelder.empty:
        new_id = 1
    else:
        new_id = forelder['foresatt_id'].max() + 1
    
    # skriv kode for å unngå duplikater
    
    forelder = pd.concat([pd.DataFrame([[new_id,
                                        f.foresatt_navn,
                                        f.foresatt_adresse,
                                        f.foresatt_tlfnr,
                                        f.foresatt_pnr]],
                columns=forelder.columns), forelder], ignore_index=True)
    
    
    return forelder

def insert_barn(b):
    global barn
    new_id = 0
    if barn.empty:
        new_id = 1
    else:
        new_id = barn['barn_id'].max() + 1
    
    # burde også sjekke for samme foresatt_pnr for å unngå duplikater
    
    barn = pd.concat([pd.DataFrame([[new_id,
                                    b.barn_pnr]],
                columns=barn.columns), barn], ignore_index=True)
    
    return barn

def insert_soknad(s):
    """[sok_id, foresatt_1, foresatt_2, barn_1, fr_barnevern, fr_sykd_familie,
    fr_sykd_barn, fr_annet, barnehager_prioritert, sosken__i_barnehagen,
    tidspunkt_oppstart, brutto_inntekt]
    """
    global soknad
    new_id = 0
    if soknad.empty:
        new_id = 1
    else:
        new_id = soknad['sok_id'].max() + 1
    
    
    # burde også sjekke for duplikater
    
    soknad = pd.concat([pd.DataFrame([[new_id,
                                     s.foresatt_1.foresatt_id,
                                     s.foresatt_2.foresatt_id,
                                     s.barn_1.barn_id,
                                     s.fr_barnevern,
                                     s.fr_sykd_familie,
                                     s.fr_sykd_barn,
                                     s.fr_annet,
                                     s.barnehager_prioritert,
                                     s.sosken__i_barnehagen,
                                     s.tidspunkt_oppstart,
                                     s.brutto_inntekt]],
                columns=soknad.columns), soknad], ignore_index=True)
    
    return soknad

# ---------------------------
# Read (select)

def select_alle_barnehager():
    """Returnerer en liste med alle barnehager definert i databasen dbexcel."""
    return barnehage.apply(lambda r: Barnehage(r['barnehage_id'],
                             r['barnehage_navn'],
                             r['barnehage_antall_plasser'],
                             r['barnehage_ledige_plasser']),
         axis=1).to_list()

def select_foresatt(f_navn):
    """OBS! Ignorerer duplikater"""
    series = forelder[forelder['foresatt_navn'] == f_navn]['foresatt_id']
    if series.empty:
        return np.nan
    else:
        return series.iloc[0] # returnerer kun det første elementet i series

def select_barn(b_pnr):
    """OBS! Ignorerer duplikater"""
    series = barn[barn['barn_pnr'] == b_pnr]['barn_id']
    if series.empty:
        return np.nan
    else:
        return series.iloc[0] # returnerer kun det første elementet i series
    
# --- Skriv kode for behandle_soknad her
def behandle_soknad(dat):
    prioritert = dat['liste_over_barnehager_prioritert_5']
    prioritert = prioritert.split(', ') # split user input
    fortrinn1 = dat.get('fortrinnsrett_barnevern')
    fortrinn2 = dat.get('fortrinnsrett_sykdom_i_familien')
    fortrinn3 = dat.get('fortrinnsrett_sykdome_paa_barnet')
    conn = sqlite3.connect('instance/janifuni.sqlite3')
    cursor = conn.cursor() # session.execute e bedre ik
    result = cursor.execute('SELECT * FROM barnehage')
    columns = [desc[0] for desc in result.description]
    bhdf = pd.DataFrame(cursor.fetchall(), columns=columns) # sql til pandas
    # dat = ('STATUS', 'FORTRINNSRETT')
    if fortrinn1 != None or fortrinn2 != None or fortrinn3 != None: # hvis har fortrinnsrett
        if prioritert == ['']:
            try: # trenger ikke å stjele
                returnNavn = gi_plass(bhdf, cursor, conn)
                dat = (returnNavn, 'TILBUD', 'JA')
                return dat
            except Exception as error: # stjel plass
                returnNavn = stjel_plass(cursor, conn)
                if returnNavn == None:
                    dat = (returnNavn, 'AVSLAG', 'JA')
                    return dat
                else:
                    dat = (returnNavn, 'TILBUD', 'JA')
                    return dat
        else: # FIX DIZ SHIDDDDDDDDDDDDDDDDDD
            print('alle ledig', bhdf)
            bhdfPrio = bhdf[bhdf['barnehage_navn'].isin(prioritert)] # vis kun prioritert
            try: # prøv vanlig order
                returnNavn = gi_plass_prio(bhdfPrio, cursor, conn, prioritert)
                dat = (returnNavn, 'TILBUD', 'JA')
                print('Prioritert funker!')
                return dat
            except: # første var ikke ledig så vanlig order
                print('Kan ikke sortere!')
                try:
                    returnNavn = gi_plass(bhdf, cursor, conn)
                    dat = (returnNavn, 'TILBUD', 'JA')
                    return dat
                except: # må vær tom
                    returnNavn = stjel_plass_full(bhdf, cursor, conn) # stjel fra høyeste antall
                    if returnNavn == None:
                        dat = (returnNavn, 'AVSLAG', 'JA')
                        return dat
                    else:
                        dat = (returnNavn, 'TILBUD', 'JA')
                        return dat
    else: # vanlig person
        if prioritert == ['']:
            try:
                returnNavn = gi_plass(bhdf, cursor, conn)
                dat = (returnNavn, 'TILBUD', 'NEI')
                return dat
            except Exception as error: # ingen plass
                print('Ingen ledig:', error)
                dat = ('', 'AVSLAG', 'NEI')
                return dat
        else:
            bhdfPrio = bhdf[bhdf['barnehage_navn'].isin(prioritert)] # vis kun prioritert
            try:
                returnNavn = gi_plass_prio(bhdfPrio, cursor, conn, prioritert)
                dat = (returnNavn, 'TILBUD', 'NEI')
                print('Prioritert funker!')
                return dat
            except: # kunne ikke sortere
                print('Kan ikke sortere!')
                if len(prioritert) == 1: 
                    print('Kun 1 prioritert')
                    try: # første prioritert har 0 plasser, så prøv uten
                        returnNavn = gi_plass(bhdf, cursor, conn)
                        dat = (returnNavn, 'TILBUD', 'NEI')
                        return dat
                    except: # funka ikke
                        print('Ingen plasser igjen')
                        dat = ('', 'AVSLAG', 'NEI')
                        return dat
                else:
                    print('Ingen plasser igjen')
                    dat = ('', 'AVSLAG', 'NEI')
                    return dat
def gi_plass(df, cur, con):
    df = df[(df['barnehage_ledige_plasser'] != 0)] # fjern null
    df = df.sort_values(by='barnehage_ledige_plasser', ascending=False, ignore_index=True) # sorter høy
    bhNavn = df.loc[0]['barnehage_navn']
    bhPlass = df.loc[0]['barnehage_ledige_plasser'] - 1
    bhAnt = df.loc[0]['barnehage_antall_plasser'] + 1
    print('Ledig', bhNavn)
    cur.execute('UPDATE barnehage SET barnehage_ledige_plasser = ?, barnehage_antall_plasser = ? WHERE barnehage_navn = ?', (int(bhPlass), int(bhAnt), bhNavn))
    print('Lagt i DB!')
    con.commit()
    con.close()
    print(df)
    return bhNavn

def gi_plass_prio(df, cur, con, pri):
    df = df.sort_values(by='barnehage_navn', key=lambda column: column.map(lambda e: pri.index(e)), ignore_index=False) # sorter prioritert
    df = df[(df['barnehage_ledige_plasser'] != 0)] # fjern null
    df = df.reset_index(drop=True) # reset index
    bhNavn = df.loc[0]['barnehage_navn']
    bhPlass = df.loc[0]['barnehage_ledige_plasser'] - 1
    bhAnt = df.loc[0]['barnehage_antall_plasser'] + 1
    print('Ledig', bhNavn)
    cur.execute('UPDATE barnehage SET barnehage_ledige_plasser = ?, barnehage_antall_plasser = ? WHERE barnehage_navn = ?', (int(bhPlass), int(bhAnt), bhNavn))
    print('Lagt i DB!')
    con.commit()
    con.close()
    print(df)
    return bhNavn

def stjel_plass(cur, con): # stjel fra nyeste ID
    tempRett = 'NEI'
    tempStat = 'AVSLAG'
    tempStat2 = 'TILBUD'
    # finn bruker som ikke har fortrinnsrett og har tilbud til plass
    checkexec = cur.execute('UPDATE users SET status = ? WHERE status = ? AND fortrinnsrett = ? ORDER BY id DESC LIMIT 1', (tempStat, tempStat2, tempRett))
    hasexec = checkexec.rowcount # 0 hvis alle har fortrinn, 1 hvis ingen har fortrinn
    if hasexec == 1:
        print('Stjal plass!', 'Unknown') # fikser senere
        con.commit()
        con.close()
        return 'Unknown' # fikser senere
    else:
        con.close()
        print('Alle har fortrinnsrett :(')
        return None

def stjel_plass_full(df, cur, con): # robin hood style
    df = df[(df['barnehage_antall_plasser'] != 0)] # finn kun de med antall
    df = df.sort_values(by='barnehage_ledige_plasser', ascending=False, ignore_index=True) # sorter høy
    bhNavn = df.loc[0]['barnehage_navn']
    tempRett = 'NEI'
    tempStat = 'AVSLAG'
    tempStat2 = 'TILBUD'
    # finn bruker som ikke har fortrinnsrett og har tilbud til plass
    checkexec = cur.execute('UPDATE users SET status = ? WHERE har_barnehage = ? AND status = ? AND fortrinnsrett = ? ORDER BY id DESC LIMIT 1', (tempStat, bhNavn, tempStat2, tempRett))
    hasexec = checkexec.rowcount
    if hasexec == 1:
        print('Stjal plass med prioritering!', bhNavn)
        con.commit()
        con.close()
        return bhNavn
    else: # siden den velger høyeste fra listen hver gang, prøv en random uten
        print('Kan ikke sortere! (har fortrinnsrett)')
        checkexec2 = cur.execute('UPDATE users SET status = ? WHERE status = ? AND fortrinnsrett = ? ORDER BY id DESC LIMIT 1', (tempStat, tempStat2, tempRett))
        hasexec2 = checkexec2.rowcount
        if hasexec2 == 1:
            print('Stjal plass!', 'Unknown') # fikser senere
            con.commit()
            con.close()
            return 'Unknown' # fikser senere
        else: # funka ikke
            con.close()
            print('Alle har fortrinnsrett med prioritering :(')
            return None

# ------------------
# Update


# ------------------
# Delete

# ----- Persistent lagring ------
def commit_all():
    """Skriver alle dataframes til excel"""
    with pd.ExcelWriter('kgdata.xlsx', mode='a', if_sheet_exists='replace') as writer:  
        forelder.to_excel(writer, sheet_name='foresatt')
        barnehage.to_excel(writer, sheet_name='barnehage')
        barn.to_excel(writer, sheet_name='barn')
        soknad.to_excel(writer, sheet_name='soknad')
        
# --- Diverse hjelpefunksjoner ---
def form_to_object_soknad(sd):
    """sd - formdata for soknad, type: ImmutableMultiDict fra werkzeug.datastructures
Eksempel:
ImmutableMultiDict([('navn_forelder_1', 'asdf'),
('navn_forelder_2', ''),
('adresse_forelder_1', 'adf'),
('adresse_forelder_2', 'adf'),
('tlf_nr_forelder_1', 'asdfsaf'),
('tlf_nr_forelder_2', ''),
('personnummer_forelder_1', ''),
('personnummer_forelder_2', ''),
('personnummer_barnet_1', '234341334'),
('personnummer_barnet_2', ''),
('fortrinnsrett_barnevern', 'on'),
('fortrinnsrett_sykdom_i_familien', 'on'),
('fortrinnsrett_sykdome_paa_barnet', 'on'),
('fortrinssrett_annet', ''),
('liste_over_barnehager_prioritert_5', ''),
('tidspunkt_for_oppstart', ''),
('brutto_inntekt_husholdning', '')])
    """
    # Lagring i hurtigminne av informasjon om foreldrene (OBS! takler ikke flere foresatte)
    foresatt_1 = Foresatt(0,
                          sd.get('navn_forelder_1'),
                          sd.get('adresse_forelder_1'),
                          sd.get('tlf_nr_forelder_1'),
                          sd.get('personnummer_forelder_1'))
    insert_foresatt(foresatt_1)
    foresatt_2 = Foresatt(0,
                          sd.get('navn_forelder_2'),
                          sd.get('adresse_forelder_2'),
                          sd.get('tlf_nr_forelder_2'),
                          sd.get('personnummer_forelder_2'))
    insert_foresatt(foresatt_2) 
    
    # Dette er ikke elegang; kunne returnert den nye id-en fra insert_ metodene?
    foresatt_1.foresatt_id = select_foresatt(sd.get('navn_forelder_1'))
    foresatt_2.foresatt_id = select_foresatt(sd.get('navn_forelder_2'))
    
    # Lagring i hurtigminne av informasjon om barn (OBS! kun ett barn blir lagret)
    barn_1 = Barn(0, sd.get('personnummer_barnet_1'))
    insert_barn(barn_1)
    barn_1.barn_id = select_barn(sd.get('personnummer_barnet_1'))
    
    # Lagring i hurtigminne av all informasjon for en søknad (OBS! ingen feilsjekk / alternativer)
        
    sok_1 = Soknad(0,
                   foresatt_1,
                   foresatt_2,
                   barn_1,
                   sd.get('fortrinnsrett_barnevern'),
                   sd.get('fortrinnsrett_sykdom_i_familien'),
                   sd.get('fortrinnsrett_sykdome_paa_barnet'),
                   sd.get('fortrinssrett_annet'),
                   sd.get('liste_over_barnehager_prioritert_5'),
                   sd.get('har_sosken_som_gaar_i_barnehagen'),
                   sd.get('tidspunkt_for_oppstart'),
                   sd.get('brutto_inntekt_husholdning'))
    
    return sok_1

# Testing
def test_df_to_object_list():
    assert barnehage.apply(lambda r: Barnehage(r['barnehage_id'],
                             r['barnehage_navn'],
                             r['barnehage_antall_plasser'],
                             r['barnehage_ledige_plasser']),
         axis=1).to_list()[0].barnehage_navn == "Sunshine Preschool"

# ------ Vis kommune graf ------

def kommune_bar(kommune : str) -> None:
    exc = pd.read_excel('kgkommune.xlsx')
    matched = exc['Sted'].str.fullmatch(kommune)
    chosen = exc.loc[matched[matched].index] # Boolean indexing til å finne kommune index
    to_flatten = chosen.values.tolist() # Velg tallene
    reduced_row = reduce(lambda x,y: x+y, to_flatten) # Fjern listen ut av listen med flatten
    reduced_row.pop(0) # Fjern kommunen
    reduced_col = chosen.columns.difference(['Sted'])
    data = {"År":reduced_col, "Prosent":reduced_row} # Samle årene og tallene i data
    exc = pd.DataFrame(data) # Lag en dataframe ut av data
    fig = px.bar(exc, x='År', y='Prosent', barmode='group')
    return fig
