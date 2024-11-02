import json
import plotly
import plotly.express as px
from flask import Flask
from flask import url_for
from flask import render_template
from flask import request
from flask import redirect
from flask import session
from flask import flash
from kgmodel import (Foresatt, Barn, Soknad, Barnehage)
from kgcontroller import (form_to_object_soknad, insert_soknad, commit_all, select_alle_barnehager, kommune_bar, behandle_soknad)
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'TAMALALALAALLAALLAAAAAAAAAAAAAAAAAAA0OBITXORM' # nødvendig for session
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///janifuni.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(minutes=5)

db = SQLAlchemy(app)

class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    navn_forelder_1 = db.Column(db.String(100))
    navn_forelder_2 = db.Column(db.String(100))
    adresse_forelder_1 = db.Column(db.String(100))
    adresse_forelder_2 = db.Column(db.String(100))
    tlf_nr_forelder_1 = db.Column(db.String(100))
    tlf_nr_forelder_2 = db.Column(db.String(100))
    personnummer_forelder_1 = db.Column(db.String(100))
    personnummer_forelder_2 = db.Column(db.String(100))
    personnummer_barnet_1 = db.Column(db.String(100))
    personnummer_barnet_2 = db.Column(db.String(100))
    tidspunkt_for_oppstart = db.Column(db.String(100))
    liste_over_barnehager_prioritert_5 = db.Column(db.String(100))
    brutto_inntekt_husholdning = db.Column(db.String(100))
    har_barnehage = db.Column(db.String(100))
    status = db.Column(db.String(100))
    fortrinnsrett = db.Column(db.String(100))

class barnehage(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    barnehage_navn = db.Column(db.String(100))
    barnehage_antall_plasser = db.Column(db.Integer)
    barnehage_ledige_plasser = db.Column(db.Integer)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barnehager')
def barnehager():
    return render_template('barnehager.html', values=barnehage.query.all())

@app.route('/behandle', methods=['GET', 'POST'])
def behandle():
    if request.method == 'POST':
        sd = request.form
        session['information'] = sd
        sdForm = sd.to_dict()
        sdSvar = behandle_soknad(sdForm)
        sdHar = sdSvar[0]
        sdStat = sdSvar[1]
        sdRett = sdSvar[2]
        # legg bruker i users DB
        sdUser = users(navn_forelder_1 = request.form['navn_forelder_1'],
                    navn_forelder_2 = request.form['navn_forelder_2'],
                    adresse_forelder_1 = request.form['adresse_forelder_1'],
                    adresse_forelder_2 = request.form['adresse_forelder_2'],
                    tlf_nr_forelder_1 = request.form['tlf_nr_forelder_1'],
                    tlf_nr_forelder_2 = request.form['tlf_nr_forelder_2'],
                    personnummer_forelder_1 = request.form['personnummer_forelder_1'],
                    personnummer_forelder_2 = request.form['personnummer_forelder_2'],
                    personnummer_barnet_1 = request.form['personnummer_barnet_1'],
                    personnummer_barnet_2 = request.form['personnummer_barnet_2'],
                    liste_over_barnehager_prioritert_5 = request.form['liste_over_barnehager_prioritert_5'],
                    tidspunkt_for_oppstart = request.form['tidspunkt_for_oppstart'],
                    brutto_inntekt_husholdning = request.form['brutto_inntekt_husholdning'],
                    har_barnehage = sdHar,
                    status = sdStat,
                    fortrinnsrett = sdRett
                    )
        db.session.add(sdUser)
        db.session.commit()
        return render_template('svar.html', sdHar=sdHar, sdStat=sdStat)
    else:
        return render_template('soknad.html')

@app.route('/kommune', methods=['GET', 'POST'])
def kommune():
   if request.method == 'POST':
       chosen_kommune = request.form.get('valgtkommune')
       created_kommune = kommune_bar(chosen_kommune)
       graphJSON = json.dumps(created_kommune, cls=plotly.utils.PlotlyJSONEncoder)
       return render_template('bar.html', graphJSON=graphJSON, chosen_kommune=chosen_kommune)
   else:
       return render_template('kommune.html')

@app.route('/soknader')
def soknader():
   return render_template('soknader.html', values=users.query.all())

@app.route('/svar')
def svar():
    information = session['information']
    print(information)
    return render_template('svar.html', data=information)

if __name__ == '__main__':
    with app.app_context():
       db.create_all()
       '''
       # Reset barnehage data
       sun = barnehage(id=1, barnehage_navn='Sunshine Preschool', barnehage_antall_plasser=0, barnehage_ledige_plasser=15)
       hap = barnehage(id=2, barnehage_navn='Happy Days Nursery', barnehage_antall_plasser=0, barnehage_ledige_plasser=2)
       learn = barnehage(id=3, barnehage_navn='123 Learning Center', barnehage_antall_plasser=0, barnehage_ledige_plasser=4)
       abc = barnehage(id=4, barnehage_navn='ABC Kindergarten', barnehage_antall_plasser=0, barnehage_ledige_plasser=0)
       tiny = barnehage(id=5, barnehage_navn='Tiny Tots Academy', barnehage_antall_plasser=0, barnehage_ledige_plasser=5)
       gigl = barnehage(id=6, barnehage_navn='Giggles and Grins Childcare', barnehage_antall_plasser=0, barnehage_ledige_plasser=0)
       play = barnehage(id=7, barnehage_navn='Playful Pals Daycare', barnehage_antall_plasser=0, barnehage_ledige_plasser=6)

       db.session.add(sun)
       db.session.add(hap)
       db.session.add(learn)
       db.session.add(abc)
       db.session.add(tiny)
       db.session.add(gigl)
       db.session.add(play)
       db.session.commit()
       '''
    app.run(port=5000)


"""
Referanser
[1] https://stackoverflow.com/questions/21668481/difference-between-render-template-and-redirect
"""

"""
Søkeuttrykk

"""
