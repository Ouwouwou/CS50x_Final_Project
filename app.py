import os
import re
import sqlite3
import time
from datetime import date, timedelta
from tempfile import mkdtemp

import xlsxwriter
from flask import (Flask, flash, redirect, render_template, request, session,
                   url_for, send_file)
from flask_mail import Mail, Message
from flask_session import Session
from validate_email import validate_email
from werkzeug.exceptions import (HTTPException, InternalServerError,
                                 default_exceptions)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_googlemaps import GoogleMaps, Map

from helpers import allowed_file, eur, login_required, admin_required, get_pending_orders, get_pending_in_date_range, get_online_vegs, get_offline_vegs

# Set global variables for source and destination folders + needed env variables
UPLOAD_FOLDER = 'static/uploads/'
DOWNLOAD_FOLDER = 'static/commandes_xlsx/'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
GOOGLEMAPS_KEY = os.environ.get('GOOGLEMAPS_KEY')
# Configure app
app = Flask(__name__, template_folder='templates')

# Ensure all the template are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Config the app to upload in the set folder only certain size of file
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Same but for downloads
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# Configure  app to send mail
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Initiate the Google Maps API
# you can set key as config
app.config['GOOGLEMAPS_KEY'] = GOOGLEMAPS_KEY
GoogleMaps(app, key=GOOGLEMAPS_KEY)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["eur"] = eur

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def index():
    #Return the homepage
    return render_template("index.html")

@app.route("/admin")
@login_required
@admin_required
def admin():
    online_vegs = get_online_vegs()

    en_attente = get_pending_orders()

    return render_template("admin_index.html", online_vegs=online_vegs, en_attente=en_attente)

@app.route("/download_LastWeek", methods=["POST"])
@login_required
@admin_required
def download_LastWeek():
    # Get today's date at time format
    time = date.today()

    # Get the date list of dates between today and 7 days ago
    day_range = 7
    date_list = [time - timedelta(days=x) for x in range(day_range)]
    WeekAgoSQLFormat = date_list[-1]
    LastWeekRange_SQLFormat = [WeekAgoSQLFormat, time]

    # Format Xlsx file name to "commandes(date 7 days ago_date today)"
    todayXlsName = time.strftime("%d%m%Y")
    WeekAgoXlsName = date_list[-1].strftime("%d%m%y")

    xlsName = "commandes{}_{}.xlsx".format(WeekAgoXlsName, todayXlsName)

    en_attente = get_pending_in_date_range(LastWeekRange_SQLFormat)

    # Create the Excel file
    workbook = xlsxwriter.Workbook("static/commandes_xlsx/{}".format(xlsName))
    worksheet = workbook.add_worksheet()

    # Add a bold format to use to highlight cells.
    bold = workbook.add_format({'bold': True})
    center = workbook.add_format()
    center.set_align('center')

    # Write some data headers.
    worksheet.write('A1', 'Récapitulatif des commandes passées durant les 6 derniers jours', bold)
    worksheet.write('B1', '{}'.format(time), bold)

    # Start from the third row. Rows and columns are zero indexed.
    row = 2
    col = 0

    for commande in en_attente:
        worksheet.write(row, col, commande["name"], bold)
        worksheet.write(row, col+1, commande["selling_point"], bold)
        worksheet.write(row, col+2, "€ {}".format(commande["total_price"]), bold)
        row += 1
        for legume in commande["legumes"]:
            worksheet.write(row, col, legume["veg_name"])
            worksheet.write(row, col+1, legume["veg_qty"], center)
            worksheet.write(row, col+2, legume["veg_unit"])
            row += 1
        row += 1

    # Close the Excel file
    workbook.close()

    xlsxPath = os.path.join(app.config['DOWNLOAD_FOLDER'], xlsName)

    online_vegs = get_online_vegs()

    return send_file(xlsxPath, as_attachment=True)
    return render_template("admin_index.html", online_vegs=online_vegs, en_attente=en_attente)

@app.route ("/connexion", methods=["GET", "POST"])
def connexion():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        #Set database to execute queries
        db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
        cur = db.cursor()

        # Query database for username
        cur.execute("SELECT * FROM users WHERE username = ?", [request.form.get("utilisateur")])
        rows = cur.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or check_password_hash(rows[0][2], request.form.get("password")) == False:
            flash("Nom d'utilisateur et/ou mot de passe invalide", category='warning')
            return render_template("connexion.html")

        # Remember which user has logged in
        session["user_id"] = rows[0][0]
        session["username"] = rows[0][1]

        # Close connection to DB and kill cursor
        cur.close()
        db.close()

        # Redirect user to home page
        # Return Elisa to admin dashboard
        if session["username"] == "Elisadmin":
            online_vegs = get_online_vegs()

            en_attente = get_pending_orders()

            return render_template("admin_index.html", online_vegs=online_vegs, en_attente=en_attente)
        else:
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("connexion.html")

