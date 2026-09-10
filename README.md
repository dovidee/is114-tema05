# Barnehageopptak

Webapplikasjon for søknad om barnehageplass, skrevet i Flask. Applikasjonen tar imot en søknad,
behandler den automatisk mot antall ledige plasser og gir søkeren umiddelbart svar (`TILBUD` eller
`AVSLAG`). I tillegg viser den en oversikt over alle barnehager, alle innsendte søknader og
statistikk over andel barn i barnehage per kommune.

Prosjektet ble laget som obligatorisk oppgave 5 i IS-114 ved Universitetet i Agder.

## Kjøre lokalt

Krever Python 3.10+.

```bash
git clone https://github.com/dovidee/is114-tema05.git
cd is114-tema05
pip install -r requirements.txt
cd barnehage
python kg.py
```

Applikasjonen kjører på `http://127.0.0.1:5000`. Alle stier i koden er relative, så `kg.py` må
startes fra mappen `barnehage`.

Excel-databasen kan bygges på nytt ved å kjøre `python initiatedb.py`. Barnehagetabellen i
SQLite-databasen nullstilles ved å fjerne kommentaren rundt blokken «Reset barnehage data» nederst
i `kg.py` og kjøre filen en gang.

## Teknologi

| Komponent | Bruk |
|-----------|------|
| Flask | Webrammeverk og ruting |
| Flask-SQLAlchemy | ORM mot SQLite (`users`, `barnehage`) |
| sqlite3 | Direkte SQL i opptaksalgoritmen |
| pandas | Databehandling og lesing av Excel-filer |
| Plotly Express | Søylediagram over kommunestatistikk |
| Jinja2 | HTML-maler |

## Struktur

| Fil | Ansvar |
|-----|--------|
| `barnehage/kg.py` | Flask-app, ruter og databasemodeller |
| `barnehage/kgcontroller.py` | Opptaksalgoritmen, CRUD-metoder og grafgenerering |
| `barnehage/kgmodel.py` | Dataklasser: `Foresatt`, `Barn`, `Barnehage`, `Soknad` |
| `barnehage/dbexcel.py` | Leser `kgdata.xlsx` inn i DataFrames |
| `barnehage/initiatedb.py` | Oppretter Excel-databasen med utgangsdata |
| `barnehage/templates/` | Jinja2-maler |

| Rute | Beskrivelse |
|------|-------------|
| `/` | Forside |
| `/barnehager` | Oversikt over barnehager og ledige plasser |
| `/behandle` | Søknadsskjema (GET) og behandling av søknad (POST) |
| `/soknader` | Alle innsendte søknader med status |
| `/kommune` | Søylediagram over andel barn i barnehage for valgt kommune |

## Algoritme for søknadsbehandling

Behandlingen skjer i `behandle_soknad` i `kgcontroller.py`. Søknaden avgjøres av to felt:
om søkeren har **fortrinnsrett** (barnevern, sykdom i familien eller sykdom på barnet), og
hvilke barnehager søkeren har **prioritert**.

Prioriteringene skrives inn som en tekststreng adskilt med komma og mellomrom, i synkende
prioritet:

```
ABC Kindergarten, Tiny Tots Academy, Giggles and Grins Childcare, Playful Pals Daycare
```

### Steg

1. Prioriteringsstrengen splittes på `", "` til en liste. Tom streng betyr ingen prioritering.
2. Barnehagetabellen leses fra SQLite inn i en DataFrame med navn, antall plasser og ledige
   plasser.
3. Søknaden følger en av fire grener, avhengig av fortrinnsrett og prioritering (se tabellen
   under).
4. Når en plass tildeles, oppdateres barnehagen i databasen: `barnehage_ledige_plasser`
   reduseres med 1 og `barnehage_antall_plasser` økes med 1.
5. Søknaden lagres i tabellen `users` med tildelt barnehage, status og fortrinnsrett.

### Grener

