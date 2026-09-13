# Barnehageopptak

Obligatorisk oppgave 5 i IS-114 ved Universitetet i Agder, høsten 2024. En webapplikasjon for
søknad om barnehageplass, skrevet i Flask. Applikasjonen tar imot en søknad, behandler den
automatisk mot antall ledige plasser og gir søkeren umiddelbart svar (`TILBUD` eller `AVSLAG`).
I tillegg viser den en oversikt over alle barnehager, alle innsendte søknader og statistikk over
andel barn i barnehage per kommune.

Utgangspunktet er et kodeskjelett utlevert i emnet, og oppgaveteksten ligger fortsatt igjen på
forsiden i `index.html`. Det som er skrevet her, er opptaksalgoritmen i `kgcontroller.py`, malene
for svar, søknadsoversikt, barnehageliste og kommunestatistikk, og rutene som hører til dem i
`kg.py`.

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

Excel-databasen skulle kunne bygges på nytt med `python initiatedb.py`, men filen stopper med
`IndentationError` slik den står (se [Merknader](#merknader)). Barnehagetabellen i
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

**`stjel_plass_full`**: samme prinsipp, men målrettet. Barnehager uten tildelte plasser
filtreres bort, resten sorteres, og den nyeste søknaden uten fortrinnsrett i den øverste
barnehagen settes til `AVSLAG`. Finnes ingen slik søknad, faller metoden tilbake til å frigjøre en
vilkårlig plass som i `stjel_plass`. Sorteringen er ment å plukke barnehagen med flest tildelte
plasser, men gjør det ikke (se [Merknader](#merknader)).

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

## Merknader

Prosjektet ble aldri gjort ferdig. Oblig 5 falt bort som krav underveis i semesteret, og arbeidet
stoppet der det sto den dagen. Punktene under er derfor ikke feil som slapp gjennom en innlevering,
men et bilde av hvor koden lå da den ble lagt fra seg: halvferdige grener, plassholdere merket
`# fikser senere`, oppgave 3 som aldri ble påbegynt, og et Excel-lag på vei ut til fordel for
SQLite uten at flyttingen ble fullført. Listen tar for seg det som faktisk ryker eller gir feil
svar, ikke skrivefeil og ubrukte importer, og står her som notat til meg selv.

- `initiatedb.py` kjører ikke. Linje 51 starter en trippel-fnutt-blokk med seks mellomrom innrykk
  inne i en `with`-blokk som ligger på åtte, og Python stopper med `IndentationError: unindent does
  not match any outer indentation level` før en eneste linje er utført. `kgdata.xlsx` i repoet er
  altså bygget med en tidligere versjon av filen, og skriptet må rettes før det kan kjøres igjen.
- `stjel_plass` returnerer strengen `'Unknown'`. Den finner riktig søknad å sette til `AVSLAG`,
  men vet ikke hvilken barnehage plassen tilhørte, så søkeren får `TILBUD` i en barnehage som ikke
  finnes. Barnehagetabellen røres heller ikke, så den frigjorte plassen registreres ingen steder:
  en søker mister plassen sin, en annen får den, og ingen av tallene i `/barnehager` endrer seg.
  To `# fikser senere` i samme funksjon sier det meste.
- `barnehage_antall_plasser` betyr to forskjellige ting. I `initiatedb.py` er det den totale
  kapasiteten (50, 25, 35, 12, 15, 10, 40), mens i SQLite settes den til `0` av reset-blokken i
  `kg.py` og økes med 1 for hver tildeling, altså antall **tildelte** plasser. Kolonnen heter
  likevel «Antall plasser» i `barnehager.html`, så en fersk database påstår at alle sju barnehagene
  har null plasser totalt og samtidig har ledige plasser. Riktig navn hadde vært
  `barnehage_tildelte_plasser`.
- `stjel_plass_full` sorterer på feil kolonne. Kommentaren sier «stjel fra høyeste antall» og
  filtreringen fjerner riktignok barnehager med `barnehage_antall_plasser == 0`, men
  `sort_values` sorterer på `barnehage_ledige_plasser`. Metoden nås bare når alt er fullt, altså
  når alle ledige plasser er 0, så sorteringen gjør ingenting og `df.loc[0]` plukker den første
  raden i id-rekkefølge. Meningen var `barnehage_antall_plasser`, og resultatet er at plassen
  stjeles fra en vilkårlig barnehage.
- To bare `except:` uten unntakstype fanger alt, inkludert feil fra databasen, og skriver
  `Kan ikke sortere!` uansett årsak. En feilstavet barnehage i skjemaet og en låst eller ødelagt
  databasefil ser helt like ut, og begge ender med `AVSLAG` til en søker som kanskje skulle fått
  plass. Feil som burde stoppet applikasjonen, blir i stedet til et svar.
- Prioriteringslisten parses med `split(', ')` og ingenting mer. Skriver du komma uten mellomrom,
  blir hele strengen ett navn som ikke matcher noe. Navnene er `isin`-matchet og dermed
  bokstavrette, og ukjente navn forsvinner stille. Søkeren får aldri vite at prioriteringen ble
  ignorert, og svaret ser ut som et helt vanlig vedtak. En nedtrekksliste per prioritet hadde
  fjernet hele problemet.
- Fallbacken ved akkurat en prioritering er inkonsistent. Har søkeren ingen fortrinnsrett, oppgir
  nøyaktig en barnehage og den er full, forkastes prioriteringen og `gi_plass` gir hvilken som
  helst barnehage. Med to eller flere fulle prioriteringer blir svaret `AVSLAG`. To søkere i samme
  situasjon får altså forskjellig svar avhengig av hvor mange barnehager de gadd å skrive opp.
  Sjekken `len(prioritert) == 1` har ingen motpart i fortrinnsrettgrenen.
- «Fortrinnsrett - Annet» og «Har søsken som går i barnehagen» gjør ingenting. Begge feltene finnes
  i `soknad.html`, men `behandle_soknad` ser kun på `fortrinnsrett_barnevern`,
  `fortrinnsrett_sykdom_i_familien` og `fortrinnsrett_sykdome_paa_barnet`, og `users`-tabellen har
  ingen kolonner for de to andre. En søker som begrunner fortrinnsrett i fritekstfeltet, blir
  behandlet som om hen ikke har fortrinnsrett i det hele tatt.
- Ingen validering i `/behandle`. Feltene hentes med `request.form['...']`, som gir 400 hvis et
  felt mangler, og en helt tom søknad godtas uten innvendinger. `instance/db.sqlite3` i repoet
  inneholder nettopp en slik rad: alle felt tomme, status `AVSLAG`.
- Ruten `/svar` viser en tom tabell. Den henter `session['information']` og sender den videre som
  `data`, mens `svar.html` leser `sdHar` og `sdStat`. Cellene blir derfor alltid tomme, og ruten
  gir 500 hvis ingen søknad ligger i sesjonen. Det virkelige svaret kommer fra `POST /behandle`,
  som rendrer den samme malen med riktige variabler. `/svar` er en rest som burde vært fjernet.
- `kommune_bar` krasjer på ukjent kommune. `str.fullmatch` er bokstavrett og eksakt, så en
  skrivefeil eller liten forbokstav gir et tomt utvalg, og `reduce` over en tom liste kaster
  `TypeError` som Flask svarer 500 på. `kommune.html` er et fritt tekstfelt uten noen liste over
  gyldige navn, så feilen er lett å treffe. Funksjonen er den samme koden som `kommune_pie` i
  OBLIG 3 og arver de samme forutsetningene: `pop(0)` antar at `Sted` er første kolonne, og
  `columns.difference(['Sted'])` antar at kolonnene sorterer alfabetisk i samme rekkefølge som i
  arket. Det stemmer for `Y2015` til `Y2023`, men er en forutsetning og ikke en garanti.
- Applikasjonen starter ikke uten `kgdata.xlsx`. `from dbexcel import *` øverst i
  `kgcontroller.py` leser Excel-filen ved import, selv om hele pandas-laget er ubrukt under
  kjøring: `form_to_object_soknad`, `insert_soknad`, `commit_all` og `select_alle_barnehager`
  importeres i `kg.py` og kalles aldri, og `Foresatt`, `Barn` og `Soknad` blir aldri laget. Bare
  `behandle_soknad` og `kommune_bar` er i faktisk bruk. Filen må altså ligge der for en modul
  ingenting spør etter.

## Lisens

CC0 1.0 Universal. Se [LICENSE](LICENSE).