@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route ("/inscription", methods=["GET", "POST"])
def inscription():
    """Register user"""
    if request.method == "POST":
        # Ensure username was submitted
        username = request.form.get("username")

        # Ensure password was submitted
        password = request.form.get("password")

        # Ensure password has been confirmed
        password_confirmation = request.form.get("confirmation")

        # Ensure password is correctly confirmed
        if password != password_confirmation:
            flash("Le mot de passe et sa confirmation ne correspondent pas", category='warning')
            return render_template("inscription.html")

        #Set database to execute queries
        db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
        cur = db.cursor()

        # Query database to see if the username is already taken
        cur.execute("SELECT * FROM users WHERE username = ?", [request.form.get("username")])
        namecheck = cur.fetchone()
        if namecheck != None:
            flash("Ce nom d'utilisateur est déjà pris", category='warning')
            return render_template("inscription.html")

        cur.execute("SELECT * FROM users WHERE email = ?", [request.form.get("email")])
        mailcheck = cur.fetchone()
        if mailcheck != None:
            flash("Cette adresse email est déjà associé à un compte", category='warning')
            return render_template("inscription.html")

        # validate_email check
        is_valid = validate_email(
            email_address = request.form.get("email"),
            check_format=True,
            check_blacklist=True,
            check_dns=True,
            dns_timeout=10,
            check_smtp=True,
            smtp_timeout=10,
            smtp_helo_host='smtp.gmail.com',
            smtp_from_address='python.tuile.test@gmail.com',
            smtp_skip_tls=False,
            smtp_tls_context=None,
            smtp_debug=False)

        # Create list to be inserted in db
        email = request.form.get("email")
        password_hash = generate_password_hash(request.form.get("password"),'pbkdf2:sha256', 8)
        user_info = [username, password_hash, email]

        # Finally, if all the checks are passed, register the user in the database
        cur.executemany("INSERT INTO users (username, hash, email) VALUES (?, ?, ?)", [user_info])
        db.commit() # Save changes

        # Send mail with users details
        sender = MAIL_USERNAME
        subject = "Inscription aux Petits Oignons - Votre compte"

        msg = Message(subject, sender=sender, recipients=[email])
        msg.body = """Bonjour,
            Merci de vous être inscrit(e) sur le site aux Petits Oignons !
            Votre compte a bien été initialisé et vous pouvez dorénavant vous connecter pour commander des paniers.
            Ci-dessous, retrouvez les détails de votre compte qui vous serviront en cas d'oubli / perte des identifiants.
            """
        # In fact, you can just return a template. Gmail is not friendly with any of the styling...
        msg.html = render_template("inscription_mail.html", username=username, password=password)
        mail.send(msg)

        cur.close() # Kill the cursor
        db.close()  # Close connection to db

        flash("Votre inscription a été réalisée avec succès. Un mail contenant vos informations a été envoyé à l'adresse mail renseignée", category='success')
        return redirect("/connexion")

    else:
        return render_template("inscription.html")

@app.route("/history")
@login_required
def history():
    # Va chercher dans la DB les commandes faites par l'utilisateur et renvoie la date et le prix de la commande
    # Set database to execute queries
    db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    user_commandes = cur.execute("""SELECT id, status, strftime("%d/%m/%Y", time) AS time, selling_point, total_price FROM commandes WHERE user_id = ? ORDER BY status, time DESC""", (session["user_id"],)).fetchall()

    commandes = []
    for commande in user_commandes:
        commande = {"id" : commande["id"],
            "status" : commande["status"],
            "time" : commande["time"],
            "selling_point" : commande["selling_point"],
            "total_price" : commande["total_price"],
            "legumes" : []}
        commande_legumes = cur.execute("""SELECT legume_id, prix, qty FROM commandes_items WHERE commandes_id = ?""", [commande["id"]]).fetchall()
        for commande_legume in commande_legumes:
            name_unit = cur.execute("""SELECT name, unit FROM legumes WHERE id = ?""", (commande_legume["legume_id"],)).fetchone()
            legume = {"veg_name" : name_unit[0],
                "veg_unit" : name_unit[1],
                "veg_id" : commande_legume["legume_id"],
                "veg_price" : commande_legume["prix"],
                "veg_qty" : commande_legume["qty"]}
            commande["legumes"].append(legume)
        commandes.append(commande)

    cur.close() # Kill the cursor
    db.close()  # Close connection to db

    if user_commandes != None:
        return render_template("history.html", **locals())
    else:
        return render_template("empty_history.html")