| Fortrinnsrett | Prioritering | Rekkefølge på forsøk |
|---------------|--------------|----------------------|
| Nei | Nei | `gi_plass`, ellers `AVSLAG` |
| Nei | Ja | `gi_plass_prio`, så `gi_plass` (kun hvis nøyaktig en prioritering), ellers `AVSLAG` |
| Ja | Nei | `gi_plass`, så `stjel_plass`, ellers `AVSLAG` |
| Ja | Ja | `gi_plass_prio`, så `gi_plass`, så `stjel_plass_full`, ellers `AVSLAG` |

### Tildelingsmetoder

**`gi_plass`**: fritt valg. Barnehager uten ledige plasser filtreres bort, resten sorteres
synkende på antall ledige plasser, og den øverste velges. Søkeren får altså barnehagen med flest
ledige plasser. Feiler hvis ingen barnehager har ledige plasser.

**`gi_plass_prio`**: prioritert valg. Kun de prioriterte barnehagene beholdes. Disse sorteres i
den rekkefølgen søkeren oppga, deretter fjernes de uten ledige plasser, og den øverste velges.
Søkeren får altså den høyest prioriterte barnehagen som faktisk har en ledig plass. Feiler hvis
ingen av de prioriterte barnehagene har ledige plasser.

**`stjel_plass`**: kun ved fortrinnsrett når ingen plasser er ledige. Den nyeste søknaden uten
fortrinnsrett som har status `TILBUD` settes til `AVSLAG`, og plassen gis til søkeren med
fortrinnsrett. Feiler hvis alle eksisterende tilbud tilhører søkere med fortrinnsrett.

**`stjel_plass_full`**: samme prinsipp, men målrettet. Barnehagen med flest tildelte plasser
velges, og den nyeste søknaden uten fortrinnsrett i nettopp den barnehagen settes til `AVSLAG`.
Finnes ingen slik søknad, faller metoden tilbake til å frigjøre en vilkårlig plass som i
`stjel_plass`.

### Eksempler

Med utgangsdataene fra `initiatedb.py`, der `ABC Kindergarten` og `Giggles and Grins Childcare`
har null ledige plasser:

- `ABC Kindergarten, Tiny Tots Academy, Giggles and Grins Childcare` gir
  **Tiny Tots Academy**, fordi førsteprioriteten er full og neste prioritet med ledig plass velges.
- `ABC Kindergarten` alene: prioriteringen forkastes, og søkeren får barnehagen med flest ledige
  plasser (**Sunshine Preschool**). Med flere enn en prioritering, der ingen har ledig plass, blir
  svaret `AVSLAG` i stedet.

## Feilsøking

### `attempt to write a readonly database`

Feilen betyr at prosessen som kjører applikasjonen ikke har skriverettigheter på SQLite-filen.
SQLite oppretter også en journalfil ved siden av databasen, så **mappen** `instance/` må være
skrivbar i tillegg til selve filen:

```bash
chown www-data:www-data barnehage/instance barnehage/instance/db.sqlite3
chmod 755 barnehage/instance
chmod 644 barnehage/instance/db.sqlite3
```

Eieren skal være brukeren som **kjører Python-prosessen**. Kjøres applikasjonen med
`python kg.py` i et terminalvindu, er det din egen bruker, og da trengs ingen `chown` i det hele
tatt. Under en webtjener er det brukeren til applikasjonstjeneren (mod_wsgi, gunicorn, uWSGI):

| Distribusjon | Apache | Nginx |
|--------------|--------|-------|
| Debian / Ubuntu | `www-data` | `www-data` |
| RHEL / Rocky / AlmaLinux / CentOS | `apache` | `nginx` |
| Fedora | `apache` | `nginx` |

Merk at Nginx normalt bare er en reverse proxy og aldri rører databasefilen selv; det er brukeren
til prosessen bak proxyen som må ha skrivetilgang. På RHEL-baserte systemer og Fedora kan SELinux
blokkere skriving selv med riktige rettigheter. Da må filen merkes med
`chcon -t httpd_sys_rw_content_t`.

## Lisens

CC0 1.0 Universal. Se [LICENSE](LICENSE).