@app.route("/legumes", methods=["GET", "POST"])
@login_required
@admin_required
def legumes():
    if request.method == "POST":
        if request.form['submit_button'] == 'submit_new_legume':
        # Following dozen of line taken from Flask 2.0 tutorial - https://flask.palletsprojects.com/en/2.0.x/patterns/fileuploads/
        # Perform tests if an img has been submitted, screen for format and upload the img to UPLOADS in static
            if not request.files['img_legume']:
                flash('No file part')
                print("Pas de fichier détecté")
            img = request.files['img_legume']
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if img.filename == '':
                flash('No selected file')
                print("Pas de fichier sélectionné")
            if img and allowed_file(img.filename):
                filename = secure_filename(img.filename)
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Convert the img to binary data
            legume_blob = str(img_path)

            # Check for no doubles
            legume_name = request.form.get("name_legume")

            db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
            cur = db.cursor()

            cur.execute("SELECT * FROM legumes WHERE name = ?", [legume_name,])
            namecheck = cur.fetchone()
            if namecheck != None:

                online_vegs = get_online_vegs()
                offline_vegs = get_offline_vegs()

                flash("Un légume avec ce nom là est déjà enregistré !", category='warning')
                return render_template("legumes.html", online_vegs=online_vegs, offline_vegs=offline_vegs)

            # Get all the other info and put all of that in a tuple
            legume_unit = request.form.get("unit_legume")
            legume_unit_price = float(request.form.get("prix_unit_legume"))
            legume_status = request.form.get("statut_legume")

            new_legume = (legume_blob, legume_name, legume_unit, legume_unit_price, legume_status)

            cur.execute("INSERT INTO legumes (image, name, unit, prix_unit, status) VALUES (?, ?, ?, ?, ?)", new_legume)
            db.commit()

            # Kill cursor and connection to db
            cur.close()
            db.close()

            online_vegs = get_online_vegs()
            offline_vegs = get_offline_vegs()

            flash("Nouveau légume bien enregistré !", category='success')
            return render_template("legumes.html", online_vegs=online_vegs, offline_vegs=offline_vegs)

        elif request.form['submit_button'] == "update_legumes":
            legume_2_update_id = request.form.getlist("id_legume")
            legume_2_update_prix = request.form.getlist("prix_unit_legume")
            legume_2_update_status = request.form.getlist("statut_legume")
            legumes_2_update = tuple((zip(legume_2_update_prix, legume_2_update_status, legume_2_update_id)))

            # Connect to db
            db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
            cur = db.cursor()

            # Query the database for update
            for index, item in enumerate(legumes_2_update):
                cur.execute("UPDATE legumes SET prix_unit = ?, status = ? WHERE id = ?", legumes_2_update[index])
                db.commit()
            # Kill cursor and connection to db
            cur.close()
            db.close()

            online_vegs = get_online_vegs()
            offline_vegs = get_offline_vegs()

            return render_template("legumes.html", online_vegs=online_vegs, offline_vegs=offline_vegs)
    else:
        online_vegs = get_online_vegs()
        offline_vegs = get_offline_vegs()

        return render_template("legumes.html", online_vegs=online_vegs, offline_vegs=offline_vegs)

@app.route("/choisir", methods=["GET", "POST"])
@login_required
def choisir():
    if request.method == "POST":
        # Create the cart when landing on page
        if request.form['submit_button'] == "add_legume":
            # Open database to query the legume added
            db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
            # This allows cur.execute to return dict {} shaped results
            db.row_factory = sqlite3.Row
            cur = db.cursor()

            _name = request.form.get("name_legume")
            print(_name)
            _quantity = float(request.form.get("quantity_legume"))
            print(_quantity)
            _id = request.form.get("id_legume")
            print(_id)

            cur.execute("SELECT * FROM legumes WHERE id = ?", [_id,])
            item = cur.fetchone()
            print(item)

            # Format the input to be stored in session["cart"]
            item_data = {item["id"] : {'image' : item["image"], 'code' : item["id"], 'name' : item["name"], 'unit' : item["unit"], 'prix_unit' : item["prix_unit"], 'quantity' : _quantity, 'prix_total' : round(item["prix_unit"] * _quantity, 2)}}

            # Format the total price of the cart / Reset it
            cart_total_price = 0

            # Session requires this to store new variables
            session.modified = True

            if "cart" in session:
                # Check if a legume id is already in the cart
                if item["id"] in session["cart"]:
                    # if yes, loop through the existing cart items and...
                    for key, value in session["cart"].items():
                        # Get the one that matches the item we are adding
                        if item["id"] == key:
                            # Update quantity
                            old_quantity = session["cart"][key]["quantity"]
                            total_quantity = old_quantity + _quantity
                            session["cart"][key]["quantity"] = total_quantity
                            # Update total price according to new total quantity
                            session["cart"][key]["prix_total"] = round(total_quantity * item["prix_unit"], 2)
                else:
                    # Add item_data to existing different cart items
                    session["cart"] = dict(list(session["cart"].items()) + list(item_data.items()))

                # Then calculate in either case the total price of the cart as addition of all items ["prix_total"]
                for key, value in session["cart"].items():
                    item_price = float(session["cart"][key]["prix_total"])
                    cart_total_price = cart_total_price + item_price

            else:
                # Create the cart as the first formatted input
                session["cart"] = item_data
                cart_total_price =  item_data[item["id"]]["prix_total"]

            # Store the cart price in session
            session["cart_total_price"] = round(cart_total_price, 2)

            # Kill cursor and connection to db
            cur.close()
            db.close()

            online_vegs = get_online_vegs()

            return render_template("faire_un_panier.html", online_vegs=online_vegs)

    else:
        online_vegs = get_online_vegs()

        return render_template("faire_un_panier.html", online_vegs=online_vegs)

@app.route("/empty_cart")
@login_required
def empty_cart():
    if "cart" in session:
        session.pop("cart")
    if "cart_total_price" in session:
        session.pop("cart_total_price")

    online_vegs = get_online_vegs()

    flash("Votre panier a été vidé.", category='success')
    return render_template("faire_un_panier.html", online_vegs=online_vegs)

@app.route("/delete/<string:code>")
@login_required
def delete_product(code):
    # Reset the total price
    cart_total_price = 0
    session.modified = True

    for item in session["cart"].items():
        if item[0] == int(code):
            session["cart"].pop(item[0], None)
            for key, value in session["cart"].items():
                individual_price = float(session["cart"][key]["prix_total"])
                cart_total_price = cart_total_price + individual_price
            break

    # Pop the cart if it's empty
    if cart_total_price == 0:
        session.pop("cart")
        session.pop("cart_total_price")

    else:
        session["cart_total_price"] = cart_total_price

    online_vegs = get_online_vegs()

    flash("Un légume a été retiré du panier.", category='warning')
    return redirect(url_for('.choisir'))

@app.route("/validate_cart", methods=["GET", "POST"])
@login_required
def validate_cart():
    if request.method == "POST":
        if "cart" in session:
            # Get the info of the form to prepare INSERT request into commandes table
            user_id = session["user_id"]
            status = "En attente"
            selling_point = request.form.get("delivery")
            total_price = session["cart_total_price"]

            # Get the time
            time = date.today()

            # Create the tuple for the query
            new_commande = [user_id, status, time, selling_point, total_price]

            # INSERT INTO commandes
            db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
            cur = db.cursor()

            cur.execute("""INSERT INTO commandes (user_id, status, time, selling_point, total_price) VALUES (?, ?, ?, ?, ?)""", new_commande)
            db.commit()

            # Loop the cart to insert items in commandes_items
            # SELECT last entry
            cur.execute("""SELECT last_insert_rowid()""")
            commande_id = cur.fetchone()

            for key, value in session["cart"].items():
                legume_id = key
                prix = float(session["cart"][key]["prix_total"])
                qty = session["cart"][key]["quantity"]
                commande_item = [commande_id[0], legume_id, prix, qty]
                cur.execute("""INSERT INTO commandes_items (commandes_id, legume_id, prix, qty) VALUES (?, ?, ?, ?)""", commande_item)
                db.commit()

            # Send e-mail
            cur.execute("""SELECT email, username FROM users WHERE id = ?""", (session["user_id"],))
            receiver = cur.fetchone()
            sender = "python.tuile.test@gmail.com"
            subject = "Votre commande aux Petits Oignons"

            cur.execute("""SELECT legume_id, qty FROM commandes_items WHERE commandes_id = ?""", (commande_id[0],))
            vegs_commande = cur.fetchall()
            # Formatting the query as a list of list rather than pissy tuples
            final_vegs_commande = [list(i) for i in vegs_commande]

            for veg_commande in final_vegs_commande:
                name = cur.execute("""SELECT name FROM legumes WHERE id = ?""", (veg_commande[0],)).fetchone()
                veg_commande[0] = name[0]

            msg = Message(subject, sender=sender, recipients=[receiver[0]])
            msg.body = """Bonjour,
                Merci d'avoir commandé sur le site aux Petits Oignons !
                Votre commande est en cours de préparation et sera bientôt disponible au point de retrait choisi: {}.
                Pour connaître les nouveaux arrivages, n'hésitez pas à visiter régulièrement le site web où les légumes disponibles seront mis en ligne.
                Les Petits Oignons honoreront les commandes dans la limite des stocks disponibles seulement.""".format(selling_point)
            # In fact, you can just return a template. Gmail is not friendly with any of the styling...
            msg.html = render_template("commande_mail.html", selling_point=selling_point, session=session, final_vegs_commande=final_vegs_commande)
            mail.send(msg)

            # Kill cursor and connection to db
            cur.close()
            db.close()
            # Send notification to the admin ?

            session.pop("cart")
            session.pop("cart_total_price")

            online_vegs = get_online_vegs()

            flash("Votre commande a bien été enregistrée !", category='success')
            return render_template("faire_un_panier.html", online_vegs=online_vegs)

        else:
            online_vegs = get_online_vegs()

            flash("Vous n'avez aucun légume dans votre panier...", category='warning')
            return render_template("faire_un_panier.html", online_vegs=online_vegs)

    else:
        online_vegs = get_online_vegs()

        return render_template("faire_un_panier.html", online_vegs=online_vegs)

@app.route("/commandes", methods=["GET", "POST"])
@login_required
@admin_required
def commandes():
    if request.method == "POST":
        # Get the updated status and id of related orders
        commande_update_id = request.form.getlist("commande_id")
        commande_update_status = request.form.getlist("status_update")
        commandes_updated = tuple((zip(commande_update_status, commande_update_id)))

        # Get ready to update
        db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
        db.row_factory = sqlite3.Row
        cur = db.cursor()

        # Update commandes table
        # First, loop the tuple of tuples and identify the item with an index
        for index, item in enumerate(commandes_updated):
            cur.execute("UPDATE commandes SET status = ? WHERE id = ?", commandes_updated[index])
            db.commit()

        en_attente = get_pending_orders()

        commandes_validees = cur.execute("""SELECT id, user_id, status, strftime("%d/%m/%Y", time) AS time, selling_point, total_price FROM commandes WHERE status = "Validée" ORDER BY time ASC""").fetchall()

        flash("Les statuts des commandes ont bien été mis à jour.\nLes clients pourront voir les changements lorsqu'ils se connecteront.", category='success')
        return render_template("commandes_control.html", **locals())

    else:
        en_attente = get_pending_orders()

        db = sqlite3.connect("ptits_oignons.db", check_same_thread=False)
        db.row_factory = sqlite3.Row
        cur = db.cursor()

        commandes_validees = cur.execute("""SELECT id, user_id, status, strftime("%d/%m/%Y", time) AS time, selling_point, total_price FROM commandes WHERE status = "Validée" ORDER BY time ASC""").fetchall()

        return render_template("commandes_control.html", **locals())

@app.route("/vente")
def vente():
    mymap = Map(
        identifier="points-de-vente",
        lat = 48.216955,
        lng = 7.009494,
        markers=[
            {
                'lat' : 48.216955,
                'lng' : 7.009494,
                'infobox': "<p>La Ferme aux Petits Oignons</p>"
            },
            {
                'lat': 48.286468700153385,
                'lng': 6.951420355545631,
                'infobox': "<p>Le Bistroquet</p>"
            },
            {
                'lat': 48.285908,
                'lng': 6.950782,
                'infobox': "<p>Marché de Saint-Dié-des-Vosges</p>"
            }
        ],
        fit_markers_to_bounds = True
    )

    return render_template("vente.html", mymap=mymap)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        nom = request.form.get("contact_name")
        prenom = request.form.get("contact_prenom")
        phone = request.form.get("phone")
        email = request.form.get("email")
        message_area = request.form.get("message_area")

        subject = "Contact site web Les Petits Oignons - Quelqu'un a une question..."
        msg = Message(subject, sender=MAIL_USERNAME, recipients=[MAIL_USERNAME,])
        msg.body = """Quelqu'un a essayer de te contacter via le site web. Voici sa / ses questions... """
        # In fact, you can just return a template. Gmail is not friendly with any of the styling...
        msg.html = render_template("contact_mail.html", nom=nom, prenom=prenom, phone=phone, email=email, message_area=message_area)
        mail.send(msg)

        flash("Votre message a bien été pris en compte. Nous vous répondrons au plus vite.", category='success')
        return render_template("contact.html")

    else:
        return render_template("contact.html")

@app.route("/paniers")
def paniers():
    return render_template("paniers.html")

@app.route("/about")
def about():
    return render_template("about.html")
